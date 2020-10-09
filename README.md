<p align="center">
  <img src="https://pbs.twimg.com/media/DQl3AJ1WsAEwl_C.jpg"/><br>
</p>

# 42 Slot Sniper
Helper script to find and snipe corrections slots automatically

# Features
- Automatically finds "set as finished" projects
- Looks for available slots meeting requirements in `config.yml`
- Snipes the correction slot

# Installation
First you need to create a virtualenv.
```shell
$ python3 -m venv .venv
$ source .venv/bin/activate
$ pip install -r requirements.txt
```
Then rename or copy the contents of `config.example.yml` and edit it as you need.

# Usage
```shell
$ ./slotsniper.py config.yml
```

# TODO
- [ ] Use cron instead of a sleep loop
- [ ] Custom ranges