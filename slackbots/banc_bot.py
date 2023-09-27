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
- In Settings > Socket Mode, enable Socket Mode. Create a token with
    connections:write permissions if prompted to. You can name the token
    anything, but 'websockets' is a reasonable choice.
- In Features > Event Subscriptions, toggle Enable Events on. Then
    open "Subscribe to bot events" and add the following events:
      message.im
    Press "Save Changes" when done.
- In Features > OAuth & Permissions > Scopes > Bot Token Scopes, add:
    chat:write
- In Features > App Home > Show Tabs, select "Allow users to send
    Slash commands and messages from the messages tab" to enable DMs.

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
    press Install To Workspace if you haven't yet, then copy your Bot User
    OAuth Token and add it to your shell startup file:
      export SLACK_BOT_TOKEN=xoxb-abcdef1234567890...

Then run this script with `python proofreading_status_bot.py` to start
listening for events triggered by users interacting with your Slack app.

If you want to keep this running constantly so that the app is always
listening and responding, you can run this script in the background
using a utility like `screen`.
"""

import os
import sys
import json
import time
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

import banc


# Setup/defaults
verbosity = 2
fake = False
valid_users = ['U348GFY5N']
db_filename = 'the-banc-annotations.parquet'
allowed_annotations = [
    'proofread level 0', 'proofread level 1',
    'spans neck', 'DN soma'
]

caveclient = banc.get_caveclient()

app = App(token=os.environ['SLACK_TOKEN_BANC_BOT'],
          signing_secret=os.environ['SLACK_SIGNING_SECRET_BANC_BOT'])
handler = SocketModeHandler(app, os.environ['SLACK_TOKEN_BANC_BOT_WEBSOCKETS'])


def show_help():
    return (
"""
""")


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
    if 'help' in message['text'].lower():
        response = show_help()
    if message['text'].lower() == 'show':
        response = '```' + str(load()[['tag', 'pt_root_id']]) + '```'

    if verbosity >= 2:
        print('Processing message:', message)
    elif verbosity >= 1:
        print('Processing message with timestamp', message['ts'])

    if response is None:
        response = process_message(message['text'],
                                   message['user'])
    if verbosity >= 1:
        print('Posting response:', response)
    if len(response) > 1500:
        say(response, thread_ts=message['ts'])
    else:
        say(response)


def process_message(message: str, user: str) -> str:
    """
    Process a slack message posted by a user, and return a text response.

    See the `show_help()` function in this module for a description of
    valid message formats and how they will be processed.

    Arguments
    ---------
    message : str
        The user's Slack message.
    user : str
        The user's Slack ID. This is a string that looks like 'ULH2UM0H4'
        and is provided by Slack for each user.

    Returns
    -------
    response : str
        A message to tell the user the information they requested, or to
        tell them the result of the upload operation their message
        triggered, or to describe an error that was encountered when
        processing their message.
    """
    message = message.replace(',', ' ').replace('[', ' ').replace(']', ' ')
    while '  ' in message:
        message = message.replace('  ', ' ')
    words = message.split(' ')
    # Convert first 3 arguments to xyz point coordinate
    try:
        point = [int(float(w)) for w in words[:3]]
    except:
        return 'Could not convert the first 3 words of your message to an xyz coordinate.'
    # Convert remaining arguments to a tag
    tag = ' '.join(words[3:])
    if not (tag in allowed_annotations or banc.annotations.is_valid_annotation(tag)):
        return f'The tag you provided, `{tag}`, is not valid. See https://github.com/jasper-tms/the-BANC-fly-connectome/blob/main/fanc/annotations.py'

    try:
        annotation_id, segid = add_annotation(point, tag, user=user)
    except Exception as e:
        return f'`{type(e).__name__}`: {e}'
    return f'Annotation #{annotation_id}: Labeled segment `{segid}` with `{tag}`'


def initialize() -> pd.DataFrame:
    df = pd.DataFrame({'pt_position': [[137091, 65209, 2873]],
                       'tag': ['neck motor neuron'],
                       'user': 'U348GFY5N'})
    df['pt_position'] = df['pt_position'].astype(object)
    df['tag'] = df['tag'].astype(str)
    df['user'] = df['user'].astype(str)
    lookup_supervoxels(df)
    materialize(df)
    return df


def load(update=True) -> pd.DataFrame:
    if not os.path.exists(db_filename):
        return initialize()
    df = pd.read_parquet(db_filename)
    if update:
        lookup_supervoxels(df)
        materialize(df)
    return df


def lookup_supervoxels(df):
    if 'supervoxel_id' not in df.columns:
        # Add a supervoxel_id column with dtype uint64
        df['supervoxel_id'] = 0
        df['supervoxel_id'] = df['supervoxel_id'].astype(np.uint64)
    needs_lookups = df['supervoxel_id'] == 0
    if needs_lookups.sum() == 0:
        return
    df.loc[needs_lookups, 'supervoxel_id'] = (
        banc.lookup.segid_from_pt_cv(
            np.vstack(df.loc[needs_lookups, 'pt_position']),
            return_roots=False)
    )
    if (df['supervoxel_id'] == 0).any():
        print('WARNING: Some points have supervoxel_id == 0')


def materialize(df):
    df['pt_root_id'] = caveclient.chunkedgraph.get_roots(df['supervoxel_id'])


def add_annotation(pt_position: 'xyz coordinate',
                   annotation: str,
                   user: str) -> None:
    """
    Returns
    -------
    2-tuple of (annotation_id, segid of annotated neuron)
    """
    if user not in valid_users:
        raise ValueError(f'User {user} is not a valid user.')
    assert isinstance(pt_position, list)
    assert len(pt_position) == 3
    assert isinstance(annotation, str)
    assert isinstance(user, str)

    df = load()

    df.loc[len(df)] = [pt_position, annotation, user, np.uint64(0), np.uint64(0)]
    lookup_supervoxels(df)
    materialize(df)
    print(df)
    # Check that pt_position is in the segmentation
    if df.at[len(df)-1, 'pt_root_id'] == 0:
        df.drop(len(df)-1, inplace=True)
        print(df)
        raise ValueError(f'Point {pt_position} is not in the segmentation.')
    # Check that the annotation is not already in the database for this segment
    if ((df['pt_root_id'] == df.at[len(df)-1, 'pt_root_id']) &
        (df['tag'] == df.at[len(df)-1, 'tag'])).sum() > 1:
        error_message = (f'Annotation `{df.at[len(df)-1, "tag"]}` already exists '
                         f'for segment {df.at[len(df)-1, "pt_root_id"]}.')
        df.drop(len(df)-1, inplace=True)
        print(df)
        raise ValueError(error_message)

    if fake:
        print('FAKE mode: not writing to database')
    else:
        df[['pt_position', 'tag', 'user', 'supervoxel_id']].to_parquet(db_filename)
    return (df.loc[len(df)-1].name, df.at[len(df)-1, 'pt_root_id'])


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'fake':
        fake = True
        print('Running in FAKE mode')
    handler.start()
