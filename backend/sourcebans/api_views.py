﻿from enum import Enum
from django.db.models import Q
from rest_framework import filters, permissions, pagination, viewsets, response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView
from django.http import HttpResponse
from django.utils.timezone import localtime
from time import mktime
import django_filters
from .permissions import sbPermissions
from .views import get_client_ip

from .serializers import BansSerializer

from steam.steamid import SteamID
from steamwebapi.api import ISteamUser
from tensor_site.auth_tokens import *

import valve.rcon
import re

from gamestatistics.models import Rank_awp, Rank_retake
from servers.models import Server
from .models import *
from .filter import *
from .tables import *


steamuserinfo = ISteamUser(steam_api_key=SteamWebAPIKey)

class requestTypeEnum(Enum):
		delete = 1
		update = 2

class DefaultResultsSetPagination(pagination.PageNumberPagination):
		page_size = 10
		page_size_query_param = 'limit'
		max_page_size = 100

class BansFilter(django_filters.FilterSet):
		search = django_filters.CharFilter(method='search_filter', label="search")
		bid = django_filters.NumberFilter(field_name="bid", lookup_expr="iexact", label="bid")

		def search_filter(self, queryset, name, value):
				return SbBans.objects.filter(
						Q(authid__icontains=value) | Q(name__icontains=value)
				)
		
		class Meta:
				model = SbBans
				fields = ["search", "bid"]

class BurstRateThrottle(UserRateThrottle):
		rate = '20/min'

class BansViewSet(viewsets.ModelViewSet):
		"""API endpoint for the bans list"""
		queryset = SbBans.objects.all().order_by('-bid')
		serializer_class = BansSerializer
		throttle_classes = [BurstRateThrottle]
		permission_classes = [permissions.IsAuthenticatedOrReadOnly]
		filter_backends = [filters.OrderingFilter, django_filters.rest_framework.DjangoFilterBackend]
		ordering_fields = ['name', 'created']
		ordering = '-created'
		pagination_class = DefaultResultsSetPagination
		filterset_class = BansFilter

		def create(self, request, *args, **kwargs):
				requestUser = request.user
				if(not requestUser.is_admin):
					return HttpResponse(status=403)
				if(not canAdminAddBan(requestUser.sb_admin_id)):
					return HttpResponse(status=403)

				data = request.data.copy()
				steamid = data["steamid"]

				try:
					if re.search("^https?\:\/\/steamcommunity.", steamid):
						steamid64 = SteamID.from_url(steamid, 5).as_64
					else:
						steamid64 = SteamID(steamid).as_64
					usersummary = steamuserinfo.get_player_summaries(steamid64)['response']['players'][0]
				except:
					return response.Response(data={"error": "INVALID_STEAMID"}, status=422, )
				
				steamid = SteamID(steamid64).as_steam2

				lastip = Rank_awp.objects.filter(steam=steamid).first()
				if(lastip is None):
					lastip = Rank_retake.objects.filter(steam=steamid).first()
				if(lastip is not None):
					lastip = lastip.lastip

				banInfo = {
					"authid": steamid,
					"ip": lastip,
					"name": usersummary["personaname"],
					"created": mktime(localtime()),
					"ends": data["ends"],
					"length": data["length"],
					"reason": data["reason"],
					"aid": requestUser.sb_admin_id,
					"adminip": get_client_ip(request),
					"sid": 1,
					"type": 0,
				}
				
				serializer = BansSerializer(data=banInfo)
				if serializer.is_valid():
					self.perform_create(serializer)
					return response.Response(data={
						"name": usersummary["personaname"],
						"steamid": steamid
						}, 
						status=200
						)

				return HttpResponse(status=500)

		def update(self, request, *args, **kwargs):
				requestUser = request.user
				instance = self.get_object()

				if(not requestUser.is_admin):
					return HttpResponse(status=403)
				if(not canAdminEditBan(instance.bid, requestUser.sb_admin_id)):
					return HttpResponse(status=403)

				update_type = request.data['update_type']
				aid = requestUser.sb_admin_id
				if update_type == requestTypeEnum.delete.value:
					instance.removedon = mktime(localtime())
					instance.removedby = aid
					instance.removetype = "E"
					instance.save()
					return HttpResponse(status=200)
				if update_type == requestTypeEnum.update.value:
					serializer = BansSerializer(instance=instance, data=request.data, partial=True)
					if serializer.is_valid():
						self.perform_update(serializer)
						return HttpResponse(status=200)
				return HttpResponse(status=500)
				
		def destroy(self, request, pk=None):
				requestUser = request.user
				bid=pk
				if(not requestUser.is_admin):
					return HttpResponse(status=403)
				if(not canAdminEditBan(bid, requestUser.sb_admin_id)):
					return HttpResponse(status=403)

				SbBans.objects.get(bid=bid).delete()
				return HttpResponse(status=200)


def canAdminEditBan(bid, aid):
		user = SbAdmins.objects.get(aid=aid)
		ban = SbBans.objects.get(bid=bid)
		userPermissions = user.gid.flags
		if(user.extraflags != 0):
			userPermissions += user.extraflags
		if(bool(sbPermissions["ADMIN_EDIT_ALL_BANS"]["value"] & userPermissions)):
			return True
		if(bool(sbPermissions["ADMIN_EDIT_OWN_BANS"]["value"] & userPermissions and ban.aid == aid)):
			return True
		if(bool(sbPermissions["ADMIN_EDIT_GROUP_BANS"]["value"] & userPermissions)):
			group = SbAdmins.objects.get(aid=ban.aid).gid
			return user.gid==group
		return False


def canAdminAddBan(aid):
		user = SbAdmins.objects.get(aid=aid)
		userPermissions = user.gid.flags
		if(user.extraflags != 0):
			userPermissions += user.extraflags
		if(bool(sbPermissions["ADMIN_ADD_BAN"]["value"] & userPermissions)):
			return True
		return False


class KickFromServerView(APIView):

		def get(self, request, *args, **kwargs):
			steamid = request.GET['steamid']
			servers = SbServers.objects.all()
			for server in servers:
				address = (server.ip, server.port)
				password = server.rcon
				try:
					with valve.rcon.RCON(address, password) as rcon:
						rconResponse = rcon.execute("status")
						response_text = rconResponse.body.decode("utf-8")
						ids = re.findall("STEAM_[0-5]:[0-1]:[0-9]*", response_text)
						if (steamid in ids):
							serverName = Server.objects.get(port=server.port).name
							rcon.execute("sm_kick #{} You have been banned from this server by an admin.".format(steamid.replace(":", "_")))
							return response.Response(
								data={
									"found": "true",
									"server": serverName
									},
								status=200
							)
				except Exception as e:
					print(e)

			return response.Response(
				data={
					"found": "false",
					"server": ""
					},
				status=200
			)