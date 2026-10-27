
# -*- encoding: utf-8 -*-
"""
License: MIT
Copyright (c) 2019 - present AppSeed.us
"""

from app.home import blueprint
from flask import render_template, redirect, url_for, request, session, Response
from functools import wraps
from flask_login import login_required, current_user
from app import login_manager
from jinja2 import TemplateNotFound
import requests
from flask import current_app as app
from app.base.forms import UpdateAccountForm
from app.base.models import User
from app import db
from requests.exceptions import ConnectionError
import json
import subprocess

# installed by the FreeTAKHub installer; the UI runs as root on the FTS host
FTS_UPDATE = "/usr/local/sbin/fts-update"

@login_manager.user_loader
def load_user(user_id):
    return User.query.filter_by(uid=user_id).first()

def fts_url(path):
    return f"{app.config['PROTOCOL']}://{app.config['IP']}:{app.config['PORT']}{path}"

def fts_headers():
    return {'Authorization': app.config['APIKEY']}

def portal_request_allowed():
    # a cross-site form can't send this header
    return request.headers.get("X-Portal") == "1"

def admin_required(view):
    """admin pages embed FTS's API and websocket keys; everyone else gets the user portal"""
    @wraps(view)
    @login_required
    def wrapper(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for('home_blueprint.portal'))
        return view(*args, **kwargs)
    return wrapper

def run_fts_update(*args):
    """call the fts-update helper, which prints JSON"""
    try:
        result = subprocess.run([FTS_UPDATE, *args], capture_output=True, text=True, timeout=60)
        return json.loads(result.stdout)
    except (OSError, ValueError, subprocess.TimeoutExpired) as e:
        return {"error": f"fts-update is not available: {e}"}

@blueprint.route('/update/status')
@admin_required
def update_status():
    return run_fts_update("status")

@blueprint.route('/update/start', methods=['POST'])
@admin_required
def update_start():
    # a cross-site form can't send this header, so another page can't make a
    # logged-in admin's browser start an update
    if request.headers.get("X-FTS-Update") != "1":
        return {"error": "missing X-FTS-Update header"}, 400
    return run_fts_update("start", *(["--rollback"] if request.args.get("rollback") == "1" else []))

@blueprint.route('/index')
@admin_required
def index():
    
    if not current_user.is_authenticated:
       return redirect(url_for('base_blueprint.login'))

    return render_template('index.html', segment='index',
    websocketkey=app.config['WEBSOCKETKEY'], apikey=app.config['APIKEY'], port=app.config['PORT'], protocol=app.config['PROTOCOL'], ip=app.config['IP'],
    userinterval=app.config['USERINTERVAL'],serverhealthinterval=app.config['SERVERHEALTHINTERVAL'], sysstatusinterval=app.config['SYSSTATUSINTERVAL']
    )


@blueprint.route('/mission')
@admin_required
def missionApi():
    
    headers = {'Authorization': app.config['APIKEY']}

    try:
        json_data = requests.get(f"{app.config['PROTOCOL']}://{app.config['IP']}:{app.config['PORT']}/DataPackageTable", headers= headers).json()
    except Exception as e:
        print(e)
        json_data = {'json_list': []}
    
    try:
        mission_json_data = requests.get(f"{app.config['PROTOCOL']}://{app.config['IP']}:{app.config['PORT']}/MissionTable", headers= headers).json()
    except Exception as e:
        print(e)
        mission_json_data = {'data': []}

    try:
        excheck_json_data = requests.get(f"{app.config['PROTOCOL']}://{app.config['IP']}:{app.config['PORT']}/ExCheckTable", headers= headers).json()
    except Exception as e:
        print(e)
        excheck_json_data = {'data': []}

    try:
        outgoing_federation_json_data = requests.get(f"{app.config['PROTOCOL']}://{app.config['IP']}:{app.config['PORT']}/FederationTable", headers= headers).json()
    except Exception as e:
        print(e)
        outgoing_federation_json_data = {'federations': []}
   
    try:
        requests.get(f"{app.config['PROTOCOL']}://{app.config['IP']}:{app.config['PORT']}", headers= headers)
    except ConnectionError:
        return render_template('mission.html', msg=f'FTS Server is not reachable at {app.config.get("IP", "IP NOT SET!")}', segment="mission", 
                                json_data = {},
                                mission_json_data = {'data': []},
                                excheck_json_data = {},
                                outgoing_federation_json_data = {'federations': []},
                                websocketkey=app.config['WEBSOCKETKEY'], apikey=app.config['APIKEY'], port=app.config['PORT'], protocol=app.config['PROTOCOL'], ip=app.config['IP'])

    return render_template('mission.html', json_data = json_data['json_list'], 
    mission_json_data = mission_json_data['data'],
    excheck_json_data = excheck_json_data['data'][0]['contents'],
    outgoing_federation_json_data = outgoing_federation_json_data['federations'],
    segment = "mission",
    websocketkey=app.config['WEBSOCKETKEY'], apikey=app.config['APIKEY'], port=app.config['PORT'], protocol=app.config['PROTOCOL'], ip=app.config['IP'],
    datapackagesizelimit=app.config['DATAPACKAGESIZELIMIT']
    
     )





