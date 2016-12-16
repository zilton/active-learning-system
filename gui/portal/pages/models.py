# -*- coding: utf-8 -*-
'''
Created on Dec/2016

@author: Zilton Cordeiro Junior
@github: https://github.com/zilton
@project: EUBRA-BIGSEA
@task: Active Learning System
'''

from flask import current_app

from datetime import datetime
from application import db
from common.models import BaseDocument
from mongoengine.fields import ReferenceField

class Tweets(BaseDocument):
    _id = db.IntField(
        verbose_name=u'_id',
        required=True,
        unique=True
    )
    
    text = db.StringField(
        verbose_name=u'Tweet',
        max_length=140,
        required=True,
        unique=False
    )
    
    created_at = db.DateTimeField(
        verbose_name=u'Created at',
        required=False
    )
    
    control = db.StringField(
        verbose_name=u'Control',        
    )
    
    control.lock = db.IntField(
        verbose_name=u'lock',
        required=True,
        unique=False
    )
    
    meta = {
        'indexes': ['control', '_id', 'text']
    }
    
    def set_sentiment(self, sentiment, user_id):
        self.sentiment = sentiment
        self.save()
    
    def get_tweet(self):
        self.find()
    
class Statistic(BaseDocument):
    _id = db.StringField(
        verbose_name=u'_id',
        required=True,
        unique=True
    )
    
    username = db.StringField(
        verbose_name=u'Username',
        max_length=140,
        required=True,
        unique=True
    )
    
    last = db.DateTimeField(
        verbose_name=u'Last',
        required=True
    )
    
    count = db.IntField(
        verbose_name=u'Count',
        required=True,
        unique=False
    )
    
    goal = db.StringField(
        verbose_name=u'Count',
        required=True,
        unique=False
    )
    
    
    meta = {
        'indexes': ['username', '_id', 'last']
    }
    
    def get_statistic(self):
        self.find()
        
class Dashboard(BaseDocument):
    _id = db.StringField(
        verbose_name=u'_id',
        required=True,
        unique=True
    )
    
    username = db.StringField(
        verbose_name=u'Username',
        max_length=140,
        required=True,
        unique=True
    )
    
    last = db.DateTimeField(
        verbose_name=u'Last',
        required=True
    )
    
    count = db.IntField(
        verbose_name=u'Count',
        required=True,
        unique=False
    )
    
    goal = db.StringField(
        verbose_name=u'Count',
        required=True,
        unique=False
    )
    
    
    meta = {
        'indexes': ['username', '_id', 'last']
    }
    
    def get_statistic(self):
        self.find()