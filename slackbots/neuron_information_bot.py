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
import json
import time
from datetime import datetime
from typing import Union

import numpy as np
import pandas as pd
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from caveclient import CAVEclient
import fanc

# Setup
verbosity = 2

caveclient = CAVEclient('fanc_production_mar2021')
table_name = 'neuron_information'

with open('slack_user_permissions.json', 'r') as f:
    permissions = json.load(f)

app = App(token=os.environ['SLACK_TOKEN_FANC_NEURONINFORMATIONBOT'],
          signing_secret=os.environ['SLACK_SIGNING_SECRET_FANC_NEURONINFORMATIONBOT'])
handler = SocketModeHandler(app, os.environ['SLACK_TOKEN_FANC_NEURONINFORMATIONBOT_WEBSOCKETS'])

def show_help():
    return (
"""
Hello! Before using me for the first time, you may want to read through:
- the list of available annotations at https://github.com/htem/FANC_auto_recon/wiki/Neuron-annotations AND
- the description of the "neuron_information" table at https://cave.fanc-fly.com/annotation/views/aligned_volume/fanc_v4/table/neuron_information

You can send me a message that looks like one of the `example messages below` to find certain types of neurons, or get or upload information about specific neurons.

Find neurons with some annotations:
- `get DNx01` -> Get a neuroglancer state showing all neurons currently annotated with "DNx01" (which should be exactly two neurons)
- `get chordotonal neuron and ascending` -> Get a neuroglancer state showing all neurons currently annotated with "chordotonal neuron" and "ascending"
- `get left T1 ventral nerve and motor neuron` -> Get a neuroglancer link that shows all neurons currently annotated with "left T1 ventral nerve" and "motor neuron"
- You can use as many search terms if you want, e.g. `get W and X and Y and Z`

Get information about a specific neuron:
- `648518346486614449?` -> get annotations for segment 648518346486614449
- `648518346486614449? all` -> get extended annotation details for segment 648518346486614449

Upload annotations to a CAVE table that the whole community can benefit from:
- `648518346486614449! primary class > central neuron` -> annotate that the indicated segment's "primary class" is "central neuron" (as opposed to "sensory neuron" or "motor neuron").
- `648518346489818455! left-right projection pattern > bilateral` -> annotate that segment 648518346489818455 projects bilaterally, i.e. has synaptic connections on both sides of the VNC's midplane.
(To upload annotations, Jasper needs to first give you permissions, so send him a message to ask if you're interested.)

This bot is a work in progress - notably, you can't yet annotate most sensory neurons because the `peripheral_nerves` table is not complete yet. This will be addressed at some point.
Feel free to send Jasper any questions or bug reports.
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

    if verbosity >= 2:
        print('Processing message:', message)
    elif verbosity >= 1:
        print('Processing message with timestamp', message['ts'])

    if response is None:
        response = process_message(message['text'],
                                   message['user'],
                                   fake=fake)
    if verbosity >= 1:
        print('Posting response:', response)
    if len(response) > 1500:
        say(response, thread_ts=message['ts'])
    else:
        say(response)


def process_message(message: str, user: str, fake=False) -> str:
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
    if message.startswith(('get ', 'find ')):
        try:
            search_terms = [x.strip('"\'') for x in message[message.find(' ')+1:].split(' and ')]
        except Exception as e:
            return f"`{type(e)}`\n```{e}```"

        try:
            return ("Search successful. View your results: " +
                    fanc.lookup.cells_annotated_with(search_terms, return_as='url'))
        except Exception as e:
            return f"`{type(e)}`\n```{e}```"

    # For some reason the '>' character typed into slack
    # is reaching this code as '&gt;', so revert it for readability.
    message = message.replace('&gt;', '>')
    tokens = message.strip(' ').split(' ')
    if len(tokens) == 0:
        return ("NO ACTION: Your message is empty or I couldn't understand"
                " it. Make a post containing the word 'help' if needed.")
    try:
        segid = int(tokens[0][:-1])
    except ValueError:
        return (f"ERROR: Could not convert the first word"
                f" `{tokens[0][:-1]}` to int. Is it a segID?")

    caveclient.materialize.version = caveclient.materialize.most_recent_version()

    if tokens[0].endswith('?'):  # Query
        return_details = False
        if len(tokens) > 1 and tokens[1].lower() in ['all', 'everything', 'verbose', 'details']:
            return_details = True
        try:
            info = fanc.lookup.annotations(segid, return_details=return_details)
        except Exception as e:
            return f"`{type(e)}`\n```{e}```"
        if len(info) == 0:
            return "No annotations found."
        if return_details:
            info.drop(columns=['id', 'valid', 'pt_supervoxel_id',
                               'pt_root_id', 'pt_position', 'deleted',
                               'superceded_id'],
                      errors='ignore',
                      inplace=True)
            info.rename(columns={'tag': 'annotation',
                                 'tag2': 'annotation_class'}, inplace=True)
            info['created'] = info.created.apply(lambda x: x.date())
            return ('```' + info.to_string(index=False) + '```')
        else:
            return ('```' + '\n'.join(info) + '```')

    elif tokens[0].endswith('!'):  # Upload
        # Permissions
        table_permissions = permissions.get(table_name, None)
        if table_permissions is None:
            return f"ERROR: `{table_name}` not listed in permissions file."
        cave_user_id = table_permissions.get(user, None)
        if cave_user_id is None:
            return ("You have not yet been given permissions to post to"
                    f" `{table_name}`. Please send Jasper a DM on slack"
                    " to request permissions.")

        # Sanity checks
        if not caveclient.chunkedgraph.is_latest_roots(segid):
            return (f"ERROR: {segid} is not a current segment ID."
                    " Was the segment edited recently? Or did you"
                    " copy-paste the wrong thing?")

        # Parse and validate annotations
        if len(tokens) < 4 or '>' not in tokens:
            return ("ERROR: To upload neuron information, your message"
                    " must have the format `{segid}! {annotation} >"
                    " {annotation_class}`. Run 'help' for examples.")
        annotation_tokens = ' '.join(tokens[1:]).split('>')
        if len(annotation_tokens) != 2:
            return (f"ERROR: Could not parse `{' '.join(tokens[1:])}`"
                    " into an annotation and annotation_class.")
        annotation_class = annotation_tokens[0].strip()
        annotation = annotation_tokens[1].strip()

        if fake:
            try:
                fanc.annotations.is_allowed_to_post(segid, annotation_class, annotation)
                point = list(fanc.lookup.anchor_point(segid))
            except Exception as e:
                return f"`{type(e)}`\n```{e}```"
            return (f"FAKE: Would upload segment {segid}, point {point}"
                    f", annotations `{annotation_class} > {annotation}`.")

        try:
            response = fanc.upload.annotate_neuron(segid, annotation_class,
                                                   annotation, cave_user_id)
            record_upload(segid, annotation, annotation_class,
                          cave_user_id, table_name)
            uploaded_data = caveclient.annotation.get_annotation(table_name,
                                                                 response)[0]
            return (f"Upload to `{table_name}` succeeded:\n"
                    f"- Segment {segid}\n"
                    f"- Point coordinate `{uploaded_data['pt_position']}`\n"
                    f"- Annotation: `{annotation}`\n"
                    f"- Annotation class: `{annotation_class}`\n"
                    f"- Annotation ID: {response[0]}")
        except Exception as e:
            return f"ERROR: Annotation failed due to\n`{type(e)}`\n```{e}```"

    else:
        return ("ERROR: The first word in your message isn't a segment"
                " ID terminated by a ! or a ?. Make a post containing"
                " the word 'help' if you need instructions.")
    

def record_upload(segid, tag, tag2, user_id, table_name) -> None:
    uploads_fn = f'neuron_information_bot_uploads_to_{table_name}.txt'
    with open(uploads_fn, 'a') as f:
        f.write(f'{segid},{tag},{tag2},{user_id}\n')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'fake':
        fake = True
        print('Running in FAKE mode')
    else:
        fake = False
    handler.start()
