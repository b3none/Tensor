from .base import *

DEBUG = False

# Database
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases

DATABASE_ROUTERS = ['Tensor.dbrouters.router']

DATABASES = {
		'default': {
        'NAME': 'Tensor',
        'ENGINE': 'django.db.backends.mysql',
        'USER': 'tensor',
        'PASSWORD': password_DB_awp,
        'HOST': '127.0.0.1',
        'PORT': '3306',
				'OPTIONS': {'charset': 'utf8mb4'},
    },
    'rank_awp': {
        'NAME': 'rank_awp',
        'ENGINE': 'django.db.backends.mysql',
        'USER': 'csgoawp',
        'PASSWORD': password_DB_awp,
        'HOST': '127.0.0.1',
        'PORT': '3306',
    },
    'surftimer': {
        'NAME': 'surftimer',
        'ENGINE': 'django.db.backends.mysql',
        'USER': 'csgosurf',
        'PASSWORD': password_DB_awp,
        'HOST': '192.168.1.105',
        'PORT': '3306',
    },
		'sourcebans': {
        'NAME': 'sourceban',
        'ENGINE': 'django.db.backends.mysql',
        'USER': 'sourceban',
        'PASSWORD': password_DB_sb,
        'HOST': '127.0.0.1',
        'PORT': '3306',
    },
    'rank_retake': {
        'NAME': 'retake_rank',
        'ENGINE': 'django.db.backends.mysql',
        'USER': 'retake',
        'PASSWORD': password_DB_retakes,
        'HOST': '127.0.0.1',
        'PORT': '3306',
    },
    'tvip': {
        'NAME': 'VIP',
        'ENGINE': 'django.db.backends.mysql',
        'USER': 'csgoawp',
        'PASSWORD': password_DB_awp,
        'HOST': '127.0.0.1',
        'PORT': '3306',
    },
}

# Paypal
PAYPAL_RECEIVER_EMAIL = paypalEmail
PAYPAL_TEST = False
ABSOLUTE_URL = 'tensor.fr'