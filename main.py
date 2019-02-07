#!/usr/bin/env python

# Bot24 - A bot for performing misc tasks on Wikimedia sites
# main.py - Task dispatcher
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
log_path = cur_dir + "/logs/"  # path to log
logger = logging.getLogger('dispatcher')  # create logger
logger.setLevel(logging.DEBUG)  # set overall logging level cutoff
handler = TimedRotatingFileHandler(log_path + "dispatcher.log", when='W0', backupCount=20, utc=True)  # create a rotating handler (once a week rotation)
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

jobs = {}
schedules = {}

for i in range(len(config["scripts"])):
    jobs[config["scripts"][i]["name"]] = getattr(__import__('scripts', fromlist=[config["scripts"][i]["module"]]), config["scripts"][i]["module"])
    schedules[config["scripts"][i]["name"]] = config["scripts"][i]["schedule"]


class JobThread(threading.Thread):
    def __init__(self, job):
        super(JobThread, self).__init__()
        self.daemon = True
        self.job = job

    def run(self):
        self.job.main()


def schedule():
    times = {}
    for job_name in jobs.iterkeys():
        ctab = crontab.CronTab(schedules[job_name])
        times[time.time() + ctab.next()] = job_name
    return times


running = {}

def main():
    for job_name, job in jobs.iteritems():
        running[job_name] = None
    while True:
        times = schedule()
        minimum = min(list(times))
        logger.info('Sleeping for %s seconds...' % (int(minimum - time.time())))
        time.sleep(minimum - time.time())
        things_to_queue = []
        for time_val, job_name in dict(times).iteritems():
            if time_val <= time.time():
                logger.info('Queuing %s...' % job_name)
                things_to_queue.append(job_name)
            del times[time_val]
        for job_name in things_to_queue:
            if running[job_name] is None:  # not running
                logger.info('Starting %s...' % job_name)
                running[job_name] = JobThread(jobs[job_name])
                running[job_name].start()
            elif running[job_name].isAlive() is False:
                running[job_name] = None
                logger.info('Starting %s...' % job_name)
                running[job_name] = JobThread(jobs[job_name])
                running[job_name].start()
            else:
                logger.info('Not starting %s, already running' % job_name)


if __name__ == '__main__':
    main()
