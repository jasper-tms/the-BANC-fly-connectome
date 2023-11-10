#!/usr/bin/env python3
"""
This Slack app uses the "socket mode" feature of Slack's Bolt framework.
This allows the app to receive messages from Slack without needing to
have your own public server. Some useful links that describe this:
- https://api.slack.com/apis/connections/socket
- https://api.slack.com/apis/connections/events-api

--- Getting started ---
Install the slack bolt python package: `pip install slack-bolt`

View and configure your Slack app: https://api.slack.com/apps
- In Features > App Home > Show Tabs, select "Allow users to send
    Slash commands and messages from the messages tab" to enable DMs.
- In Settings > Socket Mode, enable Socket Mode. Create a token with
    connections:write permissions if prompted to. You can name the token
    anything, but 'websockets' is a reasonable choice.
- In Features > Event Subscriptions, toggle Enable Events on. Then
    open "Subscribe to bot events" and add the following events:
      message.im
    Press "Save Changes" when done.

Get your app's tokens:
- From Settings > Basic Information > App Credentials, copy the Signing Secret.
    Add it to your shell environment by adding a line like this to your shell
    startup file (e.g. ~/.bashrc, ~/.zshrc):
      export SLACK_BOT_SIGNING_SECRET=abcdef1234567890...
- From Settings > Basic Information > App-Level Tokens, click on the token you
    made earlier (e.g. 'websockets'). Copy the token. Add it to your shell
    startup file (e.g. ~/.bashrc, ~/.zshrc):
      export SLACK_BOT_WEBSOCKETS_TOKEN=xapp-abcdef1234567890...
- From Features > OAuth & Permissions > OAuth Tokens for Your Workspace,
    copy your Bot User OAuth Token and add it to your shell startup file:
      export SLACK_BOT_TOKEN=xoxb-abcdef1234567890...

Then run this script with `python proofreading_status_bot.py` to start
listening for events triggered by users interacting with your Slack app.

If you want to keep this running constantly so that the app is always
listening and responding, you can run this script in the background
using a utility like `screen`.
"""

import os
import sys
import time
from datetime import datetime

import numpy as np
import pandas as pd
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from caveclient import CAVEclient


# Setup
verbosity = 2

caveclient = CAVEclient('fanc_production_mar2021')
info = caveclient.info.get_datastack_info()

app = App(token=os.environ['SLACK_TOKEN_FANC_SOMABOT'],
          signing_secret=os.environ['SLACK_SIGNING_SECRET_FANC_SOMABOT'])
handler = SocketModeHandler(app, os.environ['SLACK_TOKEN_FANC_SOMABOT_WEBSOCKETS'])

def show_help():
    return ("Send me a message with one of the following formats:\n\n"
            "`@soma-bot T1` or `@soma-bot T2` or `@soma-bot T3`\n"
            "This will request a list of orphaned somas within the"
            " top third, middle third, or bottom third of the VNC."
            " (These roughly correspond to T1+wing neuropil, T2+haltere"
            " neuropil, and T3+abdominal ganglion.)\n\n"
            "`@soma-bot`\n"
            "This will request a list of orphaned somas using the"
            " default settings, which currently is to find somas in"
            " the top third or middle third of the VNC.")


@app.event("message")
def direct_message(message, say):
    """
    Slack servers trigger this function when a user sends a direct message to the bot.

    'message' is a dictionary containing information about the message.
    'say' is a function that can be used to send a message back to the user.
    """
    print(datetime.now().strftime('%A %Y-%h-%d %H:%M:%S'))
    if message.get('channel_type', None) != 'im':
        # Skip if this is not a direct message
        return
    if message.get('subtype', None):
        # Skip if this is a system message (not something posted by a user)
        return
    if message.get('thread_ts', None):
        # Skip if this message has a reply already
        return
    if 'bot_id' in message:
        # Skip if this message was posted by another bot
        return

    response = None
    if 'help' in message['text'].lower() or not message['text'].startswith('<@U04EW9C2MEX>'):
        response = show_help()

    if verbosity >= 2:
        print('Processing message:', message)
    elif verbosity >= 1:
        print('Processing message with timestamp', message['ts'])

    kwargs = dict()
    if 'T1' in message['text'] and 'T2' not in message['text']:
        kwargs['y_range'] = 'T1'
        kwargs['query_size'] = 60
    elif 'T2' in message['text'] and 'T1' not in message['text']:
        kwargs['y_range'] = 'T2'
    elif 'T3' in message['text']:
        kwargs['y_range'] = 'T3'

    if response is None:
        orphaned_somas = fetch_orphaned_somas(**kwargs).values
        response = (f"Segment IDs: {list(orphaned_somas[:, 0])}\n"
                    f"Synapse counts: {list(orphaned_somas[:, 1])}")
    if fake:
        print('FAKE: Would post response:', response)
        return
    if verbosity >= 1:
        print('Posting response:', response)
    if len(response) > 1500:
        say(response, thread_ts=message['ts'])
    else:
        say(response)


