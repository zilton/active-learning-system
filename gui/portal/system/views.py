# -*- coding: utf-8 -*-
'''
Created on Dec/2016

@author: Zilton Cordeiro Junior
@github: https://github.com/zilton
@project: EUBRA-BIGSEA
@task: Active Learning System
'''

from flask import (
    Blueprint, render_template, session, g, flash, request, redirect, url_for,
    current_app
)
from system.forms import (ProjectForm)
from accounts.models import User
from system.models import *
system_app = Blueprint('system_app', __name__)

@system_app.before_app_request
def list_projects():
    if 'user_id' in session:
        try:
            user = User.objects.get(pk=session['user_id'])
            g.projects = []
            for project in user.control.projects:
                project_object = Project.objects.get(name=project)
                if project_object.is_active:
                    g.projects.append(project)
            g.project = ""
        except:
            pass

@system_app.route('/manager/system/new-project', methods=['GET', 'POST'])
def new_project():
    
    form = ProjectForm()
    
    if form.validate_on_submit():
        if form.validate_connection(form.host, form.database, form.collection, form.port):
            try:
                action, success = form.save(form.name, form.host, form.database,
                          form.collection, form.port, form.nameTrain,
                          form.stop_word, form.remove_stops_first,
                          form.stemmer, form.classes, form.colors, form.classifier, 
                          form.ngram_size, form.max_words, form.languages,
                          form.threshold, form.is_active)
                if success:
                    flash(u'Project successfully created!', 'success')
                    if form.is_active.data:
                        flash(u'In up to 1 minute the project will be active for classification.', 'warning')
                    else:
                        flash(u'In up to 1 minute the project will be disabled for classification.', 'warning')
                    return redirect(url_for('system_app.new_project'))
                elif action == "length":
                    flash(u'The length of the classes and colors need to be equals.', 'error')
                    return redirect(url_for('system_app.new_project'))
                elif action == "classes":
                    flash(u'The same class occurs more than one time.', 'error')
                    return redirect(url_for('system_app.new_project'))
                elif action == "colors":
                    flash(u'The same color occurs more than one time.', 'error')
                    return redirect(url_for('system_app.new_project'))
            except:
                flash(u'There is already a project named %s.' % form.name.data, 'error')
                return redirect(url_for('system_app.new_project'))
        else:
            flash(u'Please, verify the configuration of the mongodb.', 'error')
            return redirect(url_for('system_app.new_project'))
            
    return render_template('system/new_project.html', form=form)
    
