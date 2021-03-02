from os.path import exists
from os import mkdir
from sys import argv
import plotly.graph_objects as go
import subprocess
from datetime import datetime
import json
import miFit


dailyGoal = 8000

num_list = []
dis_list = []
year = str(datetime.now().year)
month = str(datetime.now().month)

all_data = miFit.main()
month_data = all_data[year][month]

for i in month_data.values():
    num_list.append(i["num"])
    dis_list.append(i["dis"])

days_list = list(month_data.keys())

# create monthly line chart
fig = go.Figure()
fig.add_trace(go.Scatter(x=days_list, y=num_list, name="steps", mode='lines+markers'))
if dis_list:
    fig.add_trace(go.Scatter(x=days_list, y=dis_list, name="meters", mode='lines+markers'))

dailyGoalList = []
for i in days_list:
    dailyGoalList.append(dailyGoal)
fig.add_trace(go.Scatter(x=days_list, y=dailyGoalList, name="daily goal", mode="lines", line={"dash": "dash"}))

fig.update_layout(title="daily steps", xaxis_title="day", template="plotly_dark")

if not exists("exports"):
    mkdir("exports")
    mkdir(f"exports/{year}")
elif not exists(f"exports/{year}"):
    mkdir(f"exports/{year}")

fig.write_html(f"exports/{year}/{month}.html")
print(f"exported monthly line chart to exports/{year}/{month}.html")

# calculate month average
average_num = [0, 0]
average_dis = [0, 0]
for i in month_data.values():
    if i["num"] is not None:
        average_num[0] += i["num"]
        average_num[1] += 1
    if i["dis"] is not None:
        average_dis[0] += i["dis"]
        average_dis[1] += 1

if average_num[1] != 0:
    average_num = int(average_num[0]/average_num[1])
if average_dis[1] != 0:
    average_dis = int(average_dis[0]/average_dis[1])

month_data["average"] = {"num": average_num, "dis": average_dis}

# export this month data to json
if exists(f"exports/{year}/{month}.json"):
    with open(f"exports/{year}/{month}.json", "r") as f:
        month_data_old = dict(json.load(f))
else:
    month_data_old = {}

with open(f"exports/{year}/{month}.json", "w") as f:
    json.dump(month_data, f, indent=4)
    print(f"exported this month data to exports/{year}/{month}.json")

# push the pages repository
if "--push" in argv or "-p" in argv or "--forcepush" in argv or "-fp" in argv:
    if month_data != month_data_old or "--forcepush" in argv or "-fp" in argv:
        print()
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
        print("\nno differences, skipping pages push")
