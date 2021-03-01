import requests
from os.path import exists
from shutil import copy2
from datetime import datetime, timedelta
import time
import base64
import json
import pickle


def main():
    # get access token

    access_token = None
    country_code = None
    if exists("token/mi-fit.pickle"):
        with open("token/mi-fit.pickle", "rb") as f:
            r_dict = pickle.load(f)

        expiration = int(r_dict["expiration"])
        if time.time() < expiration:
            access_token = r_dict["access"]
            country_code = r_dict["country_code"]
            print("loaded access token from file")
        else:
            print("token expired")
    if access_token is None or country_code is None:
        print("=" * 20)
        print("Mi Fit Authorization")
        print("=" * 20)

        email = input("Your Mi Fit email: ")
        password = input("Your Mi Fit password: ")

        body = {"state": "REDIRECTION",
                "client_id": "HuaMi",
                "redirect_uri": "https://s3-us-west-2.amazonaws.com/hm-registration/successsignin.html",
                "token": "access",
                "password": password}

        r = f"https://api-user.huami.com/registrations/{email}/tokens"
        r = requests.post(r, data=body, allow_redirects=False)

        r_location = r.headers.get("Location")
        if r_location is None:
            print("unknown mifit api error!")
            print("quitting!")
            print(r.headers)
            quit(1)

        r = r_location.split("?")[1].split("&")

        r_dict = {}
        for i in r:
            r_dict[i.split("=")[0]] = i.split("=")[1]

        if "error" in r_dict:
            print(r_dict)
            print("Error, wrong login credentials! Quitting")
            quit(1)

        access_token = r_dict["access"]
        country_code = r_dict["country_code"]
        print("got access token from authorization")

        with open("token/mi-fit.pickle", "wb") as f:
            pickle.dump(r_dict, f)
        print("saved access token to file")

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
    print("got api credentials")

    # login_token = r["token_info"]["login_token"]
    app_token = r["token_info"]["app_token"]
    user_id = r["token_info"]["user_id"]

    # get mi band data
    from_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    to_date = datetime.now().strftime("%Y-%m-%d")
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

    # load from json file
    jsonFile = "data/mi-fit.json"
    if exists(jsonFile):
        with open(jsonFile, "r") as f:
            try:
                steps_data = dict(json.load(f))
                print(f"loaded steps data from {jsonFile}")
            except Exception as e:
                print("couldn't load json file")
                print(e)
                errorFile = f"{jsonFile}.error{time.time()}.json"
                copy2(jsonFile, errorFile)
                print(f"copied the file to {errorFile}!")
                steps_data = {}
                print("using empty dict")
    else:
        steps_data = {}
        print("no saved data found, using empty dict")

    # add year and month if not in steps data
    year = str(datetime.now().year)
    month = str(datetime.now().month)

    if year not in steps_data:
        steps_data[year] = {month: {}}
    elif month not in steps_data[year]:
        steps_data[year][month] = {}

    # get steps data
    for i in r["data"]:
        bs64_data = i["summary"]
        data = json.loads(base64.b64decode(bs64_data))
        steps = data["stp"]
        steps_total = steps["ttl"]
        steps_distance = steps["dis"]
        date = (datetime.strptime(i["date_time"], "%Y-%m-%d")).date()
        year = str(date.year)
        month = str(date.month)
        day = str(date.day)

        steps_data[year][month][day] = {"num": steps_total, "dis": steps_distance}
        print(f"\n{date}")
        print(f"{steps_total} steps")
        print(f"{steps_distance} m")

    print("\ngot steps data")
    print(steps_data)

    # saving data to json
    with open(jsonFile, "w") as f:
        json.dump(steps_data, f, indent=4)
    print(f"saved steps data to {jsonFile}")

    return steps_data
