import datetime as dt 
import os 
import json 
from random import random 

import dropbox 
import dash
from dash import html
from dash import dcc
from flask import Flask, render_template, session, request
import plotly.express as px
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

def get_index_kwargs(): 
    return {
        'stats': STATS, 
        'records': records, 
        'today': today(),
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
    print("Posted")
    print(json.dumps(request.json, indent=1))

    return render_template('index.html', **get_index_kwargs())


@app.route('/authorized', methods=['POST'])
def login(): 
    usr = request.form['first']
    pwd = request.form['password']
    
    session['username'] = usr 
    session['usr_token'] = hash(usr + pwd)
    print(session['usr_token'])

    # TODO include logic to validate login 
    return render_template('index.html', **get_index_kwargs())


@app.route('/')
def index():
    session.clear()
    if session.get('usr_token'):
        session['df'] = records
        return render_template('index.html', **get_index_kwargs())
    else: 
        session['df'] = records
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
app.run(debug=True)