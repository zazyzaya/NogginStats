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
dbx = dropbox.Dropbox(
    oauth2_refresh_token=secret['refresh-token'],
    app_key=secret['db-key'],
    app_secret=secret['db-secret']
)

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET', 'dev_server')
app.config['TEMPLATES_AUTO_RELOAD'] = True

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

'''
test_data = []
for i in range(10): 
    datum = dict()
    d = dt.datetime.today() + dt.timedelta(days=(-(i+1)))
    datum['stat-date'] = d.strftime('%Y-%m-%d')
    for _,k,b in STATS: 
        if b: 
            datum[f'{k}-checked'] = random() > 0.5 
            datum[f'{k}-txt'] = f'Test text for {k}'
        else: 
            datum[f'{k}-range'] = int((random() * 10) + 1)
    test_data.append(datum)

test_df = pd.DataFrame(test_data)
test_df = test_df.sort_values(by='stat-date', ascending=False)
records = test_df.to_dict(orient='records')

TEST_USR = 'admin'
TEST_PWD = 'admin'
pwd = str(stable_hash(TEST_USR + TEST_PWD))
print('password:', pwd)
crp.to_encrypted(test_df, pwd, f'{TEST_USR}.crypt')
'''

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
    df = pd.DataFrame(df)
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

    # Overwrite existing
    if todays_log.shape[0]: 
        idx = todays_log.item()
        df.loc[idx,row.keys()] = row.values()

    # Create new
    else: 
        df = pd.concat([pd.DataFrame([row]), df])

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

@app.route('/register', methods=['POST'])
def register_acct(): 
    usr = request.json['username']
    pwd = request.json['password']
    pwd2 = request.json['password2']
    acc = request.json['access-code']

    if acc.lower() != secret['access-code']: 
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
    usr = request.json['first']
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
    #session['df'] = records
    #return render_template('index.html', **get_index_kwargs())
    if session.get('usr_token'):
        try: 
            df = crp.read_encrypted(f'{session["username"]}.crypt', session['usr_token'])
        except cryptography.fernet.InvalidToken: 
            return render_template('login.html', failed_reason='Incorrect old password')

        session['df'] = df.to_dict(orient='records')
        return render_template('index.html', **get_index_kwargs())
    else: 
        return render_template('login.html')


dash_app = dash.Dash(server=app, url_base_pathname="/dash/")
dash_app.layout = html.Div([])

FIRST = True
if __name__ == '__main__': 
    app.run(debug=True)