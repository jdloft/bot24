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

from roles import testing, testing2

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

roles = [
    testing.TestBot,
    testing2.Test2Bot
]

jobs = {}
for role in roles:
    jobs[role.name] = role


class JobThread(threading.Thread):
    def __init__(self, job):
        super(JobThread, self).__init__()
        self.job = job()

    def run(self):
        getattr(self.job, self.job.run_method)('-family:wikipedia', '-lang:en')


def schedule():
    times = {}
    for job in jobs.values():
        ctab = crontab.CronTab(job.schedule)
        times[time.time() + ctab.next()] = job
    return times


def main():
    while True:
        times = schedule()
        minimum = min(list(times))
        logger.info('Sleeping for %s...' % (minimum - time.time()))
        time.sleep(minimum - time.time())
        things_to_queue = []
        for time_val, job in dict(times).iteritems():
            if time_val <= time.time():
                logger.info('Queuing %s...' % job.name)
                things_to_queue.append(job)
            del times[time_val]
        for job in things_to_queue:
            if job.running is False:
                logger.info('Starting %s...' % job.name)
                thread = JobThread(job)
                thread.start()
            else:
                logger.info('Not starting %s - already running' % job.name)

if __name__ == '__main__':
    main()
