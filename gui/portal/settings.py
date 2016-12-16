# -*- coding: utf-8 -*-
'''
Created on Dec/2016

@author: Zilton Cordeiro Junior
@github: https://github.com/zilton
@project: EUBRA-BIGSEA
@task: Active Learning System
'''

from pymongo import MongoClient

# flask core settings
DEBUG = True
TESTING = False
SECRET_KEY = 'qh\x98\xc4o\xc4]\x8f\x8d\x93\xa4\xec\xc5\xfd]\xf8\xb1c\x84\x86\xa7A\xcb\xc0'
PERMANENT_SESSION_LIFETIME = 60 * 60 * 24 * 30

# flask wtf settings
WTF_CSRF_ENABLED = True

# flask mongoengine settings
MONGODB_SETTINGS = {
    'host' : 'localhost:5500',#'mongodb4.ctweb.inweb.org.br',
    'db': 'active_learning'
}
mongoCon = MongoClient(host=MONGODB_SETTINGS['host'], port=27017)
db_active_learning = getattr(mongoCon, MONGODB_SETTINGS['db'])

# flask mail settings
'''
For gmail is necessary turn on the access for less secure apps.
https://www.google.com/settings/security/lesssecureapps
'''

MAIL_DEFAULT_SENDER = 'eubrabigseaufmg@gmail.com'
MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USE_SSL = False
MAIL_USERNAME = 'eubrabigseaufmg@gmail.com'
MAIL_PASSWORD = '3uBR4B!GS34UFMG'

# project settings
PROJECT_PASSWORD_HASH_METHOD = 'pbkdf2:sha1'
PROJECT_SITE_NAME = u'Active Learning System'
PROJECT_SITE_URL = u'http://127.0.0.1:5000'
PROJECT_SIGNUP_TOKEN_MAX_AGE = 60 * 60 * 24 * 7  # in seconds
PROJECT_RECOVER_PASSWORD_TOKEN_MAX_AGE = 60 * 60 * 24 * 7  # in seconds


