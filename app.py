import cryptography
import datetime as dt 
import os 
import json 
from random import random 

import dropbox 
import dash
from dash import html
from flask import Flask, render_template, session, request, url_for, redirect, jsonify, make_response

import pandas as pd 
import cryptpandas as crp

from utils import *
from secret import secret

# TODO get from env variable 
'''
dbx = dropbox.Dropbox(
    oauth2_refresh_token=secret['dbx-refresh-token'],
    app_key=secret['dxb-key'],
    app_secret=secret['dxb-secret']
)
'''

dbx = dropbox.Dropbox(
    oauth2_refresh_token=os.environ.get("DBX_REFRESH_TOKEN"),
    app_key=os.environ.get('DBX_KEY'),
    app_secret=os.environ.get('DBX_SECRET')
)

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET', 'dev_server')

STATS = [
    ("Overall feeling \u2014 Depression", 'depression', False),
    ("Overall feeling \u2014 Anxiety", 'anxiety', False),
    ("Movement", 'movement', True), 
    ("Nutrition", 'nutrition', True),
    ("Rest", 'rest', True),
    ("Light Exposure", 'light', True),
    ("Social Connectedness", 'social', True),
    ("Stress Management", 'stress', True)
]

col_order = ['stat-date']
for _,k,b in STATS: 
    if b: 
        col_order.append(f'{k}-checked')
        col_order.append(f'{k}-txt')
    else: 
        col_order.append(f'{k}-range')

today = lambda : dt.datetime.today().strftime('%Y-%m-%d')
make_pwd = lambda usr,pwd: str(stable_hash(usr + pwd))

def preload_journal(day):
    preload = dict()
    
    df = pd.DataFrame(session['df'], columns=col_order)
    todays_log = (df['stat-date'] == day).to_numpy().nonzero()[0]

    if todays_log.shape[0] == 0: 
        for _,k,b in STATS: 
            if b: 
                preload[f'{k}-checked'] = False
                preload[f'{k}-txt'] = ''
            else: 
                preload[f'{k}-range'] = 5
    else: 
        preload = df.iloc[todays_log.item()].to_dict()

    return preload


def get_index_kwargs(day=None): 
    if day is None: 
        day = today()

    df = session['df']
    df = pd.DataFrame(df, columns=col_order)
    df = df.sort_values(by='stat-date', ascending=False)

    session['df'] = df.to_dict(orient='records')

    return {
        'stats': STATS, 
        'records': session['df'], 
        'today': today(),
        'journal_content': preload_journal(day),
        'range_fig': build_range_fig(pd.DataFrame(session['df'], columns=col_order)).to_html(
            full_html=False,
            include_plotlyjs='cdn',
            config={'displayModeBar': False},
            default_width='100%',
            default_height='100%'
        ),
        'cat_fig': build_catagorical(pd.DataFrame(session['df'], columns=col_order)).to_html(
            full_html=False,
            include_plotlyjs='cdn',
            config={'displayModeBar': False},
            default_width='100%',
            default_height='100%'
        ),
    }


@app.route('/submit', methods=['POST'])
def submit(): 
    df = pd.DataFrame(session['df'], columns=col_order)
    row = request.json
    todays_log = (df['stat-date'] == row['stat-date']).to_numpy().nonzero()[0]
    
    refresh_cloud = False 
    new_row = pd.DataFrame([row])

    # Overwrite existing
    if todays_log.shape[0]: 
        idx = todays_log.item()
        new_row = pd.DataFrame([row])
        
        if (df.iloc[idx] != new_row).any(axis=1).item(): 
            df = pd.concat([new_row, df])
            refresh_cloud = True 

    # Create new
    else: 
        df = pd.concat([new_row, df])
        refresh_cloud = True 

    if refresh_cloud: 
        # Update in-memory df 
        session['df'] = df.to_dict(orient='records')

        # Save
        fname = f'{session["username"]}.crypt'
        crp.to_encrypted(df, session['usr_token'], fname)
        with open(fname, 'rb') as f:
            content = f.read()    
            dbx.files_upload(content, f'/NogginStats/{fname}', dropbox.files.WriteMode.overwrite)

    return redirect(request.url)

