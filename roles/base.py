#!/usr/bin/env python

# Bot24 - A bot for performing misc tasks on Wikimedia sites
# base.py - Base class for roles
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

from __future__ import unicode_literals

import logging
from logging.handlers import TimedRotatingFileHandler
import os
import sys
# import time


class Role:
    name = 'base'
    schedule = '@hourly'
    run_method = 'run'
    running = False

    def __init__(self):
        self._logger = None

    @property
    def logger(self):
        if self._logger is None:
            parent_dir = os.path.dirname(os.path.join(os.path.dirname(__file__), ".."))
            log_path = parent_dir + "/logs/bot24.log"  # path to log
            self._logger = logging.getLogger(self.name)  # create logger
            self._logger.setLevel(logging.DEBUG)  # set cutoff
            handler = TimedRotatingFileHandler(log_path, when='W0', backupCount=20, utc=True)  # timed rotator
            handler.setLevel(logging.DEBUG)
            handler.setFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            self._logger.addHandler(handler)
            out_handler = logging.StreamHandler(sys.stdout)  # stdout handler
            out_handler.setLevel(logging.INFO)  # only see INFO messages
            out_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))  # stdout form
            self._logger.addHandler(out_handler)

        return self._logger
