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
from accounts.models import User, Control
from accounts.forms import (
    LoginForm, SignupForm, SignupConfirmForm, RecoverPasswordForm,
    RecoverPasswordConfirmForm
)
from common.utils import get_signer
from flask_mail import Message
from application import mail
import hashlib

accounts_app = Blueprint('accounts_app', __name__)


@accounts_app.before_app_request
def load_user():
    g.user = None
    
    if 'user_id' in session:
        try:
            g.user = User.objects.get(pk=session['user_id'])
            
            m = hashlib.md5()
            m.update(g.user.email.encode('utf8'))
            g.hash = m.hexdigest()
        except:
            pass


@accounts_app.route('/login/', methods=['GET', 'POST'])
def login():
    next = request.values.get('next', '/')
    form = LoginForm()
    form.next.data = next
    if form.validate_on_submit():
        session['user_id'] = unicode(form.user.pk)
        flash(u'Login successfully', 'success')
        
        g.user = User.objects.get(pk=session['user_id'])
        sha1 = hashlib.sha1()
        sha1.update(g.user.email.encode('utf8'))
        g.hash = sha1.hexdigest()
        return redirect(next)
    return render_template('accounts/login.html', form=form)


@accounts_app.route('/logout/')
def logout():
    next = request.args.get('next', '/')
    flash(u'Logout successfully', 'success')
    session.pop('user_id', None)
    return redirect(next)


@accounts_app.route('/signup/', methods=['GET', 'POST'])
def signup():
    form = SignupForm()
    if form.validate_on_submit():
        form.save()
        flash(
            u'Check your email to confirm registration.',
            'success'
        )
        return redirect(url_for('pages_app.index'))
    return render_template('accounts/signup.html', form=form)


@accounts_app.route('/signup/<token>/', methods=['GET', 'POST'])
def signup_confirm(token):
    s = get_signer()
    try:
        signed_data = s.loads(
            token, max_age=current_app.config['PROJECT_SIGNUP_TOKEN_MAX_AGE']
        )
        email = signed_data['email']
        signup = signed_data['signup']
    except:
        flash(u'Invalid activation Link.', 'error')
        return redirect(url_for('accounts_app.signup'))

    if User.objects.filter(email=email):
        flash(u'E-mail in use.', 'error')
        return redirect(url_for('accounts_app.signup'))

    next = request.values.get('next', '/')

    form = SignupConfirmForm()
    form.next.data = next
    if form.validate_on_submit():
        user = form.save(email=email)
        session['user_id'] = unicode(user.pk)
        flash(u'Account registered successfully.', 'success')
        return redirect(next)
    return render_template('accounts/signup_confirm.html', form=form, token=token)


@accounts_app.route('/recover-password/', methods=['GET', 'POST'])
def recover_password():
    form = RecoverPasswordForm()
    if form.validate_on_submit():
        form.save()
        flash(
            u'Check it out at your email instructions for setting a new password.',
            'success'
        )
        return redirect(url_for('pages_app.index'))
    return render_template('accounts/recover_password.html', form=form)

@accounts_app.route('/information/', methods=['GET', 'POST'])
def information():
    g.user = None
    
    if 'user_id' in session:
        
        try:
            g.user = User.objects.get(pk=session['user_id'])
        except:
            pass
        
    return render_template('accounts/information.html')


@accounts_app.route('/manager/', methods=['GET', 'POST'])
def selet():
    g.user = None
    
    if 'user_id' in session:
        try:
            g.user = User.objects.get(pk=session['user_id'])
            if g.user.is_superuser:
                g.all_users = User.objects.get()
            else:
                g.all_users = None                   
        except:
            pass
        
    return render_template('accounts/selet.html')

@accounts_app.route('/manager/users', methods=['GET', 'POST'])
def manager_user():
    g.user = None
    
    if 'user_id' in session:
        try:
            g.user = User.objects.get(pk=session['user_id'])
            if g.user.is_superuser:
                g.all_users = User.objects.filter()
                g._user_label = ["Name", "Login" ,"e-mail", "Institution", "Projects" ,"Active", "Admin", "Remove"]
                g._user_value = []
                #for u in g.all_users:
                    #g._user_value.append([u.name, u.username, u.email, u.is_active, u.is_superuser, "Remove"])
            else:
                g.all_users = None
        except:
            pass
        
    return render_template('accounts/manager_user.html')

@accounts_app.route('/manager/users/change-active/<active>/<username>')
def change_active(active, username):
    g.user = None
    
    if 'user_id' in session:
        try:
            g.user = User.objects.get(pk=session['user_id'])
            if g.user.is_superuser:
                if active == "True":
                    active = True
                else:
                    active = False
                user_to_change = User.objects.filter(username=username).first()
                print user_to_change.username
                user_to_change.is_active = active
                user_to_change.change_active(is_active=active)
        except:
            pass
        
    return redirect(url_for('accounts_app.manager_user'))

