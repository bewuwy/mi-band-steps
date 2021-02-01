from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from os.path import exists
from time import time_ns
from datetime import datetime
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
        flow = InstalledAppFlow.from_client_secrets_file('token/credentials.json.json', scopes)
        creds = flow.run_local_server()
    with open('token/token.pickle', 'wb') as token:
        pickle.dump(creds, token)


service = build('fitness', 'v1', credentials=creds)

data_sources = service.users().dataSources().list(userId='me').execute()

dataStream = None
for i in data_sources["dataSource"]:
    if i['dataStreamName'] == "kroki.bewuwy":
        print(i)
        dataStream = i
        break

if dataStream is None:
    print("could not find the dataStream")
    quit()


dataStreamId = dataStream["dataStreamId"]

now = datetime.now()
today = datetime(now.year, now.month, now.day, 0, 0)
today = int((today-datetime(1970, 1, 1)).total_seconds() * (10**9))
datasetId = f"{str(today)}-{str(time_ns())}"

dataset = service.users().dataSources().datasets(). \
                get(userId='me', dataSourceId=dataStreamId, datasetId=datasetId).execute()
print(dataset)
