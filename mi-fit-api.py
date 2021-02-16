import requests
from os import environ
import datetime
import base64
import json

# get access token
email = environ.get("MI_EMAIL")
password = environ.get("MI_PASS")
body = {"state": "REDIRECTION",
        "client_id": "HuaMi",
        "redirect_uri": "https://s3-us-west-2.amazonaws.com/hm-registration/successsignin.html",
        "token": "access",
        "password": password}

r = f"https://api-user.huami.com/registrations/{email}/tokens"
r = requests.post(r, data=body, allow_redirects=False)

r = r.headers.get("Location")
r = r.split("?")[1].split("&")
r_dict = {}
for i in r:
    r_dict[i.split("=")[0]] = i.split("=")[1]

if "error" in r_dict:
    print(r_dict)
    print("Error, wrong login credentials! Quitting")
    quit(1)

access_token = r_dict["access"]
country_code = r_dict["country_code"]
print("got access token")

# get API credentials
body = {'app_name': 'com.xiaomi.hm.health',
        'dn': 'account.huami.com,api-user.huami.com,api-watch.huami.com,api-analytics.huami.com,'
              'app-analytics.huami.com,api-mifit.huami.com',
        'device_id': '02:00:00:00:00:00',
        'device_model': 'android_phone',
        'app_version': '4.9.0',
        'allow_registration': 'false',
        'third_name': 'huami',
        'grant_type': 'access_token',
        'country_code': country_code,
        'code': access_token}

r = requests.post("https://account.huami.com/v2/client/login", data=body)

if r.status_code != 200:
    print("Unable to get api credentials!")
    print(r.content)
    print(r.headers)
    print(r)
    print("Quitting!")
    quit(1)

r = r.json()
login_token = r["token_info"]["login_token"]
app_token = r["token_info"]["app_token"]
user_id = r["token_info"]["user_id"]
print("got api credentials")

# get mi band data
from_date = (datetime.datetime.now() - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
to_date = datetime.datetime.now().strftime("%Y-%m-%d")
headers = {"apptoken": app_token}
params = {'query_type': 'summary',
          'device_type': 'android_phone',
          'userid': user_id,
          'from_date': from_date,
          'to_date': to_date}

r = requests.get("https://api-mifit.huami.com/v1/data/band_data.json", headers=headers, params=params)

if r.status_code != 200:
    print("Failed to load mi-band data!")
    print(r.status_code)
    print(r.content)
    print(r.headers)
    print("Quitting!")
    quit(1)

r = r.json()

# get steps data
steps_data = {}
for i in r["data"]:
    bs64_data = i["summary"]
    data = json.loads(base64.b64decode(bs64_data))
    steps = data["stp"]
    steps_total = steps["ttl"]
    steps_distance = steps["dis"]
    date = (datetime.datetime.strptime(i["date_time"], "%Y-%m-%d")).date()

    steps_data[date] = {"num": steps_total, "dis": steps_distance}
    print(f"\n{date}")
    print(f"{steps_total} steps")
    print(f"{steps_distance} m")

print("\ngot steps data")
print(steps_data)
