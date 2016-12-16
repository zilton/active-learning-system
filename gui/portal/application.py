# -*- coding: utf-8 -*-
'''
Created on Dec/2016

@author: Zilton Cordeiro Junior
@github: https://github.com/zilton
@project: EUBRA-BIGSEA
@task: Active Learning System
'''

from flask import Flask

from flask.ext.mongoengine import MongoEngine
from flask_mail import Mail

# flask mongoengine
db = MongoEngine()

# flask mail
mail = Mail()

def create_app(config_filename):
    app = Flask(__name__)
    app.config.from_object(config_filename)

    # flask mongoengine init
    db.init_app(app)

    # flask mail init
    mail.init_app(app)

    # import blueprints
    from accounts.views import accounts_app
    from pages.views import pages_app
    from system.views import system_app

    # register blueprints
    app.register_blueprint(accounts_app)
    app.register_blueprint(pages_app)
    app.register_blueprint(system_app)

    return app