@accounts_app.route('/manager/users/change-superuser/<superuser>/<username>')
def change_admin(superuser, username):
    g.user = None
    
    if 'user_id' in session:
        try:
            g.user = User.objects.get(pk=session['user_id'])
            if g.user.is_superuser:
                if superuser == "True":
                    superuser = True
                else:
                    superuser = False
                
                user_to_change = User.objects.filter(username=username).first()
                user_to_change.is_superuser = superuser
                user_to_change.change_superuser(is_superuser=superuser)
                flash(u'The admin privileges for the user %s was changed successfully.' % username, 'success')
                
                new_admin = User.objects.filter(username=username).first()
                
                if superuser and new_admin.is_superuser:
                    try:
                        site_name = current_app.config['PROJECT_SITE_NAME']
                        site_url = current_app.config['PROJECT_SITE_URL']
                        sender = current_app.config['MAIL_DEFAULT_SENDER']
                        # set context to template render
                        context = dict(
                            site_name=site_name,
                            site_url=site_url,
                            assign_by=g.user.name,
                            new_admin_name=new_admin.name
                        )
                        # load template
                        html = render_template(
                            'accounts/emails/admin_confirmation.html', **context
                        )
                        # create and send message
                        msg = Message(
                            u'Confirmation - admin privileges - {0}.'.format(site_name),
                            sender=sender,
                            recipients=[new_admin.email]
                        )
                        msg.html = html
                        mail.send(msg)
                    except:
                        flash(u"Was not possible to send a confirmation by e-mail for the user %s." % new_admin.name, 'error')
            else:
                flash(u"You do not have permission!", 'error')
        except:
            flash(u'Was not possible to assign the admin privileges for the user %s.' % username, 'success')
    
    return redirect(url_for('accounts_app.manager_user'))

@accounts_app.route('/manager/users/remove-user/<username>')
def remove_user(username):
    g.user = None
    if 'user_id' in session:
        try:
            g.user = User.objects.get(pk=session['user_id'])
            if g.user.is_superuser:
                user_to_change = User.objects.filter(username=username).first()
                if not g.user.username == user_to_change.username:
                    user_to_change.delete()
        except:
            pass
        
    return redirect(url_for('accounts_app.manager_user'))

@accounts_app.route('/recover-password/<token>/', methods=['GET', 'POST'])
def recover_password_confirm(token):
    s = get_signer()
    try:
        signed_data = s.loads(
            token, max_age=current_app.config['PROJECT_RECOVER_PASSWORD_TOKEN_MAX_AGE']
        )
        email = signed_data['email']
        recover_password = signed_data['recover-password']
    except:
        flash(u'Invalid Link.', 'error')
        return redirect(url_for('pages_app.index'))

    try:
        user = User.objects.get(email=email)
    except:
        flash(u'E-mail not found.', 'error')
        return redirect(url_for('pages_app.index'))

    form = RecoverPasswordConfirmForm()
    form.user = user
    if form.validate_on_submit():
        user = form.save()
        flash(u'Password set successfully.', 'success')
        return redirect(url_for('accounts_app.login'))
    return render_template(
        'accounts/recover_password_confirm.html',
        form=form, token=token, user=user
    )

@accounts_app.route('/accounts/admin-privileges/', methods=['GET', 'POST'])
def requests_admin_privileges():
    if 'user_id' in session:
        try:
            g.user = User.objects.get(pk=session['user_id'])
        except:
            flash(u"User does't exists.", 'error')
            return redirect(url_for('pages_app.index'))
        
        if not g.user.is_superuser:
            site_name = current_app.config['PROJECT_SITE_NAME']
            site_url = current_app.config['PROJECT_SITE_URL']
            sender = current_app.config['MAIL_DEFAULT_SENDER']
            
            try:
                users = User.objects.filter(is_superuser=True)
                for user in users:
                    # set context to template render
                    context = dict(
                        site_name=site_name,
                        site_url=site_url,
                        admin_name=user.name
                    )
                    # load template
                    html = render_template(
                        'accounts/emails/requests_admin_privileges.html', **context
                    )
                    # create and send message
                    msg = Message(
                        u'Request - admin privileges - {0}.'.format(site_name),
                        sender=sender,
                        recipients=[user.email]
                    )
                    msg.html = html
                    mail.send(msg)
                flash(u"A request was sent for the administrators.", 'success')
            except:
                flash(u"Was not possible to send a request for the administrator.", 'error')
        else:
            flash(u"You are an administrator of the system!", 'warning')
    
    return redirect(url_for('accounts_app.information'))

    
