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
from datetime import datetime, timezone
from typing import Union

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

import banc
banc.use_auth_token_key('banc_service_account')

# Setup
verbosity = 2
convert_given_point_to_anchor_point = False
annotate_recursively = False

caveclient = banc.get_caveclient()
tables = ['cell_info', 'backbone_proofread', 'proofreading_notes']

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

    if verbosity >= 2:
        print('Processing message:', message)
    elif verbosity >= 1:
        print('Processing message with timestamp', message['ts'])

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
    # Some symbols and special characters get converted strangely on
    # their way from slack to python, so revert them.
    message = message.replace('&gt;', '>')
    message = message.replace('…', '...')

    # This is a dict specifying how to do different types of searches.
    # Each entry is a search name followed by a 3-tuple of:
    # - CAVE table name to search for neurons in
    # - A bounding box [[xmin, ymin, zmin], [xmax, ymax, zmax]] to
    #   restrict the search to, or None to search the whole table
    # - A list of annotations. Cells with any of these annotations
    #   will be _excluded_ from the search results.
    todos = {
        'neck': (
            'neck_connective_y92500',
            None,
            ['backbone proofread', 'glia']),
        'neck annotations': (
            'neck_connective_y92500',
            None,
            ['ascending', 'descending']),
        'gng': (
            'somas_v1a',
            [[123271, 36446, 83], [144504, 64547, 2647]],
            ['backbone proofread', 'merge monster', 'glia', 'damaged']),
        'left T1': (
            'somas_v1a',
            [[130000, 122704, 1595], [174550, 153012, 4026]],
            ['backbone proofread', 'merge monster', 'glia', 'damaged']),
    }

    if message.lower().startswith('todo'):
        if message.lower() == 'todo':
            message = 'todo neck'
        elif ' ' not in message:
            return ("I couldn't understand your request."
                    " Type 'help' or 'todo help' for instructions.")
        roi = message[message.find(' ')+1:]
        if roi not in todos:
            msg = ("Here are the currently defined todos:\n```todo name: (CAVE table"
                   " name, coordinates of search region, tags to exclude)\n\n"
                   + "\n".join([f"{k}: {v}" for k, v in todos.items()]) +
                   f"```\nSend me the message `todo {list(todos)[0]}` to use the"
                   " first one, for example.")
            if "help" not in message:
                msg = (f"There is currently no todo defined for `{roi}`. If you'd"
                       " like one to be created, send Jasper a DM with the"
                       f" coordinates of the region you'd like to use for `{roi}`.\n"
                       + msg)
            return msg
        table_name, bounding_box, exclude_tags = todos[roi]
        if not isinstance(bounding_box, dict):
            bounding_box = {table_name: {'pt_position': bounding_box}}

        root_ids = caveclient.materialize.live_live_query(
            table_name,
            datetime.now(timezone.utc),
            filter_spatial_dict=bounding_box,
        ).pt_root_id
        root_ids = root_ids.loc[root_ids != 0]
        annos = banc.lookup.annotations(root_ids)
        todos = [i for i, anno_list in zip(root_ids, annos) if
                 all([anno not in anno_list for anno in exclude_tags])]
        msg = (f"There are {len(todos)} `{roi}` cells that need"
               " proofreading and/or annotations")
        if len(todos) <= 5:
            return msg + ":\n```" + str(todos)[1:-1] + "```"
        import random
        return msg + ". Here are 5:\n```" + str(random.sample(todos, 5))[1:-1] + "```"

    try:
        caveclient.materialize.version = caveclient.materialize.most_recent_version()
    except Exception as e:
        return ("CAVE appears to be offline. Please wait a few minutes"
                f" and try again: `{type(e)}`\n```{e}```")

    if message.startswith('synapses'):
        if len(message) < len('synapses x'):
            return ("Send me a message like 'synapses 720575941535411994'"
                    " to see inputs and outputs from one neuron, or 'synapses"
                    " 720575941535411994 720575941593843589' to see synapses from"
                    " the first neuron to the second one.")
        segids = message[len('synapses '):].split(' ')

        # Hardcoded for now, might make this configurable later
        radius_nm = 0
        #radius_nm = 1000
        shape = 'spheres' if radius_nm > 0 else 'points'
        if len(segids) == 1:
            try:
                segid = int(segids[0])
            except:
                return f'Could not convert "{segids[0]}" to an integer.'
            now = datetime.now(timezone.utc)
            inputs = caveclient.materialize.synapse_query(post_ids=segid,
                                                          timestamp=now)
            inputs['radius_nm'] = radius_nm
            inputs = inputs[['pre_pt_position', 'radius_nm']]
            inputs = inputs.rename(columns={'pre_pt_position': 'pt_position'})
            outputs = caveclient.materialize.synapse_query(pre_ids=segid,
                                                           timestamp=now)
            outputs['radius_nm'] = radius_nm
            outputs = outputs[['post_pt_position', 'radius_nm']]
            outputs = outputs.rename(columns={'post_pt_position': 'pt_position'})
            return banc.statebuilder.render_scene(
                neurons=segid,
                annotations=[{'name': 'inputs', 'type': shape, 'data': inputs},
                             {'name': 'outputs', 'type': shape, 'data': outputs}],
                annotation_units='nm'
            )
        elif len(segids) == 2:
            try:
                pre_id = int(segids[0])
            except:
                return f'Could not convert "{segids[0]}" to an integer.'
            try:
                post_id = int(segids[1])
            except:
                return f'Could not convert "{segids[1]}" to an integer.'
            synapses = caveclient.materialize.synapse_query(pre_ids=pre_id,
                                                            post_ids=post_id)
            synapses['radius_nm'] = radius_nm
            pre_pts = synapses[['pre_pt_position', 'radius_nm']]
            pre_pts = pre_pts.rename(columns={'pre_pt_position': 'pt_position'})
            post_pts = synapses[['post_pt_position', 'radius_nm']]
            post_pts = post_pts.rename(columns={'post_pt_position': 'pt_position'})
            return banc.statebuilder.render_scene(
                neurons=[pre_id, post_id],
                annotations=[{'name': 'presynaptic points', 'type': shape, 'data': pre_pts},
                             {'name': 'postsynaptic points', 'type': shape, 'data': post_pts}],
                annotation_units='nm'
            )

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

    command_chars = ['?', '!', '-']
    try:
        command_index = min([message.find(char)
                             for char in command_chars
                             if char in message])
    except ValueError:
        if 'help' in message.lower():
            return show_help()
        return ("ERROR: Your message does not contain a `?`, `!`, or `-`"
                " character, so I don't know what you want me to do."
                " Make a post containing the word 'help' for instructions.")
    if 'help' in message[:command_index].lower():
        return show_help()
    command_char = message[command_index]

    if command_char == '?':
        if message.startswith('??', command_index):
            return_details = True
            message = message.replace('??', '?', 1)
        else:
            return_details = False

        neuron = message[:command_index]
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

    if command_char == '!':  # Upload
        neuron = message[:command_index]
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
                point = banc.lookup.anchor_point(segid)
            neuron = point

        if not caveclient.chunkedgraph.is_latest_roots(segid):
            return (f"ERROR: {segid} is not a current segment ID."
                    " It may have been edited recently, or perhaps"
                    " you copy-pasted the wrong thing.")
        annotation = message[command_index+1:].strip()
        invalidity_errors = []
        for table in tables:
            if annotation.replace(' ', '_').replace('-', '_') == table:
                annotation_to_post = True
            else:
                annotation_to_post = annotation
            try:
                if not banc.annotations.is_valid_annotation(annotation_to_post,
                                                            table_name=table,
                                                            response_on_unrecognized_table=True,
                                                            raise_errors=True):
                    raise ValueError(f'Invalid annotation "{annotation_to_post}"'
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
                banc.annotations.is_allowed_to_post(segid, annotation_to_post,
                                                    response_on_unrecognized_table=True,
                                                    table_name=table)
                return (f"FAKE: Would upload segment {segid}, point"
                        f" `{list(point)}`, annotation `{annotation}`"
                        f" to table `{table}`.")
            try:
                annotation_ids = banc.upload.annotate_neuron(
                    neuron, annotation_to_post, cave_user_id, table_name=table,
                    recursive=annotate_recursively,
                    convert_given_point_to_anchor_point=convert_given_point_to_anchor_point
                )
                uploaded_data = caveclient.annotation.get_annotation(table,
                                                                     annotation_ids)
                msg = (f"Upload to `{table}` succeeded:\n"
                       f"- Segment {segid}\n"
                       f"- Point coordinate `{uploaded_data[0]['pt_position']}`\n")
                for anno in uploaded_data:
                    if msg.count('\n') > 3:
                        msg += '\n\n'
                    msg += f"- Annotation ID: {anno['id']}"
                    if 'proofread' in anno:
                        msg += f"\n- Annotation: `{anno['proofread']}`"
                        record_upload(anno['id'], segid,
                                      anno['proofread'],
                                      cave_user_id, table)
                    elif 'tag' in anno and 'tag2' in anno:
                        msg += f"\n- Annotation: `{anno['tag']}`"
                        msg += f"\n- Annotation class: `{anno['tag2']}`"
                        record_upload(anno['id'], segid,
                                      anno['tag2'] + ': ' + anno['tag'],
                                      cave_user_id, table)
                    elif 'tag' in anno:
                        msg += f"\n- Annotation: `{anno['tag']}`"
                        record_upload(anno['id'], segid,
                                      anno['tag'],
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
    if command_char == '-':  # Delete annotation
        neuron = message[:command_index]
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

        annotation = message[command_index+1:].strip()

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
