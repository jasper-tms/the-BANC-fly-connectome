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
import re
from datetime import datetime
from typing import Union

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

import banc
banc.use_auth_token_key('banc_service_account')

# Setup
verbosity = 2
convert_given_point_to_anchor_point = False

caveclient = banc.get_caveclient()
tables = ['cell_info', 'backbone_proofread']

with open('slack_user_permissions.json', 'r') as f:
    permissions = json.load(f)

app = App(token=os.environ['SLACK_TOKEN_BANC_BOT'],
          signing_secret=os.environ['SLACK_SIGNING_SECRET_BANC_BOT'])
handler = SocketModeHandler(app, os.environ['SLACK_TOKEN_BANC_BOT_WEBSOCKETS'])


def show_help():
    return (
"""
:bank: Hello and welcome to the BANC-FlyWire community! :money_with_wings:

I'll be happy to assist you today.
- You can find the instructions for how to talk to me in <https://github.com/jasper-tms/the-BANC-fly-connectome/wiki/banc‐bot-user-manual|my user manual>
- You might also want to check out <https://github.com/jasper-tms/the-BANC-fly-connectome/wiki/Annotations-(cell-types,-etc.)|the list of available annotations>

I'm at your service, but I'm also a work in progress! Feel free to send <@U348GFY5N> any questions, requests, or bug reports if I seem to be misbehaving.
""")


@app.event("message")
def direct_message(message, say, client):
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
        try:
            response = process_message(message['text'],
                                       message['user'],
                                       client=client,
                                       fake=fake)
        except Exception as e:
            response = f"`{type(e)}`\n```{e}```"
    if verbosity >= 1:
        print('Posting response:', response)
    if len(response) > 1500:
        say(response, thread_ts=message['ts'])
    else:
        say(response)


