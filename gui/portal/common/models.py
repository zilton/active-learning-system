# -*- coding: utf-8 -*-
'''
Created on Dec/2016

@author: Zilton Cordeiro Junior
@github: https://github.com/zilton
@project: EUBRA-BIGSEA
@task: Active Learning System
'''

from application import db

from datetime import datetime


class BaseDocument(db.Document):

    created_at = db.DateTimeField(
        verbose_name=u'Criado em',
        required=True
    )
    updated_at = db.DateTimeField(
        verbose_name=u'Atualizado em',
        required=True
    )

    meta = {'abstract': True}

    def save(self, *args, **kwargs):
        if not self.created_at:
            self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        return super(BaseDocument, self).save(*args, **kwargs)
