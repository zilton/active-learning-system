# -*- coding: utf-8 -*-
'''
Created on Dec/2016

@author: Zilton Cordeiro Junior
@github: https://github.com/zilton
@project: EUBRA-BIGSEA
@task: Active Learning System
'''

import ast
from bson import json_util
from datetime import datetime
from dateutil import tz
import datetime
from django.template.defaultfilters import pprint
from flask import (
    Blueprint, render_template, session, g, flash, request, redirect, url_for,
    current_app
)
from flask import Blueprint, render_template
import re
import time

from accounts.models import User
from pages.models import Statistic
from pages.models import Tweets
from settings import MONGODB_SETTINGS, db_active_learning
from settings_active_self_learning import MIN_SCORE_SELF_TRAINING
from system.models import Project

pages_app = Blueprint('pages_app', __name__)

t = None

@pages_app.route('/')
def index():   
    return render_template('pages/index.html')


@pages_app.route('/about/')
def about():
    return render_template('pages/about.html')

@pages_app.route('/training/<project_name>')
def training(project_name):
    if 'user_id' in session:
        user = User.objects.get(pk=session['user_id'])
        if user.control:
            if not project_name in user.control.projects:
                g.tweet = None
                flash(u"You don't have permission to work on the project %s" % project_name, 'warning')
                return redirect("/")
        else:
            flash(u"You don't have permission to work on the project %s" % project_name, 'warning')
            return redirect("/")
        
        project = Project.objects.get(name=project_name)
        if not project.is_active:
            g.tweet = None
            flash(u"The %s project is disabled!" % project_name, 'warning')
            return render_template('pages/training.html')
        
        g.tweet = Tweets.objects.filter(__raw__={'control.lock' : {'$exists' : False}, 'control.project':project_name}).order_by('control.created_at', 'age').first()
        
        try:
            tweet_utc_time = g.tweet.created_at
            
            from_zone = tz.tzutc()
            to_zone = tz.tzlocal()
            
            utc = g.tweet.created_at.replace(tzinfo=from_zone)
            local = utc.astimezone(to_zone)
            print utc, local
            g.tweet.created_at = local
            
            conn = db_active_learning['tweets']
            control = g.tweet.control
            control['lock'] = datetime.datetime.utcnow()
            conn.save({'_id':int(g.tweet._id), 'control':control, 'text':g.tweet.text, 'created_at':tweet_utc_time})
            
            g.statistic = Statistic.objects.filter(username=g.user.username).first()
        except:
            g.tweet = None
        
        if not g.tweet == None:
            '''
            #SERÁ NECESSÁRIO NO FUTURO
            while (True) :
                print g.tweet.control
                control = ast.literal_eval(str(g.tweet.control))
                if 'score' in control['self_training']:
                    if control['classification']['score'] < MIN_SCORE_SELF_TRAINING:
                        break
                g.tweet = Tweets.objects.filter(control__exists={"active_learning" : {}}).first()
            '''
            
            g.class_color = []
            project = Project.objects.get(name=project_name)
            for train in project.workflow.trains:
                for i in range(0, len(train.classes)):
                    g.class_color.append([train.classes[i], train.colors[i]])
            
            g.metrics = ['Classifier', 'Score', 'Sentiment']
            g.values = []
            g.project = project_name
            
            for classifier in g.tweet["control"]["classification"]:
                g.values.append([classifier["classifier"],
                                 float("%.2f" % classifier["score"]),
                                 classifier["sentiment"]])
    else:
        return redirect('login')
    
    return render_template('pages/training.html')

@pages_app.route('/projects/')
def all_projects():
    projects = Project.objects.filter()
    
    if 'user_id' in session:
        user = User.objects.get(pk=session['user_id'])
        
        if user.control:
            if user.control.projects:
                user_projects = user.control.projects
            else:
                user_projects = []
        else:
            user.add_control()
            
        g.all_projects = []
        
        for project in projects:
            if project.is_active:
                if project.name in user_projects:
                    g.all_projects.append([project.name, True])
                else:
                    g.all_projects.append([project.name, False])
    
    return render_template('pages/projects.html')
    
@pages_app.route('/projects/action/<project>/<action>')
def add_remove_project(project, action):
    print project, action
    
    if action.lower() == "true":
        action = True
    elif action.lower() == "false":
        action = False
    else:
        return redirect(url_for('pages_app.all_projects'))
    
    if 'user_id' in session:
        user = User.objects.get(pk=session['user_id'])
        if user.control:
            if not user.control.projects:
                user.add_control()
            
        else:
            user.add_control()
        
        
        if action:
            if not project in user.control.projects:
                user.control.projects.append(project)
        else:
            if project in user.control.projects:
                user.control.projects.remove(project)
                
        user.save() 
    
    return redirect(url_for('pages_app.all_projects'))