def process_message(message: str,
                    user: str,
                    client=None,
                    fake=False) -> str:
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
    while '  ' in message:
        message = message.replace('  ', ' ')

    if message.startswith(('get', 'find')):
        search_terms = message[message.find(' ')+1:].strip('"\'')

        if message.startswith(('getids', 'findids')):
            results = banc.lookup.cells_annotated_with(search_terms,
                                                       return_as='list')
            if len(results) > 300:
                return (f"{len(results)} cells matched that search! Try a more"
                        " specific search (like `findids X and Y and Z`) to see"
                        " a list of IDs.")
            return f"Search successful:```{', '.join(map(str, results))}```"
        if message.startswith(('getnum', 'findnum')):
            results = banc.lookup.cells_annotated_with(search_terms,
                                                       return_as='list')
            return f"Your search matched {len(results)} cells."

        return ("Search successful. View your results: " +
                banc.lookup.cells_annotated_with(search_terms, return_as='url'))

    try:
        caveclient.materialize.version = caveclient.materialize.most_recent_version()
    except Exception as e:
        return ("CAVE appears to be offline. Please wait a few minutes"
                f" and try again: `{type(e)}`\n```{e}```")

    # Because HTML or something, the '>' character typed into slack
    # is reaching this code as '&gt;', so revert it for readability.
    message = message.replace('&gt;', '>')

    return_details = False
    if '??' in message:
        return_details = True
        message = message.replace('??', '?')
    if '?' in message:  # Query
        neuron = message[:message.find('?')]
        try:
            segid = int(neuron)
        except ValueError:
            try:
                point = [int(coordinate.strip(','))
                         for coordinate in re.split(r'[ ,]+', neuron)]
            except ValueError:
                return f"ERROR: Could not parse `{neuron}` as a segment ID or a point."
            segid = banc.lookup.segid_from_pt(point)
        if not caveclient.chunkedgraph.is_latest_roots(segid):
            return (f"ERROR: {segid} is not a current segment ID."
                    " It may have been edited recently, or perhaps"
                    " you copy-pasted the wrong thing.")
        modifiers = message[message.find('?')+1:].strip(' ')
        if any([x in modifiers.lower() for x in ['all', 'details', 'verbose', 'everything']]):
            return_details = True

        info = banc.lookup.annotations(segid, return_details=return_details)
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

    if '!' in message:  # Upload
        neuron = message[:message.find('!')]
        try:
            segid = int(neuron)
            neuron = segid
            try:
                point = banc.lookup.anchor_point(segid)
            except Exception as e:
                return f"`{type(e)}`\n```{e}```"
        except ValueError:
            point = [int(coordinate.strip(','))
                     for coordinate in re.split(r'[ ,]+', neuron)]
            segid = banc.lookup.segid_from_pt(point)
            if convert_given_point_to_anchor_point:
                point = fanc.lookup.anchor_point(segid)
            neuron = point

        if not caveclient.chunkedgraph.is_latest_roots(segid):
            return (f"ERROR: {segid} is not a current segment ID."
                    " It may have been edited recently, or perhaps"
                    " you copy-pasted the wrong thing.")
        annotation = message[message.find('!')+1:].strip(' ')
        invalidity_errors = []
        for table in tables:
            if annotation.replace(' ', '_').replace('-', '_') == table:
                annotation = True
            try:
                if not banc.annotations.is_valid_annotation(annotation,
                                                            table_name=table,
                                                            response_on_unrecognized_table=True,
                                                            raise_errors=True):
                    raise ValueError(f'Invalid annotation "{annotation}"'
                                     f' for table "{table}".')
            except Exception as e:
                invalidity_errors.append(e)
                continue

            # Permissions
            table_permissions = permissions.get(table, None)
            if table_permissions is None:
                return f"ERROR: `{table}` not listed in permissions file."
            cave_user_id = table_permissions.get(user, None)
            if cave_user_id is None:
                return ("You have not yet been given permissions to post to"
                        f" `{table}`. Please send Jasper a DM on slack"
                        " to request permissions.")

            if fake:
                banc.annotations.is_allowed_to_post(segid, annotation,
                                                    response_on_unrecognized_table=True,
                                                    table_name=table)
                return (f"FAKE: Would upload segment {segid}, point"
                        f" `{list(point)}`, annotation `{annotation}`"
                        f" to table `{table}`.")
            try:
                annotation_id = banc.upload.annotate_neuron(
                    neuron, annotation, cave_user_id, table_name=table,
                    convert_given_point_to_anchor_point=convert_given_point_to_anchor_point
                )
                uploaded_data = caveclient.annotation.get_annotation(table,
                                                                     annotation_id)[0]
                msg = (f"Upload to `{table}` succeeded:\n"
                       f"- Segment {segid}\n"
                       f"- Point coordinate `{uploaded_data['pt_position']}`\n"
                       f"- Annotation ID: {annotation_id}")
                if 'proofread' in uploaded_data:
                    msg += f"\n- Annotation: `{uploaded_data['proofread']}`"
                    record_upload(annotation_id, segid,
                                  uploaded_data['proofread'],
                                  cave_user_id, table)
                elif 'tag' in uploaded_data and 'tag2' in uploaded_data:
                    msg += f"\n- Annotation: `{uploaded_data['tag']}`"
                    msg += f"\n- Annotation class: `{uploaded_data['tag2']}`"
                    record_upload(annotation_id, segid,
                                  uploaded_data['tag2'] + ': ' + uploaded_data['tag'],
                                  cave_user_id, table)
                elif 'tag' in uploaded_data:
                    msg += f"\n- Annotation: `{uploaded_data['tag']}`"
                    record_upload(annotation_id, segid,
                                  uploaded_data['tag'],
                                  cave_user_id, table)
                else:
                    msg = (msg + "\n\nWARNING: Something went wrong with recording"
                           " your upload on the slackbot server. Please send Jasper"
                           " a screenshot of your message and this response.")
                return msg
            except Exception as e:
                return f"ERROR: Annotation failed due to\n`{type(e)}`\n```{e}```"

        msg = (f"ERROR: Annotation `{annotation}` is not valid for any of the"
               " CAVE tables I know how to post to:")
        for table, e in zip(tables, invalidity_errors):
            msg += f"\n\nTable `{table}` gave `{type(e)}`:\n```{e}```"
        return msg
    if message.split(' ')[0].endswith('-'):  # Deletion
        print('Attempting deletion')
        neuron = message[:message.find('-')]
        try:
            segid = int(neuron)
        except ValueError:
            try:
                point = [int(coordinate.strip(','))
                         for coordinate in re.split(r'[ ,]+', neuron)]
            except ValueError:
                return f"ERROR: Could not parse `{neuron}` as a segment ID or a point."
            segid = banc.lookup.segid_from_pt(point)
        if not caveclient.chunkedgraph.is_latest_roots(segid):
            return (f"ERROR: {segid} is not a current segment ID."
                    " It may have been edited recently, or perhaps"
                    " you copy-pasted the wrong thing.")

        annotation = message[message.find('-')+1:].strip(' ')

        user_id = None
        for table in permissions:
            if user in permissions[table]:
                user_id = permissions[table][user]
                break
        if user_id is None:
            return ("You have not yet been given permissions to delete"
                    " annotations. Please send Jasper a DM on slack"
                    " to request permissions.")
        try:
            response = banc.upload.delete_annotation(segid, annotation, user_id)
            return (f'Successfully deleted annotation with ID {response[1]}'
                    f' from table `{response[0]}`.')
        except Exception as e:
            return f"ERROR: Deletion failed due to\n`{type(e)}`\n```{e}```"

    return ("ERROR: Your message does not contain a `?`, `!`, or `-`"
            " character, so I don't know what you want me to do."
            " Make a post containing the word 'help' for instructions.")


def record_upload(annotation_id, segid, annotation, user_id, table_name) -> None:
    uploads_fn = f'annotation_bot_uploads_to_{table_name}.csv'
    with open(uploads_fn, 'a') as f:
        f.write(f'{annotation_id},{segid},{annotation},{user_id}\n')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'fake':
        fake = True
        print('Running in FAKE mode')
    else:
        fake = False
    handler.start()
