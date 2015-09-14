#!/usr/bin/env python

# Bot24 - A bot for performing misc tasks on Wikimedia sites
# bot24.py - Task dispatcher
# Copyright (C) 2015 Jamison Lofthouse
#
# This file is part of Bot24.
#
# Bot24 is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Bot24 is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Bot24.  If not, see <http://www.gnu.org/licenses/>.

# A significant amount of infrastructure was taken from legoktm's legobot
# https://github.com/legoktm/legobot

from __future__ import unicode_literals

import os
import sys
import logging
from logging.handlers import TimedRotatingFileHandler
import time
import crontab
import threading
import yaml

# Setup log file
cur_dir = os.path.dirname(os.path.abspath(__file__))
log_path = cur_dir + "/logs/bot24.log"  # path to log
logger = logging.getLogger('dispatcher')  # create logger
logger.setLevel(logging.DEBUG)  # set overall logging level cutoff
handler = TimedRotatingFileHandler(log_path, when='W0', backupCount=20, utc=True)  # create a rotating handler (once a week rotation)
handler.setLevel(logging.DEBUG)  # set handler log level
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))  # log file format
logger.addHandler(handler)
out_handler = logging.StreamHandler(sys.stdout)  # create stdout handler
out_handler.setLevel(logging.INFO)  # only see INFO messages
out_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))  # stdout format
logger.addHandler(out_handler)

# Setup data file
with open(os.path.abspath("config.yaml")) as conf:
    config = yaml.load(conf)

jobs = []
schedules = []

for i in range(len(config["roles"])):
    jobs.append(getattr(getattr(__import__('roles', fromlist=[config["roles"][i]["module"]]), config["roles"][i]["module"]), config["roles"][i]["class"])())
    schedules.append(config["roles"][i]["schedule"])


class JobThread(threading.Thread):
    def __init__(self, job):
        super(JobThread, self).__init__()
        self.job = job()

    def run(self):
        self.job.run()


def schedule():
    times = {}
    for i in range(len(jobs)):
        ctab = crontab.CronTab(schedules[i])
        times[time.time() + ctab.next()] = jobs[i]
    return times

running = {}


def main():
    for job in jobs:
        running[job.__name__] = None
    while True:
        times = schedule()
        minimum = min(list(times))
        logger.info('Sleeping for %s seconds...' % (int(minimum - time.time())))
        time.sleep(minimum - time.time())
        things_to_queue = []
        for time_val, job in dict(times).iteritems():
            if time_val <= time.time():
                logger.info('Queuing %s...' % job.__name__)
                things_to_queue.append(job)
            del times[time_val]
        for job in things_to_queue:
            if running[job.__name__] is None:  # not running
                logger.info('Starting %s...' % job.__name__)
                running[job.__name__] = JobThread(job)
                running[job.__name__].start()
            elif running[job.__name__].isAlive() is False:
                running[job.__name__] = None
                logger.info('Starting %s...' % job.__name__)
                running[job.__name__] = JobThread(job)
                running[job.__name__].start()
            else:
                logger.info('Not starting %s, already running' % job.__name__)

if __name__ == '__main__':
    main()