@pages_app.route('/statistics/')
def statistics():
    '''
    db.training_tweets.aggregate([ { "$group": { "_id": { "day": { "$dayOfMonth" : "$control.active_learning.classified_at" }, "month": { "$month" : "$control.active_learning.classified_at" }, "year": { "$year" : "$control.active_learning.classified_at" } }, "Count": { "$sum" : 1 } } }, { "$sort": { "_id.year": 1, "_id.month": 1, "_id.day": 1 } }, { "$project": { "_id": 0, "date": { "$concat": [ {"$substr" : [ "$_id.day", 0, 2]}, "-", {"$substr" : [ "$_id.month", 0, 2]}, "-", {"$substr" : [ "$_id.year", 0, 4]} ] }, "count": 1 } } ])
    '''
    
    g.user = None
    g.count_data = [{"key" : "Labeled tweets", "values":[], "color": "#00adff"}]
    if 'user_id' in session:
        try:
            g.user = User.objects.get(pk=session['user_id'])
            if g.user.is_superuser:
                collection_training_tweets = db_active_learning['training_tweets']
                result = collection_training_tweets.aggregate([ { "$group": {
                                                                             "_id": {
                                                                                     "day": {"$dayOfMonth" : "$control.active_learning.classified_at" },
                                                                                     "month": { "$month" : "$control.active_learning.classified_at" },
                                                                                     "year": { "$year" : "$control.active_learning.classified_at" } 
                                                                                     },
                                                                             "count": { "$sum" : 1 } } },
                                                               { "$sort": {
                                                                           "_id.day": -1,
                                                                           "_id.year": -1,
                                                                           "_id.month": -1,
                                                                            } 
                                                                }, 
                                                               { "$project": { 
                                                                              "_id": 0, 
                                                                              "date": { 
                                                                                       "$concat": [ 
                                                                                                   {
                                                                                                     "$substr" : [ "$_id.day", 0, 2]}, 
                                                                                                   "-", {"$substr" : [ "$_id.month", 0, 2]}, 
                                                                                                   "-", {"$substr" : [ "$_id.year", 0, 4]} ] }, 
                                                                              "count": 1 
                                                                              } 
                                                                } ])
                i = 0
                for r in result:
                    #date = time.mktime(datetime.datetime.strptime(r['date'], "%d-%m-%Y").timetuple())
                    #g.count_data[0]["values"].append([int(date)*1000, r['count']])
                    g.count_data[0]["values"].append({"label" : str(r['date']), "value" : int(r['count'])})
                    i += 1
                    if i == 15:
                        break

        except:
            pass
    
    return render_template('pages/statistics.html')

@pages_app.route('/manager/system', methods=['GET', 'POST'])
def manager_system():
    
    if 'user_id' in session:
        pass
    
    return render_template('pages/manager_system.html')

@pages_app.route('/classification/<sentiment>/<_id>')
def classification(sentiment, _id):
    
    if not 'user_id' in session:
        return redirect('login')
    
    op = sentiment.split(';')
    sentiment = op[0]
    project_name = op[1]
    
    tweet = Tweets.objects.filter(_id=_id).first()
    classified_at = datetime.datetime.utcnow()
    
    try:
        username = g.user.username
    except:
        username = 'guest'
        
    er = re.compile('CLASS\=[0-9]*',re.IGNORECASE + re.DOTALL)
    tweet['control']['lac_line'] = er.sub(("CLASS=%s" % sentiment), tweet['control']['lac_line'])
    
    tweet['control']['active_learning'] = {'sentiment' : sentiment,
                                           'user' : username,
                                           'classified_at':classified_at}
    
    collection_labeled_tweets = db_active_learning['labeled_tweets']
    collection_tweets = db_active_learning['tweets']
    collection_statistic = db_active_learning['statistic']
    
    tweet['control'].pop('lock', None)
    collection_labeled_tweets.save({'_id':int(_id), 'control':tweet['control'], 'text':tweet.text, 'created_at':tweet.created_at})
    collection_tweets.remove({'_id':int(_id)})
    
    result = collection_statistic.find({'username' : username})
    exists = False
    for s in result:
        exists = True
        s['count'] = s['count'] + 1
        g.count_labeled = s['count']
        
        if not 'goal' in s:
            s['goal'] = {'classified_at':classified_at, 'count':600}
        if s['goal']['count'] > 0:
            s['goal']['count'] = s['goal']['count'] - 1
        else:
            s['goal']['count'] = 600
        s['goal']['classified_at'] = classified_at
        
        collection_statistic.save(s)
    
    if not exists:
        collection_statistic.save({'username' : username, 'count' : 1, 'last' : datetime.datetime.utcnow()})
    
    return redirect(url_for('pages_app.training', project_name=project_name))

    




