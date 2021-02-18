from os.path import exists
from os import mkdir
from sys import argv
import plotly.graph_objects as go
import subprocess
from datetime import datetime
from os import environ
import json
import googleFit
import miFit


MODE = "miFit"

this_month = {}
num_list = []
dis_list = []
if MODE == "googleFit":
    this_month = googleFit.main()

    num_list = list(this_month.values())
elif MODE == "miFit":
    this_month = miFit.main(environ.get("MI_EMAIL"), environ.get("MI_PASS"))

    for i in this_month.values():
        num_list.append(i["num"])
        dis_list.append(i["dis"])
else:
    print("wrong mode! quitting!")
    print("modes: googleFit | miFit")
    quit(1)

days_list = list(this_month.keys())

# create monthly line chart
fig = go.Figure()
fig.add_trace(go.Scatter(x=days_list, y=num_list, name="steps"))
if dis_list:
    fig.add_trace(go.Scatter(x=days_list, y=dis_list, name="meters"))
fig.update_layout(title="daily steps", xaxis_title="day", template="plotly_dark")

year = str(datetime.now().year)
month = str(datetime.now().month)

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
for i in this_month.values():
    if MODE == "miFit":
        if i["num"] is not None:
            average_num[0] += i["num"]
            average_num[1] += 1
        if i["dis"] is not None:
            average_dis[0] += i["dis"]
            average_dis[1] += 1
    elif MODE == "googleFit":
        average_num[0] += i
        average_num[1] += 1

if average_num[1] != 0:
    average_num = int(average_num[0]/average_num[1])
if average_dis[1] != 0:
    average_dis = int(average_dis[0]/average_dis[1])

if MODE == "miFit":
    this_month["average"] = {"num": average_num, "dis": average_dis}
elif MODE == "googleFit":
    this_month["average"] = average_num

# export this month data to json
if exists(f"exports/{year}/{month}.json"):
    with open(f"exports/{year}/{month}.json", "r") as f:
        this_month_old = dict(json.load(f))
else:
    this_month_old = {}

with open(f"exports/{year}/{month}.json", "w") as f:
    json.dump(this_month, f, indent=4)
    print(f"exported this month data to exports/{year}/{month}.json")

# push the pages repository
if "--push" in argv or "-p" in argv or "--forcepush" in argv or "-fp" in argv:
    if this_month != this_month_old or "--forcepush" in argv or "-fp" in argv:
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
