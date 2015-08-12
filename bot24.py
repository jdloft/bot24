#!/usr/bin/python

# Bot24 - A bot for performing misc tasks on Wikimedia sites
# Bot24.py - Main dispatcher for tasks
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

# Parts of logging and threading taken from legoktm's legobot dispatcher

from __future__ import unicode_literals

import os
import sys
import logging
from logging.handlers import TimedRotatingFileHandler

# Setup log file
cur_dir = os.path.dirname(os.path.abspath(__file__))
log_path = cur_dir + "/logs/dispatcher.log"  # path to log
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

