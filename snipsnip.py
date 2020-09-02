#!/usr/bin/env python3
import requests as r
from bs4 import BeautifulSoup
from pprint import pprint
import os
import sys
import pickle
import argparse
import time
import datetime
from urllib.parse import urlparse, parse_qs
import subprocess

SIGN_IN = "https://signin.intra.42.fr/users/sign_in"
PROFILE = "https://profile.intra.42.fr/"
PROJECT = "https://projects.intra.42.fr"

def login(args):
    session = r.Session()
    session.headers.update({'User-Agent': "Mozilla/5.0 (X11; Linux x86_64; rv:79.0) Gecko/20100101 Firefox/79.0"})

    req1 = session.get(SIGN_IN)
    if req1.status_code == 200:
        page_signin = req1.content.decode('utf-8')
    else:
        if args.debug:
            print('[debug] failed to get sign-in page, requests.get returned: ', req1.status_code)
        return None
        
    soup1 = BeautifulSoup(page_signin, features="html.parser")

    post_data = {} 
    for form_input in soup1.find_all('input'):
        key = form_input.get('name')
        value = form_input.get('value')
        post_data[key] = value

    post_data["user[login]"] = args.user
    post_data["user[password]"] = args.password

    req2 = session.post(SIGN_IN, data=post_data, allow_redirects=False)
    if req2.status_code == 200 or req2.status_code == 302:
        if args.save == True:
            store_session(session)
        return session
    else:
        if args.debug:
            print('[debug] failed to post login data, requests.post returned: ', req2.status_code)
        return None


def store_session(session): #save session into a file
    try:
        with open("intra_session.pickle", 'wb') as fp:
            pickle.dump(session, fp)
            fp.close()
            return True  #great success
    except:
        return False


def select_project(session):
    req1 = session.get(PROFILE)
    if req1.status_code == 200:
        page_projects = req1.content.decode('utf-8')
    else:
        if args.debug:
            print('[debug] failed to get profile page, requests.get returned: ', req1.status_code)
        return None, None
        
    soup1 = BeautifulSoup(page_projects, features="html.parser")

    projects = []
    for i, project in enumerate(soup1.find_all("a", class_="project-item")):
        name = project.text.strip()
        print(str(i)+ ": " + name)
        projects.append((name, project['href']))
    
    if not projects:
        return None, None
    idx = int(input("Select your project: "))
    print()
    return projects[idx]

def snipe_project(session, name, url):
    req1 = session.get(url)
    if req1.status_code == 200:
        page_project = req1.content.decode('utf-8')
    else:
        if args.debug:
            print('[debug] failed to get project page, requests.get returned: ', req1.status_code)
        return
        
    soup1 = BeautifulSoup(page_project, features="html.parser")
    subscribe_link = soup1.find("a", text="Subscribe to defense\n")
    slots_url = PROJECT + subscribe_link["href"]

    req2 = session.get(slots_url)
    if req2.status_code == 200:
        page_slots = req2.content.decode('utf-8')
    else:
        if args.debug:
            print('[debug] failed to get project page, requests.get returned: ', req1.status_code)
        return

    soup2 = BeautifulSoup(page_slots, features="html.parser")
    calendar = soup2.find(id="calendar")
    
    url_json_base = PROJECT + calendar["data-index-url"]

    team_id = parse_qs(urlparse(url_json_base).query)['team_id'][0]
    print(f"Sniping slots for team {team_id}...")

    while True:
        today = datetime.date.today()
        end_date = today + datetime.timedelta(days=5)
        url_json = url_json_base + "&start=" + str(today) + "&end=" + str(end_date)

        req3 = session.get(url_json)
        if req3.status_code == 200:
            json = req3.json()
        print("Slots available at: " + str(datetime.datetime.now()))
        for slot in json:
            notify_string = f"FOUND SLOT FOR {name} !!\n" + slot["start"] + " - " + slot["end"] + "!"
            subprocess.run(["notify-send", "-u", "critical", notify_string])
        print()
        time.sleep(60)

if __name__=="__main__":
    parser = argparse.ArgumentParser(description="intra slot sniper")
    parser.add_argument("-d", "--debug", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)

    auth = subparsers.add_parser("login", help="authenticate on intra.42.fr")
    auth.add_argument("-s", "--save", type=argparse.FileType('wb'))
    auth.add_argument("user")
    auth.add_argument("password")
    
    
    load = subparsers.add_parser("load", help="load a saved session")
    load.add_argument("load", type=argparse.FileType('rb'))

    args = parser.parse_args()

    if args.command == "load":
        print("Loading session...")
        session = pickle.load(args.load)
    else:
        print("Logging on the intra...")
        session = login(args)
        if args.save:
            pickle.dump(session, args.save)
    if session is None:
        print("Error while fetching session. Exiting...")
        sys.exit(1)
    print("Session loaded.")
    print()
    
    name, url = select_project(session)
    if not name:
        print("Cannot find any projects. Exiting...")
        sys.exit(1)
    
    snipe_project(session, name, url)