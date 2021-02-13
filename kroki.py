from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from os.path import exists
from os import mkdir
from time import time_ns
from datetime import datetime, timedelta
from sys import argv
import plotly.graph_objects as go
import subprocess
import json
import requests
import pickle


# authorization
scopes = ['https://www.googleapis.com/auth/fitness.activity.read']
creds = None

if exists('token/token.pickle'):
    with open('token/token.pickle', 'rb') as token:
        creds = pickle.load(token)
        print("loaded authorization token from file")
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        print("refreshed token")
    else:
        flow = InstalledAppFlow.from_client_secrets_file('token/credentials.json', scopes)
        creds = flow.run_local_server()
        print("authorized!")
    with open('token/token.pickle', 'wb') as token:
        pickle.dump(creds, token)
        print("saved authorization token to file")

headers = {"Authorization": f"Bearer {creds.token}", "Content-Type": "application/json;encoding=utf-8"}


# get dataSource
r = requests.get("https://fitness.googleapis.com/fitness/v1/users/me/dataSources", headers=headers)
data_sources = r.json()

dataStreamId = None
for i in data_sources["dataSource"]:
    if i['dataStreamId'] == "raw:com.google.step_count.delta:com.xiaomi.hm.health:":
        # get xiaomi mi band dataStream
        dataStreamId = i['dataStreamId']
        break
if dataStreamId is None:
    print("could not find the mi band dataStream")
    quit()


# aggregate test
end = datetime.today()
start = datetime(end.year, end.month, end.day, end.hour, end.minute) - timedelta(days=7)
start = int((start - datetime(1970, 1, 1)).total_seconds() * (10 ** 9))
end = int(time_ns())

# print(int(start/(10**6)))
#
# body = {"aggregateBy": [{"dataTypeName": "com.google.step_count.delta", "dataSourceId": "derived:com.google.step_count.delta:com.google.android.gms:estimated_steps"}],
#         "bucketByTime": {"durationMillis": 86400000},
#         "startTimeMillis": int(start/(10**6)), "endTimeMillis": int(end/(10**6))}
# body = json.dumps(body)
#
# r = requests.post("https://www.googleapis.com/fitness/v1/users/me/dataset:aggregate", data=body, headers=headers)
# r = r.json()
#
# print(r)
# for i in r["bucket"]:
#     print(i)
# quit()


# get dataset

datasetId = f"{str(start)}-{str(end)}"
r = requests.get(f"https://fitness.googleapis.com/fitness/v1/users/me/dataSources/{dataStreamId}/datasets/{datasetId}",
                 headers=headers)
steps_response = r.json()
if r.status_code != 200:
    print("error when trying to fetch data!")
    print(r.status_code)
    print(r.content)
    quit()
print("fetched data from google fit")


# load data.json
if exists("data.json"):
    with open("data.json", "r") as f:
        steps_data = json.load(f)
    print("loaded data from file")
else:
    steps_data = {}


# count steps
steps = {}
for i in steps_response["point"]:
    start = datetime.fromtimestamp(int(i["startTimeNanos"]) / (10 ** 9))
    end = datetime.fromtimestamp(int(i["endTimeNanos"]) / (10 ** 9))

    value = i["value"][0]["intVal"]

    print(f"{start} - {end} -> {value}")

    if start not in steps:
        steps[start] = value
    else:
        steps[start] += value


# save new data
for i in steps:
    if not str(i.year) in steps_data:
        steps_data[str(i.year)] = {}
    if not str(i.month) in steps_data[str(i.year)]:
        steps_data[str(i.year)][str(i.month)] = {}
    if not str(i.day) in steps_data[str(i.year)][str(i.month)]:
        steps_data[str(i.year)][str(i.month)][str(i.day)] = 0

    if steps[i] > steps_data[str(i.year)][str(i.month)][str(i.day)]:
        steps_data[str(i.year)][str(i.month)][str(i.day)] = steps[i]
        # update data only if it's higher

if (datetime.now() + timedelta(days=1)).month == datetime.now().month:
    steps_data[str(datetime.now().year)][str(datetime.now().month)][str(datetime.now().day + 1)] = 0
    # setting next day to 0 for better scale

this_month = steps_data[str(datetime.now().year)][str(datetime.now().month)]
for i in this_month:
    print(f"{i}: {this_month[i]}")

with open("data.json", "w") as f:
    json.dump(steps_data, f, indent=4)
print("saved new data to file")


# create monthly line chart
fig = go.Figure()
fig.add_trace(go.Scatter(x=list(this_month.keys()), y=list(this_month.values())))
fig.update_layout(title="daily steps", xaxis_title="day", yaxis_title="steps", template="plotly_dark")

if not exists("exports"):
    mkdir("exports")
if not exists(f"exports/{str(datetime.now().year)}"):
    mkdir(f"exports/{str(datetime.now().year)}")

fig.write_html(f"exports/{str(datetime.now().year)}/{str(datetime.now().month)}.html")
print(f"exported monthly line chart to exports/{str(datetime.now().year)}/{str(datetime.now().month)}.html")


# export this month data to json
if exists(f"exports/{str(datetime.now().year)}/{str(datetime.now().month)}.json"):
    with open(f"exports/{str(datetime.now().year)}/{str(datetime.now().month)}.json", "r") as f:
        this_month_old = dict(json.load(f))
else:
    this_month_old = {}
if this_month == this_month_old:
    diff = False
else:
    diff = True

with open(f"exports/{str(datetime.now().year)}/{str(datetime.now().month)}.json", "w") as f:
    json.dump(this_month, f, indent=4)
    print(f"exported this month data to exports/{str(datetime.now().year)}/{str(datetime.now().month)}.json")


# push the pages repository
if "--push" in argv or "-p" in argv or "--forcepush" in argv or "-fp" in argv:
    if diff or "--forcepush" in argv or "-fp" in argv:
        p = subprocess.Popen(["git", "add", "."], cwd="exports")
        p.wait()
        p.kill()

        p = subprocess.Popen(["git", "commit", "-am", f"{datetime.now().date()} auto update"], cwd="exports")
        p.wait()
        p.kill()

        p = subprocess.Popen(["git", "push"], cwd="exports")
        p.wait()
        p.kill()
        print("\npushed pages repo")
    else:
        print("no differences, skipping pages push")
