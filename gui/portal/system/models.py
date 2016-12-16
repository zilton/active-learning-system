# -*- coding: utf-8 -*-
'''
Created on Dec/2016

@author: Zilton Cordeiro Junior
@github: https://github.com/zilton
@project: EUBRA-BIGSEA
@task: Active Learning System
'''

from werkzeug.security import generate_password_hash, check_password_hash
from flask import current_app

from datetime import datetime
from application import db
from common.models import BaseDocument

class TrainConfig(db.EmbeddedDocument):
    name = db.StringField(
                            verbose_name=u'name'
                            )
    
    stop_word = db.StringField(
                                verbose_name=u'stop word',
                                required=True,
                                default="pt",
                                db_field="stop-word"
                                )
    
    remove_stops_first = db.BooleanField(
                                        #verbose_name=u'remove stops first',
                                        required=True,
                                        default=False,
                                        db_field="remove-stops-first"
                                        )
    
    stemmer = db.BooleanField(
                                verbose_name=u'stemmer',
                                required=True,
                                default=False
                            )
    
    total_of_classes = db.IntField(
                                   verbose_name=u'total of classes',
                                   required=True,
                                   db_field="total-of-classes",
                                   default=3
                                  )
    
    classes = db.ListField(
                            db.StringField(
                                           verbose_name=u'classes',
                                           required=True
                                        ),
                            default=[
                                       "negative", "neutral", "positive"
                                    ]
                            )
    
    colors = db.ListField(
                            db.StringField(
                                           verbose_name=u'colors',
                                           required=True
                                        )
                            )
    
    classifier = db.StringField(
                                verbose_name=u'classifier name',
                                required=True,
                                default="LAC"
                                )
    
    ngram_size = db.IntField(
                               verbose_name=u'negram size',
                               required=True,
                               db_field="negram-size",
                               default=1
                              )
    
    max_words = db.IntField(
                           verbose_name=u'max words',
                           required=True,
                           db_field="max-words",
                           default=5000
                          )
    
class ClassifierServerPort(BaseDocument):
    port = db.IntField(
                       verbose_name=u'port',
                       required=True,
                       db_field="port",
                       default=40000
                      )
    
    meta = {
        'indexes': ['port']
    }
    
    def next_port(self):
        self.port = self.port + 0
        self.save()
        return self.port

class ClassificationServer(db.EmbeddedDocument):
    address = db.StringField(
                            verbose_name=u'lac-classification-server address',
                            required=True,
                            default="localhost"
                            )
        
    port = db.IntField(
                       verbose_name=u'port',
                       required=True,
                       default=40000
                      )
    
    classifier_name = db.StringField(
                            verbose_name=u'classifier-name',
                            required=True,
                            db_field="classifier-name",
                            default="LAC"
                            )
    
    training_file = db.StringField(
                                verbose_name=u'training-file',
                                required=True,
                                db_field="training-file",
                                default="/scratch/bigsea_active_learning/treinos_lac/"
                                )

class StopWords(db.EmbeddedDocument):    
    pt = db.StringField(
                        verbose_name=u'PT',
                        required=False,
                        default="/scratch/bigsea_active_learning/processamento/src/pipeline/resources/stopWordLists/portugues.txt"
                        )
    
    en = db.StringField(
                        verbose_name=u'EN',
                        required=False,
                        default="/scratch/bigsea_active_learning/processamento/src/pipeline/resources/stopWordLists/ingles.txt"
                        )
    
    es = db.StringField(
                        verbose_name=u'ES',
                        required=False,
                        default="/scratch/bigsea_active_learning/processamento/src/pipeline/resources/stopWordLists/espanhol.txt"
                        )

class Fields(db.EmbeddedDocument):
    tweets = db.ListField(
                            db.StringField(
                                           verbose_name=u'Tweets fields',
                                           required=False
                                        ),
                            default=[
                                       "_id", "id", "text", "created_at", "geo", "place", "coordinates", "entities", 
                                        "_tmp_", "control", "lang",
                            
                                        "user.id", "user.screen_name", "user.location", "user.profile_image_url", 
                                        "user.profile_image_url_https", "user.friends_count", "user.followers_count", 
                                        "user.description", "user.lang",
                            
                                        "retweeted_status.id", "retweeted_status.text", "retweeted_status.created_at",
                                        "retweeted_status.user.id", "retweeted_status.user.screen_name",
                                        "retweeted_status.retweet_count", "retweeted_status.entities"
                                    ]
                            )
    
