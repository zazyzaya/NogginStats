import plotly.express as px

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