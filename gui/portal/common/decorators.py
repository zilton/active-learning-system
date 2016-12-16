# -*- coding: utf-8 -*-
'''
Created on Dec/2016

@author: Zilton Cordeiro Junior
@github: https://github.com/zilton
@project: EUBRA-BIGSEA
@task: Active Learning System
'''

from functools import wraps
from flask import request


def get_page(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        page = request.args.get('page', 1)
        try:
            kwargs['page'] = int(page)
        except:
            kwargs['page'] = 1
        return f(*args, **kwargs)
    return decorated_function
