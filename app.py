import cryptography
import datetime as dt 
import os 
import json 
from random import random 

import dropbox 
import dash
from dash import html
from dash import dcc
from flask import Flask, render_template, session, request, url_for, redirect
import plotly.express as px
import pandas as pd 
import cryptpandas as crp

from secret import secret

# Annoyingly, python hashes are inconsistant
import hashlib
from operator import xor
from struct import unpack

def stable_hash(a_string):
    sha256 = hashlib.sha256()
    sha256.update(bytes(a_string, "UTF-8"))
    digest = sha256.digest()
    h = 0
    #
    for index in range(0, len(digest) >> 3):
        index8 = index << 3
        bytes8 = digest[index8 : index8 + 8]
        i = unpack('q', bytes8)[0]
        h = xor(h, i)
    #
    return h

# TODO get from env variable 
dbx = dropbox.Dropbox(secret['db-token'])

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

def preload_journal(): 
    preload = dict()
    
    df = pd.DataFrame(session['df'])
    todays_log = (df['stat-date'] == today()).to_numpy().nonzero()[0]

    if todays_log.shape[0] == 0: 
        for _,k,b in STATS: 
            if b: 
                preload[f'{k}-checked'] = False
                preload[f'{k}-txt'] = ''
            else: 
                preload[f'{k}-range'] = 5
    else: 
        preload = df.iloc[todays_log.item()].to_dict()
        print(preload)

    return preload


def get_index_kwargs(): 
    return {
        'stats': STATS, 
        'records': session['df'], 
        'today': today(),
        'journal_content': preload_journal(),
        'range_fig': build_range_fig(pd.DataFrame(session['df'])).to_html(
            full_html=False,
            include_plotlyjs='cdn',
            config={'displayModeBar': False},
            default_width='100%',
            default_height='100%'
        ),
        'cat_fig': build_catagorical(pd.DataFrame(session['df'])).to_html(
            full_html=False,
            include_plotlyjs='cdn',
            config={'displayModeBar': False},
            default_width='100%',
            default_height='100%'
        ),
    }


@app.route('/submit', methods=['POST'])
def submit(): 
    print(json.dumps(request.json, indent=1))
    
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

    # Write local
    crp.to_encrypted(df, session['usr_token'], f'{session["username"]}.crypt')

    # Update in-memory df 
    session['df'] = df.to_dict(orient='records')

    # TODO write to cloud

    return redirect(url_for('index'))


@app.route('/authorized', methods=['POST'])
def login(): 
    usr = request.form['first']
    pwd = request.form['password']
    
    session['username'] = usr 
    session['usr_token'] = str(stable_hash(usr + pwd))

    try: 
        print("Correct pwd")
        df = crp.read_encrypted(f'{session["username"]}.crypt', session['usr_token'])
    except cryptography.fernet.InvalidToken: 
        print("Wrong pwd")
        return render_template('login.html', failed_reason='Incorrect old password')

    session['df'] = df.to_dict(orient='records')

    return redirect(url_for('index'))


@app.route('/reset_pwd_submit', methods=['POST'])
def reset_pwd_submit(): 
    old_pwd = request.json['old_pwd']
    new_pwd = request.json['password']

    if new_pwd != request.json['password2']: 
        return "Passwords don't match"

    pwd = str(stable_hash(session['username'] + old_pwd))
    
    try: 
        crp.read_encrypted(f'{session["username"]}.crypt', pwd)
    except cryptography.fernet.InvalidToken: 
        return 'Incorrect old password'

    pwd = str(stable_hash(session['username'] + new_pwd))
    session['usr_token'] = pwd 
    df = pd.DataFrame(session['df'])
    crp.to_encrypted(df, pwd, f'{session["username"]}.crypt')
    # TODO Reupload to cloud 

    return redirect(url_for('index'))


@app.route('/pwd_reset')
def pwd_reset_screen(): 
    return render_template('pwd_reset.html')


@app.route('/')
def index():
    #session.clear()
    #session['df'] = records
    #return render_template('index.html', **get_index_kwargs())
    print("routed to index")
    if session.get('usr_token'):
        try: 
            df = crp.read_encrypted(f'{session["username"]}.crypt', session['usr_token'])
        except cryptography.fernet.InvalidToken: 
            return render_template('login.html', failed_reason='Incorrect old password')

        session['df'] = df.to_dict(orient='records')
        return render_template('index.html', **get_index_kwargs())
    else: 
        return render_template('login.html')


def build_catagorical(orig_df): 
    cols = [c for c in orig_df.columns if 'checked' in c] 
    df = orig_df[cols + ['stat-date']]
    df = df.replace({True: 1, False: -1})
    col_names =  [c.replace('-checked', '').capitalize() for c in df.columns]

    rolling_avgs = df[cols].rolling(window=5, min_periods=1).mean()
    rolling_avgs['stat-date'] = orig_df['stat-date']
    rolling_avgs.columns = col_names

    heatmap_df = rolling_avgs.set_index('Stat-date').sort_index()

    # If the index is datetime or something else, convert to string for nicer axis ticks
    heatmap_df.index = heatmap_df.index.astype(str)
    heatmap_df_T = heatmap_df.T

    fig = px.imshow(
        heatmap_df_T,
        color_continuous_scale=['red', 'white', 'green'],
        aspect='auto',
        labels=dict(color='Smoothed Score'),
        x=heatmap_df_T.columns,  # Dates on x-axis
        y=heatmap_df_T.index,    # Metrics on y-axis
        title='Daily Checkins (Rolling average)'
    )

    fig.update_layout(
        xaxis_title='Date',
        xaxis=dict(tickmode='array', tickvals=heatmap_df_T.columns),
        coloraxis_showscale=False,
        width=None,
        height=None,
        margin_pad=10,
        plot_bgcolor='rgba(0, 0, 0, 0)'
    )

    return fig 


def build_range_fig(df): 
    range_fig = px.line(
        df, x='stat-date', y=['depression-range', 'anxiety-range'], 
        labels={
            'variable': 'Mood Metric',  
            'value': 'Score',           
            'stat-date': 'Date',
        }
    )

    range_fig.for_each_trace(lambda trace: (
        trace.update(name={
            'depression-range': 'Depression',
            'anxiety-range': 'Anxiety'
        }[trace.name]),
        trace.update(hovertemplate=f"<b>{trace.name}</b><br>Date: %{{x}}<br>Score: %{{y}}<extra></extra>")
    ))

    range_fig.update_layout(
        legend=dict(
            orientation="h",     # horizontal
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5
        ),
        width=None,
        height=None
    )

    return range_fig


dash_app = dash.Dash(server=app, url_base_pathname="/dash/")
dash_app.layout = html.Div([])

if __name__ == '__main__': 
    app.run(debug=True)