@blueprint.route('/connect')
@admin_required
def connectApi():
    headers = {'Authorization': app.config['APIKEY']}
    try:
        json_data = requests.get(f"{app.config['PROTOCOL']}://{app.config['IP']}:{app.config['PORT']}/ManageEmergency/getEmergency", headers= headers)
    except ConnectionError:
        return render_template('connect.html', msg=f'FTS Server is not reachable at {app.config.get("IP", "IP NOT SET!")}', segment="connect", 
                                json_data = {'json_list': []},
                                websocketkey=app.config['WEBSOCKETKEY'], apikey=app.config['APIKEY'], port=app.config['PORT'], protocol=app.config['PROTOCOL'], ip=app.config['IP'])
    json_data = json_data.json()
    
    return render_template('connect.html', json_data = json_data['json_list'], segment="connect",
    websocketkey=app.config['WEBSOCKETKEY'], apikey=app.config['APIKEY'], port=app.config['PORT'], protocol=app.config['PROTOCOL'], ip=app.config['IP'])     


@blueprint.route('/configure')
@admin_required
def configureApi():
    headers = {'Authorization': app.config['APIKEY']}
    try:
        outgoing_federation_json_data = requests.get(f"{app.config['PROTOCOL']}://{app.config['IP']}:{app.config['PORT']}/FederationTable", headers= headers).json()
    except ConnectionError:
        return render_template('configure.html', msg=f'FTS Server is not reachable at {app.config.get("IP", "IP NOT SET!")}', segment="configure", 
                                outgoing_federation_json_data = {'federations': []},
                                websocketkey=app.config['WEBSOCKETKEY'], apikey=app.config['APIKEY'], port=app.config['PORT'], protocol=app.config['PROTOCOL'], ip=app.config['IP'])

    return render_template('configure.html', segment="configure", 
    outgoing_federation_json_data = outgoing_federation_json_data['federations'],
    websocketkey=app.config['WEBSOCKETKEY'], apikey=app.config['APIKEY'], port=app.config['PORT'], protocol=app.config['PROTOCOL'], ip=app.config['IP'])

@blueprint.route('/users')
@admin_required
def usersApi():
    return render_template('users.html', segment="users", 
    websocketkey=app.config['WEBSOCKETKEY'], apikey=app.config['APIKEY'], port=app.config['PORT'], protocol=app.config['PROTOCOL'], ip=app.config['IP'])     
      
@blueprint.route('/video')
@admin_required
def videoApi():
    return render_template('video.html', segment="video",
    websocketkey=app.config['WEBSOCKETKEY'], apikey=app.config['APIKEY'], port=app.config['PORT'], protocol=app.config['PROTOCOL'], ip=app.config['IP'])

@blueprint.route('/about')
@admin_required
def aboutApi():
    return render_template('about.html', segment="about", uiversion=app.config['UIVERSION'],
    websocketkey=app.config['WEBSOCKETKEY'], apikey=app.config['APIKEY'], port=app.config['PORT'], protocol=app.config['PROTOCOL'], ip=app.config['IP'])     

