#!/usr/bin/env python3
import argparse
import configparser
import datetime
import logging
import os
import pickle
import pprint
import re
import sys
import time
from urllib.parse import parse_qs, urlparse

import requests as r
from bs4 import BeautifulSoup

SIGN_IN = 'https://signin.intra.42.fr/users/sign_in'
PROFILE = 'https://profile.intra.42.fr/'
PROJECT = 'https://projects.intra.42.fr'
DATE_FORMAT = '%Y-%m-%dT%H:%M:%S'


def make_slots(json):
    result = []
    for slot in json:
        slot['start'] = datetime.datetime.fromisoformat(slot['start'])
        slot['end'] = datetime.datetime.fromisoformat(slot['end'])
        slot['ids'] = slot['ids'].split(',')
        duration = (slot['end'] - slot['start']) / len(slot['ids'])
        for idx, uuid in enumerate(slot['ids']):
            result.append({
                'start': slot['start'] + duration * idx,
                'end': slot['start'] + duration * (idx + 1),
                'id': uuid,
            })
    return result


class Sniper:
    session = None

    def __init__(self, config):
        self.user = config['authentication']['user']
        self.password = config['authentication']['password']
        self.save_file = config['sniper'].get('save_file', None)
        self.start = datetime.time.fromisoformat(config['sniper'].get('start', '08:00'))
        self.end = datetime.time.fromisoformat(config['sniper'].get('end', '18:00'))
        self.days = list(map(int, config['sniper'].get('days', '0,1,2,3,4').split(',')))
        try:
            if self.save_file is not None and os.path.exists(self.save_file) and self.load_session():
                logging.info(f'Session loaded from {self.save_file}')
            else:
                self.login()
        except Exception as err:
            logging.error(f'Error fetching session: {err}')
            sys.exit(1)
        self.projects = self.get_projects()


    def get_project_info(self, url):
        req = self.session.get(url)
        if req.status_code == 200:
            page_project = req.content.decode('utf-8')
        else:
            logging.warning(f'Failed to get project page, requests.get returned: {req.status_code}')
            return None

        soup = BeautifulSoup(page_project, features='html.parser')

        info = dict()
        link = soup.find('a', text='Subscribe to defense\n')
        if not link:
            return None
        info['project_url'] = url
        info['slots_url'] = PROJECT + link['href']
        info['name'] = soup.find('div', class_='project-header').find('a', href=re.compile(r'/projects/')).text.strip()

        req = self.session.get(info['slots_url'])
        if req.status_code == 200:
            page_slots = req.content.decode('utf-8')
        else:
            logging.warning(f'Failed to get slots page, requests.get returned: {req.status_code}')
            return None

        soup = BeautifulSoup(page_slots, features='html.parser')
        info['csrf_token'] = soup.find('meta', {'name': 'csrf-token'})['content']
        info['slots_json'] = PROJECT + soup.find('div', id='calendar')['data-index-url']
        info['team_id'] = parse_qs(urlparse(info['slots_json']).query)['team_id'][0]
        return info


    def get_projects(self):
        req = self.session.get(PROFILE)
        if req.status_code == 200:
            page_projects = req.content.decode('utf-8')
        else:
            raise Exception(f'Failed to get profile page, requests.get returned: {req.status_code}')

        soup = BeautifulSoup(page_projects, features='html.parser')

        projects = []
        for project in soup.find_all('a', class_='project-item'):
            info = self.get_project_info(project['href'])
            if info is not None:
                projects.append(info)

        return projects


    def store_session(self):
        try:
            with open(self.save_file, 'wb') as fp:
                pickle.dump(self.session, fp)
            return True
        except OSError as err:
            logging.warning(f'Error saving session: {err}')
            return False


    def load_session(self):
        try:
            with open(self.save_file, 'rb') as fp:
                self.session = pickle.load(fp)
            return True
        except OSError as err:
            logging.warning(f'Error loading file: {err}')
            return False


    def login(self):
        self.session = r.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:79.0) Gecko/20100101 Firefox/79.0'})

        req1 = self.session.get(SIGN_IN)
        if req1.status_code == 200:
            page_signin = req1.content.decode('utf-8')
        else:
            raise Exception(f'Failed to get sign-in page, requests.get returned: {req1.status_code}')

        soup = BeautifulSoup(page_signin, features='html.parser')

        post_data = {}
        for form_input in soup.find_all('input'):
            key = form_input.get('name')
            value = form_input.get('value')
            post_data[key] = value

        post_data['user[login]'] = self.user
        post_data['user[password]'] = self.password

        req2 = self.session.post(SIGN_IN, data=post_data, allow_redirects=False)
        if req2.status_code == 200 or req2.status_code == 302:
            if self.save_file and self.store_session():
                logging.info(f'Session saved to {self.save_file}')
            return True
        raise Exception(f'Failed to post login data, requests.post returned: {req2.status_code}')


    def take_slot(self, project, slot):
        post_url = PROJECT + f"/projects/{project['name'].lower()}/slots/{slot['id']}.json?team_id={project['team_id']}"
        body = {
            'start': slot['start'],
            'end': slot['end'],
            '_method': 'put'
        }
        self.session.headers.update({
            "X-CSRF-Token": project['csrf_token'],
        })
        pprint.pprint(self.session.headers)
        req = self.session.post(post_url, data=body)
        if req.status_code == 200:
            logging.info(f"Slot taken at {slot['start']} for project {project['name']} !")
        else:
            logging.warning(f"Failed to take slot {slot['start']} for {project['name']}: {req.status_code}")


    def snipe(self):
        slot_filter = lambda slot: (self.start <= datetime.time(slot['start'].hour, slot['start'].minute) <= self.end) and slot['start'].weekday() in self.days
        while True:
            today = datetime.date.today()
            end_date = today + datetime.timedelta(days=5)
            for project in self.projects:
                url_json = project['slots_json'] + "&start=" + str(today) + "&end=" + str(end_date)

                req = self.session.get(url_json)
                if req.status_code == 200:
                    json = req.json()
                else:
                    logging.warning(f"Cannot fetch json for {url_json}")
                    continue
                slots = make_slots(json)
                slots = list(filter(slot_filter, slots))
                if len(slots) > 0:
                    self.take_slot(project, slots[0])
                    continue
            time.sleep(30)


if __name__=='__main__':
    log_level = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
    }

    parser = argparse.ArgumentParser(description='intra slot sniper')
    parser.add_argument('-d', '--debug', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='INFO')
    parser.add_argument('file', type=argparse.FileType('r'), help='config file')

    args = parser.parse_args()
    logging.basicConfig(level=log_level[args.debug])
    config = configparser.ConfigParser()
    config.read_file(args.file)

    sniper = Sniper(config)

    sniper.snipe()
