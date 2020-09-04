<p align="center">
  <img src="https://pbs.twimg.com/media/DQl3AJ1WsAEwl_C.jpg"/><br>
</p>

# 42 Slot Sniper
Helper script to find and snipe corrections slots automatically

# Features
- Automatically finds "set as finished" projects
- Looks for available slots meeting requirements in `config.ini`
- Snipes the correction slot

# Installation
First you need to create a virtualenv (or make sure [bs4](https://www.crummy.com/software/BeautifulSoup/bs4/doc/) and [requests](https://requests.readthedocs.io/en/master/) are installed)
```shell
$ python3 -m venv .venv
$ source .venv/bin/activate
$ pip install -r requirements.txt
```
Then rename or copy the contents of `config.example.ini` and edit it as you need.

# Usage
```shell
$ ./slotsniper.py config.ini
```

# TODO
- [ ] blacklist projects
- [ ] ???