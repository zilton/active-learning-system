# -*- coding: utf-8 -*-
'''
Created on Dec/2016

@author: Zilton Cordeiro Junior
@github: https://github.com/zilton
@project: EUBRA-BIGSEA
@task: Active Learning System
'''

from _socket import timeout
from flask import (session, g)
from flask import render_template, current_app
from flask_mail import Message
from pymongo import MongoClient
from wtforms import *

from accounts.models import *
from accounts.models import User
from application import mail
from common.utils import get_signer
from flask.ext.wtf import Form
from system.models import *
import re

class ProjectForm(Form):

    project = None

    name = TextField(
        label=u'Project name',
        validators=[
            validators.required(),
            validators.Regexp(
                                regex=r'.+',
                                message=u'Use any name.'
                            )
        ]
    )
    
    nameup = SelectField(
        label=u'Project name',
        choices=[],
        validators=[
            validators.Optional()
        ]
    )
    
    host = TextField(
        label=u'Host',
        validators=[
            validators.required()
        ]
    )
    
    port = IntegerField(label=u'Port',
                        default=27017,
                        validators=[
                            validators.required(),
                            validators.NumberRange(min=0, max=65535)
                        ])
    
    database = TextField(
        label=u'Database',
        validators=[
            validators.required()
        ]
    )
    
    collection = TextField(
        label=u'Collection',
        validators=[
            validators.required()
        ]
    )
    
    languages = TextField(
                            label=u'Language(s)',
                            description="Minimum one language. PT;EN;ES",
                            default="PT",
                            validators=[validators.required(),
                                        validators.Regexp(
                                                            regex=r'((\w\w\;)+)|(^\w\w$)',
                                                            message=u'Split the classes using semicolons.'
                                                        )
                                        ]
                        )
    
    ###Train configuration
    
    nameTrain = TextField(
                            label=u'Training name',
                            validators=[validators.required(),
                                        validators.Regexp(
                                                            regex=r'([\w\d]+(\-)*(\_)*)+',
                                                            message=u'Only letters, numbers, - ou _'
                                                        )
                                        ]
                        )
    
    stop_word = TextField(
                            label='Stop word',
                            description="PT or EN or ES",
                            default='PT',
                            validators=[validators.required(),
                                        validators.Regexp(
                                                            regex=r'^([pP][tT]|[eE][sS]|[eE][nN])$',
                                                            message=u'Just PT or EN or ES'
                                                        )]
                            )
    
    remove_stops_first = BooleanField(
                            label='Remove stop word first',
                            validators=[validators.Optional()],
                            default=True
                            )
    
    stemmer = BooleanField(
                            label='Stemming',
                            validators=[validators.Optional()],
                            default=True
                            )
    
    classes = TextField(
                        label=u'Classes',
                        default="negative;neutral;positive",
                        description="Minimum two classes. Split using semicolon.",
                        validators=[
                            validators.required(),
                            validators.Regexp(
                                                regex=r'([\w\d]+\;)+',
                                                message=u'Split the classes using semicolons.'
                                            )]
                        )
    
    colors = TextField(
                        label=u'Colors',
                        default="D42A17;2B99D9;33D92E",
                        description="Same number and order of the classes. Split using semicolon.",
                        validators=[
                            validators.required(),
                            validators.Regexp(
                                                regex=r'([\w\d]+\;)+',
                                                message=u'Split the colors using semicolons.'
                                            )]
                        )
    
    classifier = TextField(
                        label=u'Classifier',
                        default="LAC",
                        validators=[
                            validators.required()
                        ]
                    )
    
    ngram_size = IntegerField(label=u'N-gram size',
                        default=1,
                        validators=[
                            validators.required(),
                            validators.NumberRange(min=1, max=3)
                        ])
    
    max_words = IntegerField(label=u'Max words',
                        default=5000,
                        validators=[
                            validators.required(),
                            validators.NumberRange(min=10, max=100000)
                        ])
    
    threshold = FloatField(label=u'Threshold',
                                default=0.9,
                                description="Between 0.2 and 1.0",
                                validators=[
                                            validators.required(),
                                            validators.NumberRange(min=0.2, max=1.0)
                                            ]
                           )
    
    is_active = BooleanField(
                            label='Active',
                            validators=[validators.Optional()],
                            default=True
                            )
    
    next = HiddenField()

    def validate_connection(self, host, database, collection, port):
        print host.data, database.data, collection.data, port.data
        try:
            mongoCon = MongoClient(host=host.data, port=port.data)
        except:
            return False
        try:
            db_raw_data = getattr(mongoCon, database.data)
            col = db_raw_data[collection.data]
        except:
            return False
        try:
            count = col.count()
            print count
            if count == 0:
                return False
        except:
            return False
        
        mongoCon.close()
        return True
        
    def save(self, name, host, database,
             collection, port, nameTrain,
             stop_word, remove_stops_first,
             stemmer, classes, colors, classifier, 
             ngram_size, max_words, languages, threshold, is_active):
        
        name = self.name.data
        host = self.host.data
        database = self.database.data
        collection = self.collection.data
        port = self.port.data
        nameTrain = self.nameTrain.data
        stop_word = self.stop_word.data.lower()
        remove_stops_first = self.remove_stops_first.data
        stemmer = self.stemmer.data
        classes = self.classes.data.lower()
        colors = self.colors.data
        classifier = self.classifier.data
        ngram_size = int(self.ngram_size.data)
        max_words = self.max_words.data
        languages = self.languages.data.lower()
        threshold = float(self.threshold.data)
        is_active = self.is_active.data
        
        g.user = User.objects.get(pk=session['user_id'])
        
        mongodb = MongoDB(host=host, database=database, collection=collection, port=port)
        
        mongodb_updater = MongoDBUpdater()
        
        classification_server = ClassificationServer()
        classification_server.training_file = classification_server.training_file + "labelled_training__" + name + "_" + classification_server.classifier_name + ".txt" 
        
        classes = classes.split(';')
        
        er = re.compile(';$', re.IGNORECASE)
        colors = er.sub('', colors).split(';')
        
        if not len(classes) == len(colors):
            return ("length", False)
        
        for c in classes:
            if classes.count(c) > 1:
                return ("classes", False)
        
        for c in colors:
            if colors.count(c) > 1:
                return ("colors", False)
            
        trains=[TrainConfig(name=nameTrain, stop_word=stop_word, remove_stops_first=remove_stops_first,
                           stemmer=stemmer, classes=classes, colors=colors, classifier=classifier, ngram_size=ngram_size,
                           max_words=max_words, total_of_classes=len(classes))]
        
        workflow = Workflow(_global = Global(classification_server=classification_server,
                                             mongodb_updater=mongodb_updater,
                                             mongodb=mongodb,
                                             fields=Fields(),
                                             stop_words=StopWords()
                                             ),
                            trains=trains
                            )
        
        
        p = ClassifierServerPort.objects.filter().first()
        if p == None:
            p = ClassifierServerPort()
            p.save()
        
        workflow._global.classification_server.port = p.next_port()
        
        self_training = SelfTraining(threshold=threshold)
        
        languages = languages.split(";")
        project = Project(name=name, users=[g.user.username],
                          workflow=workflow, languages=languages, self_training=self_training,
                          is_active=is_active)
        project.save()
        
        user = User.objects.get(pk=session['user_id'])
        if not self.name.data in user.control.projects:
            user.control.projects.append(self.name.data)
            user.save()
        
        return ("insert", True)
    
    def update(self, name, host, database,
             collection, port, nameTrain,
             stop_word, remove_stops_first,
             stemmer, classes, colors, classifier, 
             ngram_size, max_words, languages,
             threshold, is_active, project):    
        
        project.workflow._global.mongodb.host = self.host.data
        project.workflow._global.mongodb.database = self.database.data
        project.workflow._global.mongodb.collection = self.collection.data
        project.workflow._global.mongodb.port = self.port.data
        
        project.self_training.threshold = self.threshold.data
        project.is_active = self.is_active.data
        project.languages = self.languages.data.split(';')
        
        project.workflow.trains[0].stop_word = self.stop_word.data
        project.workflow.trains[0].stemmer = self.stemmer.data
        project.workflow.trains[0].remove_stops_first = self.remove_stops_first.data
        project.workflow.trains[0].classes = self.classes.data.split(';')
        
        er = re.compile(';$', re.IGNORECASE)
        project.workflow.trains[0].colors = er.sub('', self.colors.data).split(';')
        project.workflow.trains[0].classifier = self.classifier.data
        project.workflow.trains[0].ngram_size = self.ngram_size.data
        project.workflow.trains[0].max_words = self.max_words.data
        
        classes = project.workflow.trains[0].classes
        colors = project.workflow.trains[0].colors
        
        if not len(classes) == len(colors):
            return ("length", False)
        
        for c in classes:
            if classes.count(c) > 1:
                return ("classes", False)
        
        for c in colors:
            if colors.count(c) > 1:
                return ("colors", False)
        
        project.save()
        
        user = User.objects.get(pk=session['user_id'])
        if not self.name.data in user.control.projects:
            user.control.projects.append(self.name.data)
            user.save()
            
        return ("update", True)
    
    
    
    