def fetch_orphaned_somas(y_range=[0, 160000], query_size=30, synapse_count_threshold=50):
    """
    Get a list of somas that have few postsynaptic sites associated with
    them, which likely means they are falsely split from their arbor and
    they are in need of a few merge operations.

    query_size determines how many somas to select randomly from the
    full soma table for inspection. Then only the subset of those somas
    that have a small enough synapse count will be returned. As such,
    different calls to this function will return different numbers of
    somas. As of Dec 2022, calling this function with the default
    parameters typically returns between 2 and 8 somas.

    Arguments
    ---------
    y_range : list of ints (default [0, 160000]) or str
      If str, must be 'T1', 'T2', or 'T3' to select these coordinate ranges:
        T1 -> [     0, 120000]
        T2 -> [120000, 160000]
        T3 -> [160000, 223000]
      Only inspect somas with y coordinate between y_range[0] and
      y_range[1]. This allows us to prioritize connecting somas to
      arbors in specific regions of the dataset. The default parameters
      currently specify to look in the anterior half of the VNC (T1 &
      wing & T2 neuropils), where most people in the community are
      currently focused.
      Some useful landmark values:
        120000 : Just below T1
        160000 : Just below T2
        223000 : The bottom of the dataset

    query_size : int (default 30)
      Request postsynaptic site counts for this many somas. Larger queries take
      more time.

    synapse_count_threshold : int (default 50)
      Among the queried somas, only return ones that have fewer than this
      number of postsynaptic sites. 50 seems to be a pretty reasonable cutoff,
      so it's unlikely users would find it useful to change this.

    Returns
    -------
    A DataFrame with 2 columns named 'pt_root_id' and 'synapse_counts'. Each row
    represents the segment ID and number of synapses for a different object.
    """
    if isinstance(y_range, str):
        y_range = {
            'T1': [     0, 120000],
            'T2': [120000, 160000],
            'T3': [160000, 223000]
        }[y_range]

    try:
        caveclient.materialize.version = caveclient.materialize.most_recent_version()
    except Exception as e:
        return f"The CAVE server did not respond: `{type(e)}`\n```{e}```"
    somas = caveclient.materialize.query_table(info['soma_table'])
    somas = somas.loc[np.vstack(somas.pt_position)[:, 1] > y_range[0]]
    somas = somas.loc[np.vstack(somas.pt_position)[:, 1] < y_range[1]]
    soma_ids = somas.pt_root_id

    orphaned_somas = pd.Series(dtype='int64')
    iteration = 0
    while orphaned_somas.shape == (0,):
        iteration += 1
        if iteration > 1:
            print(f'Failed to find synapseless somas: Now doing iteration number {iteration}')
        # Get synapses for a random n somas
        soma_ids_sample = soma_ids.sample(query_size)
        synapses = caveclient.materialize.synapse_query(post_ids=soma_ids_sample)

        synapse_counts = pd.Series(
            data=synapses.post_pt_root_id.value_counts(),
            index=soma_ids_sample,
            name='synapse_counts'
        ).fillna(0).astype('int64')
        synapse_counts.sort_values(inplace=True)
        orphaned_somas = synapse_counts[synapse_counts <= synapse_count_threshold].reset_index()

    return orphaned_somas


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'fake':
        fake = True
        print('Running in FAKE mode')
    else:
        fake = False
    handler.start()
