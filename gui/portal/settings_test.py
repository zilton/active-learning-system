# -*- coding: utf-8 -*-
'''
Created on Dec/2016

@author: Zilton Cordeiro Junior
@github: https://github.com/zilton
@project: EUBRA-BIGSEA
@task: Active Learning System
'''

from settings import *

# flask core settings
TESTING = True

# flask wtf settings
WTF_CSRF_ENABLED = False

# flask mongoengine settings
MONGODB_SETTINGS = {
    'DB': 'flaskexample_test'
}

# password hash method
PROJECT_PASSWORD_HASH_METHOD = 'md5'