@system_app.route('/manager/system/update-project/<projectName>/<up_proj>', methods=['GET', 'POST'])
def update_project(projectName=None, up_proj=None):
    form = ProjectForm()
    
    choices = [(projectName, projectName)]
    form.nameup.choices = choices
    form.nameup.data = projectName
    form.name.data = projectName
    
    if form.nameup.data == None or form.nameup.data == "--Select--":
        flash(u'Please, choose a project.', 'error')
        return redirect(url_for('system_app.update_project'))
    
    user = User.objects.get(pk=session['user_id'])
    try:
        project = Project.objects.get(name=form.nameup.data)
    except:
        flash(u'The project no longer exists, register a new one!', 'warning')
        return redirect(url_for('system_app.new_project'))
    
    if up_proj == "False":
        form.languages.data = form.languages.data.lower()
        form.stop_word.data = form.stop_word.data.lower()
        form.classes.data = form.classes.data.lower()
        
        form.languages.data = project.languages[0].upper()
        for i in range(1, len(project.languages)):
            form.languages.data += ";" + project.languages[i].upper()
            
        form.threshold.data = project.self_training.threshold
        form.is_active.data = project.is_active
        
        form.host.data = project.workflow._global.mongodb.host
        form.database.data = project.workflow._global.mongodb.database
        form.collection.data = project.workflow._global.mongodb.collection
        form.port.data = project.workflow._global.mongodb.port
        
        form.nameTrain.data = project.workflow.trains[0].name
        form.stop_word.data = project.workflow.trains[0].stop_word.upper()
        form.stemmer.data = project.workflow.trains[0].stemmer
        form.remove_stops_first.data = project.workflow.trains[0].remove_stops_first
        
        form.classes.data = project.workflow.trains[0].classes[0]
        for i in range(1,len(project.workflow.trains[0].classes)):
            form.classes.data += ";" + project.workflow.trains[0].classes[i]
        
        form.colors.data = project.workflow.trains[0].colors[0]
        for i in range(1,len(project.workflow.trains[0].colors)):
            form.colors.data += ";" + project.workflow.trains[0].colors[i]
        
        form.classifier.data = project.workflow.trains[0].classifier
        form.ngram_size.data = project.workflow.trains[0].ngram_size
        form.max_words.data = project.workflow.trains[0].max_words
    
    elif up_proj == "True":
        form.languages.data = form.languages.data.lower()
        form.stop_word.data = form.stop_word.data.lower()
        form.threshold.data = float(form.threshold.data)
        form.ngram_size.data = int(form.ngram_size.data)
        form.max_words.data = int(form.max_words.data)
        form.port.data = int(form.port.data)
        
        if form.validate_on_submit():
            if user.username in project.users:
                if form.validate_connection(form.host, form.database, form.collection, form.port):
                    try:
                        action, success =   form.update(form.name, form.host, form.database,
                                            form.collection, form.port, form.nameTrain,
                                            form.stop_word, form.remove_stops_first,
                                            form.stemmer, form.classes, form.colors, form.classifier, 
                                            form.ngram_size, form.max_words, form.languages,
                                            form.threshold, form.is_active, project)
                        if success:
                            flash(u'Project successfully updated!', 'success')
                            if form.is_active.data:
                                flash(u'In up to 1 minute the project will be active for classification.', 'warning')
                            else:
                                flash(u'In up to 1 minute the project will be disabled for classification.', 'warning')
                            return redirect(url_for('system_app.update_project', projectName=projectName, up_proj=False))
                        elif action == "length":
                            flash(u'The length of the classes and colors need to be equals.', 'error')
                            return redirect(url_for('system_app.update_project', projectName=projectName, up_proj=False))
                        elif action == "classes":
                            flash(u'The same class occurs more than one time.', 'error')
                            return redirect(url_for('system_app.update_project', projectName=projectName, up_proj=False))
                        elif action == "colors":
                            flash(u'The same color occurs more than one time.', 'error')
                            return redirect(url_for('system_app.update_project', projectName=projectName, up_proj=False))
                    except:
                        flash(u'Was not possible to update the project ' + form.nameup.data, 'error')
                        return redirect(url_for('system_app.update_project', projectName=projectName, up_proj=False))
                else:
                    flash(u'Please, verify the configuration of the mongodb.', 'error')
                    return redirect(url_for('system_app.update_project', projectName=projectName, up_proj=False))
            else:
                flash(u'You do not have permission to update the project ' + form.nameup.data, 'error')
                return redirect(url_for('system_app.update_project', projectName=projectName, up_proj=False))
    else:
        flash(u"Don't try to crash the system!", 'error')
        return redirect(url_for('system_app.update_project', projectName=projectName, up_proj=False))
    return render_template('system/update_project.html', projectName=projectName, up_proj=False, form=form)

@system_app.route('/manager/system/delete-project/<project_name>', methods=['GET', 'POST'])
def delete_project(project_name):
    projects = Project.objects.get(name=project_name)
    projects.delete_project()
    
    users = User.objects.filter()
    for user in users:
        user.remove_project(project_name)
                
    flash(u'Project successfully deleted!', 'success')
    return redirect(url_for('system_app.load_project'))

@system_app.route('/manager/system/delete-project', methods=['GET', 'POST'])
def del_page():
    form = ProjectForm()
    projects = Project.objects.filter()
    choices = [("--Select--", "--Select--")]
    for project in projects:
        choices.append((project.name, project.name))
    form.nameup.choices = choices
    return render_template('system/delete_project.html', form=form)

@system_app.route('/manager/system/load-project/', methods=['GET', 'POST'])
def load_project():
    form = ProjectForm()
    
    projects = Project.objects.filter()
    choices = [("--Select--", "--Select--")]
    for project in projects:
        choices.append((project.name, project.name))
    form.nameup.choices = choices
    
    if form.nameup.data == None or form.nameup.data == "--Select--":
        flash(u'Please, choose a project.', 'error')
        return redirect(url_for('system_app.load_project'))
    
    return render_template('system/load_project.html', form=form)