@app.route("/repop", methods=['POST'])
def repop(): 
    date = request.json['stat-date']
    return make_response(jsonify(preload_journal(date)), 200)

@app.route('/create_acct')
def create_page(): 
    return app.send_static_file('create_acct.html')

@app.route('/log_out')
def logout(): 
    session.clear() 
    return redirect(url_for('index'))

@app.route('/register', methods=['POST'])
def register_acct(): 
    usr = request.json['username'].lower()
    pwd = request.json['password']
    pwd2 = request.json['password2']
    acc = request.json['access-code']

    if acc.lower() != os.environ.get('ACCESS_CODE'): 
        return 'Wrong access code'
    elif pwd != pwd2: 
        return "Passwords don't match"
    else: 
        ret = dbx.files_list_folder('/NogginStats')
        fnames = [r.name for r in ret.entries]
        if usr in fnames: 
            return "Username taken"
    
    # Create empty entry for new user
    fname = f'{usr}.crypt'
    df = pd.DataFrame(columns=col_order)
    crp.to_encrypted(df, make_pwd(usr,pwd), fname)
    
    with open(fname, 'rb') as f:
        content = f.read()
        dbx.files_upload(content, f'/NogginStats/{fname}', dropbox.files.WriteMode.overwrite)

    session['username'] = usr 
    session['df'] = df.to_dict(orient='records')
    session['usr_token'] = make_pwd(usr, pwd)

    return redirect(url_for('index'))


@app.route('/authorize', methods=['POST'])
def login(): 
    usr = request.json['first'].lower()
    pwd = request.json['password']
    
    session['username'] = usr 
    session['usr_token'] = make_pwd(usr, pwd)

    fname = f'{session["username"]}.crypt'
    
    # Pull from cloud if not local 
    if not os.path.exists(fname): 
        try: 
            dbx.files_download_to_file(fname, f'/NogginStats/{fname}')
        except dropbox.exceptions.ApiError:
            return 'Account does not exist'

    try: 
        df = crp.read_encrypted(fname, session['usr_token'])
    except cryptography.fernet.InvalidToken: 
        return 'Incorrect password'

    session['df'] = df.to_dict(orient='records')
    return redirect(url_for('index'))


@app.route('/reset_pwd_submit', methods=['POST'])
def reset_pwd_submit(): 
    old_pwd = request.json['old_pwd']
    new_pwd = request.json['password']

    if new_pwd != request.json['password2']: 
        return "Passwords don't match"

    pwd = make_pwd(session['username'], old_pwd)
    
    try: 
        crp.read_encrypted(f'{session["username"]}.crypt', pwd)
    except cryptography.fernet.InvalidToken: 
        return 'Incorrect old password'

    pwd = make_pwd(session['username'], new_pwd)
    session['usr_token'] = pwd 
    df = pd.DataFrame(session['df'])
    
    fname = f'{session["username"]}.crypt'
    crp.to_encrypted(df, pwd, fname)
    with open(fname, 'rb') as f:
        content = f.read()
        dbx.files_upload(content, f'/NogginStats/{fname}', dropbox.files.WriteMode.overwrite)

    return redirect(url_for('index'))


@app.route('/pwd_reset')
def pwd_reset_screen(): 
    return render_template('pwd_reset.html')


@app.route('/')
def index():
    #session.clear()
    #session['df'] = records
    #return render_template('index.html', **get_index_kwargs())
    if session.get('usr_token'):
        try: 
            df = crp.read_encrypted(f'{session["username"]}.crypt', session['usr_token'])
        except (cryptography.fernet.InvalidToken, FileNotFoundError): 
            return render_template('login.html', failed_reason='Incorrect old password')

        session['df'] = df.to_dict(orient='records')
        return render_template('index.html', **get_index_kwargs())
    else: 
        return render_template('login.html')


dash_app = dash.Dash(server=app, url_base_pathname="/dash/")
dash_app.layout = html.Div([])