@blueprint.route('/webmap')
@admin_required
def webmapApi():
    return render_template('webmap.html', segment="webmap", uiversion=app.config['UIVERSION'],
    websocketkey=app.config['WEBSOCKETKEY'], apikey=app.config['APIKEY'],
    ip=app.config['IP'], protocol=app.config['PROTOCOL'], port=app.config['PORT'],
    webmapip=app.config['WEBMAPIP'], webmapport=app.config['WEBMAPPORT'], webmapprotocol=app.config['WEBMAPPROTOCOL'])

@blueprint.route('/page-user', methods=['GET', 'POST'])
@admin_required
def page_user():
    import copy
    update_account_form = UpdateAccountForm(request.form)
    y = request.form
    if "update" in request.form:
        password = request.form['password']
        token = request.form['token']
        group = request.form['group']
        user = User.query.filter_by(uid=current_user.uid).first()
        user.token = token
        user.group = group
        user.password = password
        db.session.add(user)
        db.session.commit()
        return render_template('page-user.html', form=update_account_form)

    else:
        uid = copy.copy(current_user.uid)
        return render_template('page-user.html', form=update_account_form, ip=app.config["IP"], port=app.config["PORT"], websocketkey=app.config['WEBSOCKETKEY'], apikey=app.config['APIKEY'], user_id=uid)

@blueprint.route('/mission/<hash>/qr')
@admin_required
def qr(hash):
    qr_link = 'http://' + app.config['IP'] + ':' + app.config['PORT'] + '/GenerateQR'+ '?datapackage_hash=' + hash
    return render_template('qr.html', qr_link=qr_link)

@blueprint.route('/<template>')
@admin_required
def route_template(template):

    try:

        return render_template(template + '.html')

    except TemplateNotFound:
        return render_template('page-404.html'), 404
    
    except:
        return render_template('page-500.html'), 500




## User portal

@blueprint.route('/portal')
@login_required
def portal():
    try:
        account = requests.get(fts_url("/SelfService/account"), params={"uid": current_user.uid},
                               headers=fts_headers(), timeout=10).json()
    except Exception:
        account = {"message": "FTS is not reachable"}
    return render_template('portal.html', account=account, is_admin=session.get("is_admin"))

@blueprint.route('/portal/password', methods=['POST'])
@login_required
def portal_password():
    if not portal_request_allowed():
        return {"message": "missing X-Portal header"}, 400
    data = request.get_json(silent=True) or {}
    try:
        reply = requests.post(fts_url("/SelfService/password"), headers=fts_headers(), timeout=10,
                              json={"uid": current_user.uid, "current": data.get("current", ""), "new": data.get("new", "")})
        return reply.json(), reply.status_code
    except Exception:
        return {"message": "FTS is not reachable"}, 502

@blueprint.route('/portal/qr', methods=['POST'])
@login_required
def portal_qr():
    if not portal_request_allowed():
        return {"message": "missing X-Portal header"}, 400
    data = request.get_json(silent=True) or {}
    try:
        reply = requests.post(fts_url("/SelfService/enrollQR"), headers=fts_headers(), timeout=20,
                              json={"uid": current_user.uid, "app": data.get("app", "atak")})
        return reply.json(), reply.status_code
    except Exception:
        return {"message": "FTS is not reachable"}, 502

@blueprint.route('/portal/package')
@login_required
def portal_package():
    try:
        # the package connects to the address the portal is viewed at
        reply = requests.get(fts_url("/UserPackage"), params={"uid": current_user.uid, "host": request.host.rsplit(":", 1)[0]},
                             headers=fts_headers(), timeout=60)
    except Exception:
        return {"message": "FTS is not reachable"}, 502
    if reply.status_code != 200:
        return reply.json(), reply.status_code
    return Response(reply.content, mimetype="application/zip",
                    headers={"Content-Disposition": reply.headers.get("Content-Disposition", "attachment; filename=package.zip")})
