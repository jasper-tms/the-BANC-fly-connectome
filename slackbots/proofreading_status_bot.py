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
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from caveclient import CAVEclient
import fanc


# Setup
verbosity = 2

caveclient = CAVEclient('fanc_production_mar2021')
all_tables = caveclient.materialize.get_tables()
# If there are multiple proofreading tables indicating different levels of
# completion, the line below must list them in order of least complete
# proofreading status to most complete proofreading status
proofreading_tables = ['proofread_first_pass', 'proofread_second_pass']

with open('slack_user_permissions.json', 'r') as f:
    permissions = json.load(f)

app = App(token=os.environ['SLACK_TOKEN_FANC_PROOFREADINGSTATUSBOT'],
          signing_secret=os.environ['SLACK_SIGNING_SECRET_FANC_PROOFREADINGSTATUSBOT'])
handler = SocketModeHandler(app, os.environ['SLACK_TOKEN_FANC_PROOFREADINGSTATUSBOT_WEBSOCKETS'])


def show_help():
    return (
"""
Hello! I can help you get or upload information about which neurons in FANC have been proofread. FANC has has two proofreading tables, `proofread_first_pass` and `proofread_second_pass`. Before you proceed, please read these descriptions carefully:

`proofread_first_pass`:
```
This table lists cells that have received a "first pass" of proofreading, meaning someone has spent at least ~10 minutes proofreading it, the cell has no obvious large merge errors remaining, and all the thick branches have been extended to so that the neuron's backbone is relatively complete. **Users should not hesitate to add entries to this "first pass" table for any cell that is in reasonable shape!** (We have a separate table, "proofread_second_pass", that indicates neurons that are basically complete, where we want to be more selective about only posting really well-proofread neurons.) All users can add entries to this table.
```
`proofread_second_pass`:
```
This table lists cells that have received a "second pass" of focused proofreading work to ensure that the cell's anatomy and connectivity are quite accurately reconstructed. **Users should only add cells to this table if they're confident that any remaining proofreading on this neuron would only cause trivial, almost unnoticeable changes to its morphology and connectivity.** (For cells that are in decent shape but have not received extensive attention, consider adding the cell to the table "proofread_first_pass" instead.) Only authorized users (typically only project leaders or proofreaders with >1 year of experience) can add entries to this table.
```

You can send me a message that looks like one of the `example messages below` to get or upload proofreading status information.

`648518346486614449?`
A segment ID followed by a "?" indicates that you want to know whether this segment ID has already been marked as proofread.

`648518346486614449!`
A segment ID followed by a "!" indicates that you want to mark this segment ID as "first pass" proofread.

`648518346486614449!!`
A segment ID followed by a "!!" indicates that you want to mark this segment ID as "second pass" proofread.

The "!" and "!!" commands above only work if the segment ID has exactly one soma attached to it, in which case the soma's location will be used to anchor the annotation. If the segment ID is a descending neuron or sensory neuron and so it has no soma, use the following type of command:

`648518346486614449! 48848 114737 2690` or
`648518346486614449! 48848, 114737, 2690`
To mark a *neuron with no soma* as proofread, provide an xyz point coordinate (typically copied from the top bar of neuroglancer) to use as a representative point. This should be a point inside the neuron's large-diameter backbone that is unlikely to be affected by any future edits to this neuron. (Like before, you can use either "!" to mark the neuron as "first pass" proofread, or use "!!" to mark it as "second pass" proofread.)


• These examples use the segment ID 648518346486614449 but you should substitute this with the segment ID that you're interested in.
• If you want to confirm I'm working properly, try sending me the first example message, `648518346486614449?`, and make sure you get a response.
• If you want to mark a large number of segments as proofread, you can send a message to Jasper on Slack instead of using this bot.
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
    #return "I am currently down for maintenance. Please try again later."
    tokens = message.strip(' ').split(' ')
    if len(tokens) == 0:
        return ("NO ACTION: Your message is empty or I couldn't understand"
                " it. Make a post containing the word 'help' if needed.")
    if tokens[0] not in all_tables and tokens[0][-1] not in ['?', '!']:
        return (f"ERROR: Could not understand first word `{tokens[0]}`. Make "
                "a post containing the word 'help' if you need instructions.")

    if tokens[0] in all_tables:
        table_name = tokens.pop(0)
    elif tokens[0].endswith('!!'):
        table_name = proofreading_tables[1]
        # Convert !! to ! so both upload commands now end in just one !
        tokens[0] = tokens[0][:-1]
    elif tokens[0].endswith('!'):
        table_name = proofreading_tables[0]
    else:
        table_name = proofreading_tables

    try:
        segid = int(tokens[0][:-1])
    except ValueError:
        return (f"ERROR: Could not convert the first word"
                f" `{tokens[0][:-1]}` to int. Is it a segID?")

    try:
        caveclient.materialize.version = caveclient.materialize.most_recent_version()
    except Exception as e:
        return f"The CAVE server did not respond: `{type(e)}`\n```{e}```"

    if tokens[0].endswith('?'):  # Query
        try:
            status = fanc.lookup.proofreading_status(segid, table_name)
        except Exception as e:
            return f"Query failed with `{type(e)}`\n```{e}```"

        if isinstance(status, str):
            return (f"Yes, segment {segid} is in `{status}`.")
        elif isinstance(status, tuple):
            return (f"A previous version(s) of segment {segid} was found in"
                    f" `{status[0]}`: {status[1]}.\nThis means it was"
                    " marked as proofread at some point but then edited"
                    " afterward, and the new version has not yet been marked"
                    " as proofread.")
        elif status is None:
            return f"No, segment {segid} is not marked as proofread."

        return ValueError(f'Unexpected query results:\n```{status}```')


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
        try:
            if not caveclient.chunkedgraph.is_latest_roots(segid):
                return (f"ERROR: {segid} is not a current segment ID."
                        " Was the segment edited recently? Or did you"
                        " copy-paste the wrong thing?")
            if have_recently_uploaded(segid, table_name):
                return (f"ERROR: I recently uploaded segment {segid}"
                        f" to `{table_name}`. I'm not going to upload"
                        " it again.")
            if fanc.lookup.proofreading_status(segid, table_name) == table_name:
                return (f"ERROR: {segid} is already marked as proofread in"
                        f" table `{table_name}`. Taking no action.")
        except Exception as e:
            return f"Validation steps failed with `{type(e)}`\n```{e}```"


        try:
            point = fanc.lookup.anchor_point(segid)
        except Exception as e:
            if len(tokens) == 1:
                return (f"`{type(e)}`\n```{e}```\nIf you would like to provide an"
                        " anchor point, see the instructions in the help function.")
            elif len(tokens) != 4:
                return "Anchor point not provided correctly."
            try:
                point = [float(i.strip(',')) for i in tokens[1:]]
            except ValueError:
                return (f"ERROR: Could not convert the last 3 words to"
                        " integers. Are they point coordinates?"
                        f"\n\n`{[i for i in tokens[1:]]}`")
            segid_from_point = fanc.lookup.segid_from_pt(point)
            if not segid_from_point == segid:
                return (f"ERROR: The provided point `{point}` is inside"
                        f" segment {segid_from_point} which doesn't"
                        f" match the segment ID you provided, {segid}.")
            # Drop the last 3 tokens
            tokens = tokens[:-3]
        if len(tokens) > 1 and len(point) > 0:
            return (f"ERROR: Segment {segid} has an anchor point at {point}"
                    " but you provided additional information."
                    " Additional information is unexpected when the"
                    " segment has an anchor point, so I didn't do anything.")

        stage = caveclient.annotation.stage_annotations(table_name)
        try:
            stage.add(
                proofread=True,
                pt_position=point,
                user_id=cave_user_id,
                valid_id=segid
            )
        except Exception as e:
            return f"ERROR: Staging failed with error\n`{type(e)}`\n```{e}```"

        if fake:
            return (f"FAKE: Would upload segment {segid} and point"
                    f" coordinate `{point}` to `{table_name}`.")
        try:
            response = caveclient.annotation.upload_staged_annotations(stage)
            record_upload(segid, cave_user_id, table_name)
            return (f"Upload to `{table_name}` succeeded:\n"
                    f"- Segment {segid}\n"
                    f"- Point coordinate `{point}`\n"
                    f"- Annotation ID: {response[0]}")
        except Exception as e:
            return f"ERROR: Upload failed with error\n`{type(e)}`\n```{e}```"

    else:
        return ("ERROR: The first word in your message isn't a segment"
                " ID terminated by a ! or a ?. Make a post containing"
                " the word 'help' if you need instructions.")
    

def record_upload(segid, user, table_name) -> None:
    uploads_fn = f'proofreading_status_bot_uploads_{table_name}.txt'
    with open(uploads_fn, 'a') as f:
        f.write(f'{segid},{user}\n')


def have_recently_uploaded(segid, table_name) -> bool:
    uploads_fn = f'proofreading_status_bot_uploads_{table_name}.txt'
    with open(uploads_fn, 'r') as f:
        recent_uploads = [int(line.strip().split(',')[0]) for line in f.readlines()]
    return segid in recent_uploads


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'fake':
        fake = True
        print('Running in FAKE mode')
    else:
        fake = False
    handler.start()
