#!/usr/bin/env python3
"""
Anyone with access to the BANC Users google sheet and a Google Sheets API token
can run this script to create a JSON file with the permissions.

The google sheet is expected to have columns named "CAVE ID", "Slack ID", and
then the last few column names should be table names, with a 'y' in the cell
if the user has access to that table. "cell_info" must be the first of the table
name columns & all columns after "cell_info" will be interpreted as table names.

You need to have a Google Sheets API token file stored at ~/.gsheetssecret
which can be generated/downloaded from
https://console.cloud.google.com/apis/api/sheets.googleapis.com/credentials
(This is not trivial to set up so probably Jasper will be the main
person running this script.)

This needs to be run from a computer with browser access, e.g. not a server
over ssh. It will open a browser window to authenticate with Google.
"""

import os
import pickle
import json

import pandas as pd
import gspread
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

banc_users_spreadsheet_id = '1UFmeWr2uF9jTLVMw3bD6nM3ejM-b-HDZz6sQBPTEoZ8'
secret_file = os.path.expanduser('~/.gsheetssecret')
session_file = os.path.expanduser('~/.gsheetssession.pickle')
permissions_file = 'slack_user_permissions.json'
with open(permissions_file, 'r') as f:
    permissions = json.load(f)

SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']


def auth_gspread():
    creds = None
    # The session file stores the user's access and refresh tokens, and
    # is created automatically when the authorization flow completes
    # for the first time.
    if os.path.exists(session_file):
        with open(session_file, 'rb') as token:
            creds = pickle.load(token)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                secret_file, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
        with open(session_file, 'wb') as token:
            pickle.dump(creds, token)

    client = gspread.authorize(creds)
    return client


client = auth_gspread()

# Pull the contents of the google sheet
spreadsheet = client.open_by_key(banc_users_spreadsheet_id)
worksheet = spreadsheet.sheet1
data = worksheet.get_all_values()
# Turn into dataframe, expecting the first row as column names
df = pd.DataFrame(data[1:], columns=data[0])
df.columns = df.columns.str.replace(' ', '_')
df = df.loc[df['Slack_ID'].str.startswith('U')]
df['CAVE_ID'] = df['CAVE_ID'].astype(int)
# Assume that the columns including and after 'cell_info' are table names
table_names = df.columns[df.columns.get_loc('cell_info'):]
columns = pd.Index(['Slack_ID', 'CAVE_ID']).append(table_names)
for row in df[columns].iterrows():
    slack_id = row[1]['Slack_ID']
    cave_id = row[1]['CAVE_ID']
    for table_name in table_names:
        if row[1][table_name] == 'y':
            if slack_id not in permissions[table_name]:
                print(f'INFO: Adding {slack_id} to permissions for {table_name}')
                permissions[table_name][slack_id] = cave_id
            elif permissions[table_name][slack_id] != cave_id:
                print(f'WARNING: {slack_id} has multiple cave_ids for {table_name}')
                print(f'  {permissions[table_name][slack_id]} vs {cave_id}')
            else:
                print(f'INFO: {slack_id} already has permissions for {table_name}')

# Check whether there are any slack_ids in permissions that
# are not in the google sheet
for table_name in table_names:
    for slack_id in permissions[table_name]:
        if slack_id not in df['Slack_ID'].values:
            print(f'WARNING: {slack_id} in permissions but not in google sheet')

with open(permissions_file, 'w') as f:
    json.dump(permissions, f, indent=4)
    f.write('\n')
