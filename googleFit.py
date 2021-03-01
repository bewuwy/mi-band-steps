from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from os.path import exists
from time import time_ns
from datetime import datetime, timedelta
import json
import requests
import pickle


def main():
    # authorization
    scopes = ['https://www.googleapis.com/auth/fitness.activity.read']
    creds = None

    if exists('token/google-token.pickle'):
        with open('token/google-token.pickle', 'rb') as token:
            creds = pickle.load(token)
            print("loaded authorization token from file")
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            print("refreshed token")
        else:
            flow = InstalledAppFlow.from_client_secrets_file('token/google-credentials.json', scopes)
            creds = flow.run_local_server()
            print("authorized!")
        with open('token/google-token.pickle', 'wb') as token:
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

    # get dataset
    end = datetime.today()
    start = datetime(end.year, end.month, end.day, end.hour, end.minute) - timedelta(days=7)
    start = int((start - datetime(1970, 1, 1)).total_seconds() * (10 ** 9))
    end = int(time_ns())

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
    jsonFile = "data/google-fit.json"
    if exists(jsonFile):
        with open(jsonFile, "r") as f:
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

    with open(jsonFile, "w") as f:
        json.dump(steps_data, f, indent=4)
    print("saved new data to file")

    return steps_data
