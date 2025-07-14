from datetime import datetime 
import os 
import json 
import random 

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

test_df = pd.DataFrame([
    {
        k: random.randint(0,10) if not b else bool(random.randint(0,1))
        for (_, k, b) in STATS
    }
    for _ in range(10)
])

today = lambda : datetime.today().strftime('%Y-%m-%d')

@app.route('/submit', methods=['POST'])
def submit(): 
    print("Posted")
    print(json.dumps(request.json, indent=1))

    return render_template('index.html', stats=STATS)


@app.route('/login', methods=['POST'])
def login(): 
    usr = request.form['first']
    pwd = request.form['password']
    
    session['username'] = usr 
    session['usr_token'] = hash(usr + pwd)
    print(session['usr_token'])

    # TODO include logic to validate login 
    return render_template('index.html', stats=STATS, today=today())


@app.route('/')
def index():
    session.clear()
    if session.get('usr_token'):
        return render_template('index.html', stats=STATS, today=today())
    else: 
        return render_template('login.html')

app.run(debug=True)