class MongoDBUpdater(db.EmbeddedDocument):
    mongodb = db.StringField(
                                verbose_name=u'mongodb',
                                default = "mongodb4.ctweb.inweb.org.br",
                                required=True
                            )
    
    _db = db.StringField(
                            verbose_name=u'db',
                            default = "active_learning",
                            required=True,
                            db_field="db"
                        )
    
    collection = db.StringField(
                            verbose_name=u'collection',
                            default = "tweets",
                            required=True,
                            db_field="collection"
                        )
    port = db.IntField(
                       verbose_name=u'Port',
                       default=27017,
                       required=True,
                       unique=False
                      )
    
class MongoDB(db.EmbeddedDocument):
    host = db.StringField(
            verbose_name=u'Host',
            required=True,
            unique=False
        )
    
    database = db.StringField(
            verbose_name=u'Database',
            required=True,
            unique=False
        )
    
    collection = db.StringField(
            verbose_name=u'Collection',
            required=True,
            unique=False
        )
    
    port = db.IntField(
                       verbose_name=u'Port',
                       default=27017,
                       required=True,
                       unique=False
                      )

class Global(db.EmbeddedDocument):
    
    rabbitmq = db.ListField(
                            db.StringField(
                                           verbose_name=u'list of field (IP, vhost, user, passwd)',
                                           required=False
                                        ),
                                        default=["10.5.5.4", "active_learning", "bigsea", "bigsea"]
                            )
    
    mongodb = db.EmbeddedDocumentField(MongoDB)
    
    mongodb_updater =  db.EmbeddedDocumentField(MongoDBUpdater,
                                                db_field="mongodb-updater"
                                                )
    
    trigrams = db.StringField(
                                verbose_name=u'trigrams',
                                default = "../trigrams/",
                                required=False
                            )
    
    workflow_dir = db.StringField(
                                    verbose_name=u'workflow-dir',
                                    default = "/scratch/bigsea_active_learning/processamento/src/pipeline/workflows/",
                                    required=False,
                                    db_field="workflow-dir"
                                )
    
    contexts = db.ListField(
                            db.StringField(
                                            verbose_name=u'contexts',
                                            default = "1000",
                                            required=False
                                        ),
                            default=["1000"]
                            )
    
    classification_server = db.EmbeddedDocumentField(
                                                             ClassificationServer,
                                                             db_field = "classification-server",
                                                             default=ClassificationServer()
                                                        )
    '''
    lac_dir = db.StringField(
                                verbose_name=u'lac-dir',
                                default = "lac-basedir/",
                                required=False,
                                db_field="lac-dir"
                            )
    '''
    
    fields =  db.EmbeddedDocumentField(Fields)
    
    stop_words =  db.EmbeddedDocumentField(StopWords,
                                           db_field="stop-words"
                                           )
    
class Workflow(db.EmbeddedDocument):
    _global =  db.EmbeddedDocumentField(
                                        Global,
                                        db_field="global",
                                        required=True,
                                        )
    trains = db.ListField(db.EmbeddedDocumentField(TrainConfig))
    
class SelfTraining(db.EmbeddedDocument):
    threshold = db.FloatField(
                                verbose_name=u'Threshold',
                                default=0.9,
                                required=True,
                                db_field="threshold"
                            )
class Project(BaseDocument):

    name =  db.StringField(
            verbose_name=u'name',
            max_length=100,
            required=True,
            unique=True
        )
    
    users = db.ListField(db.StringField(
                                        verbose_name=u'list of user name',
                                        required=False,
                                        unique=False
                                        )
                         )
    
    languages = db.ListField(db.StringField(
                                            verbose_name=u'Languages',
                                            required=False,
                                            unique=False
                                            ),
                             default=["pt"]
                             )
    
    self_training = db.EmbeddedDocumentField(SelfTraining,
                                             verbose_name=u'Self-Training',
                                             required=True,
                                             db_field="self-training"
                                            )
    
    is_active = db.BooleanField(
        verbose_name=u'active',
        default=False,
        required=False
    )
    
    created_at = db.DateTimeField(
        verbose_name=u'created at',
        default=datetime.utcnow(),
        required=False
    )
    
    updated_at = db.DateTimeField(
        verbose_name=u'updated at',
        default=datetime.utcnow(),
        required=False
    )
    
    workflow =  db.EmbeddedDocumentField(Workflow)

    meta = {
        'indexes': ['name', 'users', 'created_at', 'is_active']
    }

    def __init__(self, *args, **kwargs):
        super(Project, self).__init__(*args, **kwargs)
    
    def add_user(self, username):
        self.users.append(username)
        self.save()
        
    def change_is_active(self, is_active):
        self.is_active = is_active
        self.save()
    
    def set_workflow(self, workflow):
        self.workflow = workflow
        self.save()
    
    def delete_project(self):
        self.delete()
        
        
        
        
        