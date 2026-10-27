# -*- encoding: utf-8 -*-
"""
License: MIT
Copyright (c) 2019 - present AppSeed.us
"""

from flask import jsonify, render_template, redirect, request, session, url_for
from flask_login import (
    current_user,
    login_required,
    login_user,
    logout_user
)

from app import db, login_manager
from app.base import blueprint
from app.base.forms import LoginForm, CreateAccountForm
from app.base.models import User
from flask import current_app as app
from app.base.util import verify_pass
from requests.exceptions import ConnectionError

@blueprint.route('/')
def route_default():
    return redirect(url_for('base_blueprint.login'))

@blueprint.route('/error-<error>')
def route_errors(error):
    return render_template('errors/{}.html'.format(error))

## Login & Registration

@blueprint.route('/login', methods=['GET', 'POST'])
def login():
    login_form = LoginForm(request.form)
    if 'login' in request.form:
        import requests
        # read form data
        username = request.form['username']
        password = request.form['password']

        # Locate user
        try:
            # portal=1: non-admins may sign in too, to the user portal only
            user = requests.get(f"{app.config['PROTOCOL']}://{app.config['IP']}:{app.config['PORT']}/AuthenticateUser", params={"username": username, "password": password, "portal": "1"}, headers={"Authorization": f"{app.config['APIKEY']}"})
        except ConnectionError:
            return render_template('login/login.html', msg=f'FTS Server is not reachable at {app.config.get("IP", "IP NOT SET!")}', form=login_form)
        # FTS answers 200 {uid} for admins, 403 for device-only accounts and
        # 401 for wrong credentials; anything else must not sign anyone in
        if user.status_code == 403:
            # "this account has no web UI access" or "this account is disabled"
            try:
                reason = user.json().get("message") or "this account has no web UI access"
            except ValueError:
                reason = "this account has no web UI access"
            return render_template('login/login.html', msg=reason[:1].upper() + reason[1:], form=login_form)
        try:
            user = user.json() if user.status_code == 200 else None
        except ValueError:
            user = None

        # Check the password
        if user and user.get("uid"):
            # FTS versions without the user portal only accept admins and don't say so
            user_admin = user.get("admin", True) is True
            user = User(uid = user["uid"])
            db.session.add(user)
            db.session.commit()
            login_user(user)
            # admin pages embed FTS's API and websocket keys, so only admins get them
            session["is_admin"] = bool(user_admin)
            z = current_user
            url = url_for('base_blueprint.route_default') if user_admin else url_for('home_blueprint.portal')
            new_redr = redirect(url)
            return new_redr

        # Something (user or pass) is not ok
        return render_template( 'login/login.html', msg='Wrong user or password', form=login_form)
    z = current_user
    if not current_user.is_authenticated:
        return render_template( 'login/login.html',
                                form=login_form)
    return redirect(url_for('home_blueprint.index'))

@blueprint.route('/logout')
def logout():
    session.pop("is_admin", None)
    db.session.delete(current_user)
    db.session.commit()
    logout_user()

    return redirect(url_for('base_blueprint.login'))

@blueprint.route('/shutdown')
@login_required
def shutdown():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()
    return 'Server shutting down...'

## Errors

@login_manager.unauthorized_handler
def unauthorized_handler():
    return render_template('errors/403.html'), 403

@blueprint.errorhandler(403)
def access_forbidden(error):
    return render_template('errors/403.html'), 403

@blueprint.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@blueprint.errorhandler(500)
def internal_error(error):
    return render_template('errors/500.html'), 500
