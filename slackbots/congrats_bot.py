#!/usr/bin/env python3
"""
Install the slack python package with `pip install slack_sdk`
Some useful Slack API info pages:
  - https://api.slack.com/messaging/retrieving
  - https://api.slack.com/messaging/sending

View and configure your slack apps: https://api.slack.com/apps
Through Features > App Home > Show Tabs, select "Allow users to send
  Slash commands and messages from the messages tab" to enable DMs.
Through Features > OAuth & Permissions > Scopes > Bot Token Scopes,
give your bot these permissions:
  chat:write
  im:read
  im:history
From Features > OAuth & Permissions > OAuth Tokens for Your Workspace,
  copy your app's auth token to your shell environment by adding a line
  like this to your shell startup file (e.g. ~/.bashrc, ~/.zshrc):
    export SLACK_BOT_TOKEN=xoxb-123456789012-...
"""

import os
import sys
import json
from datetime import datetime, timezone, timedelta

import slack_sdk

import banc

caveclient = banc.get_caveclient()
tables = ['backbone_proofread', 'cell_info']

with open('slack_user_permissions.json', 'r') as f:
    users = json.load(f)

if len(sys.argv) > 1 and sys.argv[1] in os.environ:
    token = os.environ[sys.argv[1]]
else:
    token = os.environ['SLACK_TOKEN_BANC_BOT']
slackclient = slack_sdk.WebClient(token=token)

channel_to_post_to = 'banc'
channel_ids = {
    'banc': 'C06HWL1UQL9',
}
channel_id = channel_ids[channel_to_post_to]
thread_ts = None

now = datetime.now(timezone.utc)
then = now - timedelta(days=7)


def provide_update(table_names=tables):
    """
    For each of the given tables, provide an update about how many annotations
    are there in total, how many were added in the last week, and who the top 3
    contributors were in the past week
    """
    msg = ("Hello fellow BANCers, happy Friday! :money_with_wings: Here's this"
           " week's update on the amazing progress you all made in building the"
           " BANC connectome.\n\n")
    for table_name in table_names:
        table_now = caveclient.materialize.live_live_query(table_name, timestamp=now)
        table_then = caveclient.materialize.live_live_query(table_name, timestamp=then)
        n_this_week = len(table_now) - len(table_then)
        counts_now = table_now.user_id.value_counts()
        counts_then = table_then.user_id.value_counts()
        for user in counts_now.index:
            if user not in counts_then.index:
                counts_then[user] = 0
        for user in counts_then.index:
            if user not in counts_now.index:
                counts_now[user] = 0
        counts_diff = (counts_now - counts_then).sort_values(ascending=False)
        top_users_caveids = counts_diff[0:3].index
        top_users_slackids = [[slackid
                               for slackid, caveid in users[table_name].items()
                               if caveid == user_caveid][0]
                              for user_caveid in top_users_caveids]
        top_counts = counts_diff[0:3].values.astype(int)
        msg += f"*`{table_name}` has {len(table_now)} total entries on {table_now.pt_root_id.nunique()} unique cells.*"
        if top_counts[0] == 0:
            msg += f"\n\t`{table_name}` has no new entries in the last 7 days.\n\n"
        else:
            msg += (f"\n:chart_with_upwards_trend:   {n_this_week} entries were added in the last 7 days."
                    "\n:trophy:   Congrats and big thanks to this week's top contributors!"
                    f"\n\t\t:first_place_medal:   <@{top_users_slackids[0]}> ({top_counts[0]} annotations)")
            if top_counts[1] > 0:
                msg += f"\n\t\t:second_place_medal:   <@{top_users_slackids[1]}> ({top_counts[1]} annotations)"
            if top_counts[2] > 0:
                msg += f"\n\t\t:third_place_medal:   <@{top_users_slackids[2]}> ({top_counts[2]} annotations)"
            msg += "\n\n"

    if fake:
        print(msg)
        return
    slackclient.chat_postMessage(
        channel=channel_id,
        thread_ts=thread_ts,
        text=msg
    )
    print('Posted update to slack')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'post':
        fake = False
    else:
        fake = True
        print('Running in FAKE mode')

    provide_update()
