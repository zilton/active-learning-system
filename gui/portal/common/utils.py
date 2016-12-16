# -*- coding: utf-8 -*-
'''
Created on Dec/2016

@author: Zilton Cordeiro Junior
@github: https://github.com/zilton
@project: EUBRA-BIGSEA
@task: Active Learning System
'''

from flask import current_app
from itsdangerous import URLSafeTimedSerializer


def get_signer():
    secret = current_app.config['SECRET_KEY']
    s = URLSafeTimedSerializer(secret)
    return s
