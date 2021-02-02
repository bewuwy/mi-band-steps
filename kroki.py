from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from os.path import exists
from time import time_ns
from datetime import datetime, timedelta
import requests
import pickle


scopes = ['https://www.googleapis.com/auth/fitness.activity.read']
creds = None

if exists('token/token.pickle'):
    with open('token/token.pickle', 'rb') as token:
        creds = pickle.load(token)
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file('token/credentials.json', scopes)
        creds = flow.run_local_server()
    with open('token/token.pickle', 'wb') as token:
        pickle.dump(creds, token)


headers = {"Authorization": f"Bearer {creds.token}", "Content-Type": "application/json;encoding=utf-8"}
r = requests.get("https://fitness.googleapis.com/fitness/v1/users/me/dataSources", headers=headers)

data_sources = r.json()

dataStream = None
for i in data_sources["dataSource"]:
    if i['dataStreamId'] == "raw:com.google.step_count.delta:com.xiaomi.hm.health:":
        dataStream = i
        break
if dataStream is None:
    print("could not find the dataStream")
    quit()

dataStreamId = dataStream["dataStreamId"]

now = datetime.utcnow()
week = datetime(now.year, now.month, now.day, now.hour, now.minute) - timedelta(days=7)
week = int((week-datetime(1970, 1, 1)).total_seconds() * (10**9))
now = int(time_ns())

# dataset
datasetId = f"{str(week)}-{str(now)}"

r = requests.get(f"https://fitness.googleapis.com/fitness/v1/users/me/dataSources/{dataStreamId}/datasets/{datasetId}",
                 headers=headers)
steps = r.json()

print(steps)
for i in steps["point"]:
    print(i)
