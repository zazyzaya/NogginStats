import datetime as dt 
import os 
import json 
from random import random 

import dropbox 
from flask import Flask, render_template, session, url_for, request
import pandas as pd 

from secret import secret

# TODO get from env variable 
dbx = dropbox.Dropbox(secret['db-token'])

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

test_data = []
for i in range(10): 
    datum = dict()
    d = dt.datetime.today() - dt.timedelta(days=(-i))
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

today = lambda : dt.datetime.today().strftime('%Y-%m-%d')

@app.route('/submit', methods=['POST'])
def submit(): 
    print("Posted")
    print(json.dumps(request.json, indent=1))

    return render_template('index.html', stats=STATS, records=records, today=today())


@app.route('/authorized', methods=['POST'])
def login(): 
    usr = request.form['first']
    pwd = request.form['password']
    
    session['username'] = usr 
    session['usr_token'] = hash(usr + pwd)
    print(session['usr_token'])

    # TODO include logic to validate login 
    return render_template('index.html', stats=STATS, today=today(), records=records)


@app.route('/')
def index():
    print 
    return render_template('index.html', stats=STATS, records=records, today=today())

    session.clear()
    if session.get('usr_token'):
        return render_template('index.html', stats=STATS, today=today())
    else: 
        return render_template('login.html')

app.run(debug=True)