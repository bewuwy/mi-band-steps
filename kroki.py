from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from os.path import exists
from time import time_ns
from datetime import datetime, timedelta
import plotly.graph_objects as go
import json
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

dataStreamId = None
for i in data_sources["dataSource"]:
    if i['dataStreamId'] == "raw:com.google.step_count.delta:com.xiaomi.hm.health:":
        dataStreamId = i['dataStreamId']
        break
if dataStreamId is None:
    print("could not find the dataStream")
    quit()


end = datetime.today()
start = datetime(end.year, end.month, end.day, end.hour, end.minute) - timedelta(days=7)
start = int((start-datetime(1970, 1, 1)).total_seconds() * (10**9))
end = int(time_ns())

datasetId = f"{str(start)}-{str(end)}"
r = requests.get(f"https://fitness.googleapis.com/fitness/v1/users/me/dataSources/{dataStreamId}/datasets/{datasetId}",
                 headers=headers)
steps = r.json()

if exists("data.json"):
    with open("data.json", "r") as f:
        steps_data = json.load(f)
else:
    steps_data = {}

for i in steps["point"]:
    start = (datetime.fromtimestamp(int(i["startTimeNanos"])/(10**9)))
    steps_data[str(start.date())] = 0
for i in steps["point"]:
    start = (datetime.fromtimestamp(int(i["startTimeNanos"])/(10**9)))
    # end = (datetime.fromtimestamp(int(i["endTimeNanos"])/(10**9)))
    value = i["value"][0]["intVal"]

    if str(start.date()) in steps_data:
        steps_data[str(start.date())] += value
    else:
        steps_data[str(start.date())] = value
    # print(f"{start} - {end} -> {value}")

print(steps_data, end="\n"*2)
for i in steps_data:
    print(f"{i} -> {steps_data[i]}")

with open("data.json", "w") as f:
    json.dump(steps_data, f, indent=4)

fig = go.Figure()
fig.add_trace(go.Scatter(x=list(steps_data.keys()), y=list(steps_data.values()), name="steps"))
fig.update_layout(title="daily steps", xaxis_title="date", yaxis_title="steps")
fig.show()
