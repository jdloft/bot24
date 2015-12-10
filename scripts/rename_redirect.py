#!/usr/bin/python
# -*- coding: utf-8 -*-

# Bot24 - A bot for performing misc tasks on Wikimedia sites
# rename_redirect.py - Script that renames a set of redirects
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

"""
This bot renames a list of redirects.

This script understands the following command-line arguments:

&params;

Furthermore, the following command line parameters are supported:

    -summary       Summary of the edit made by bot.

    -dry           Suppress changes, but show what would have been
                   changed.

"""

from __future__ import unicode_literals

__version__ = '$Id$'

import ast
import codecs
import re

import pywikibot
from pywikibot import Bot, config, pagegenerators

docuReplacements = {
    '&params;': pagegenerators.parameterHelp
}


class RedirectBot(Bot):
    def __init__(self, summary, **kwargs):
        super(RedirectBot, self).__init__(**kwargs)
        self.site = pywikibot.Site()
        self.summary = summary

    def init_redirects(self, old_redirect, new_redirect):
        try:  # Verify redirect target
            destination = old_redirect.getRedirectTarget()
        except pywikibot.IsNotRedirectPage:
            pywikibot.error(u"%s is not a redirect." % old_redirect.title())
            return
        except pywikibot.CircularRedirect:
            pywikibot.error(u'%s points to a circular redirect.' % old_redirect.title())
            return
        except pywikibot.NoPage:
            pywikibot.error(u"%s doesn't exist." % old_redirect.title())
            return

        pywikibot.output("%s was found. Proceeding..." % old_redirect.title())
        pywikibot.output("Target: %s" % destination.title())

        try:  # Handle double redirects
            destination = destination.getRedirectTarget()
            pywikibot.output(u"%s points to another redirect. Going to resolve the double redirect." % old_redirect.title())
            try:
                destination.get()
            except pywikibot.NoPage:
                pywikibot.error(u"%s points to a redirect that points to a non-existent page!" % old_redirect.title())
                return
        except pywikibot.IsNotRedirectPage:
            pass

        try:  # Handle new redirect
            new_redirect_target = new_redirect.getRedirectTarget().title()
            if(new_redirect_target == destination.title()):
                pywikibot.output(u"%s is a redirect and already points to the correct target." % new_redirect.title())
            else:
                pywikibot.error(u"%s is a redirect but doesn't point to the correct target!" % new_redirect.title())
                return
        except pywikibot.IsNotRedirectPage:
            try:
                new_redirect.get()
                pywikibot.error(u"%s exists and isn't a redirect!" % new_redirect.title())
                return
            except pywikibot.NoPage:
                pywikibot.output(u"%s doesn't exist. Creating it now..." % new_redirect.title())
                old_text = new_redirect.text
                new_redirect.text = u"#REDIRECT [[%s]]" % destination.title()
                pywikibot.showDiff(old_text, new_redirect.text)
                if not new_redirect.botMayEdit():  # Explicit call just to be safe
                    raise pywikibot.OtherPageSaveError(new_redirect, "Editing restricted by {{bots}} template")
                if(self.summary):
                    new_redirect.save(self.summary)
                else:
                    new_redirect.save(u"Change redirect target to %s for redirect move" % destination.title())

    def fix_links(self, old_redirect, new_redirect):
        generator = old_redirect.getReferences(content=True)
        link_pattern = re.compile(
            r'(?<=\[\[)(?P<title>.*?)(?:#(?P<section>.*?))?(?:\|.*?)?(?=\]\])')
        for page in generator:
            pywikibot.output("Working on: %s" % page.title())
            old_text = page.text
            curpos = 0
            while True:
                match = link_pattern.search(page.text, pos=curpos)
                if not match:
                    break
                if not match.group('title').strip():
                    curpos = match.end()
                    continue
                title = match.group('title')
                if title.startswith("File:") or title.startswith("Category:"):
                    curpos = match.end()
                    continue
                if title == old_redirect.title():
                    page.text = page.text[0:match.start('title')] + new_redirect.title() + page.text[match.end('title'):len(page.text)]
                curpos  = match.end('title') + (len(page.text[0:match.start('title')] + new_redirect.title() + page.text[match.end('title'):len(page.text)]) - len(old_text))

            pywikibot.showDiff(old_text, page.text)
            if not page.botMayEdit():  # Explicit call just to be safe
                raise pywikibot.OtherPageSaveError(page, "Editing restricted by {{bots}} template")
            if(self.summary):
                page.save(self.summary)
            else:
                page.save(u"Fix link to old redirect after redirect was moved")

    def run(self, redirects):
        for old_redirect_title, new_redirect_title in redirects:
            pywikibot.output("Moving %s to %s." % (old_redirect_title, new_redirect_title))
            old_redirect = pywikibot.Page(self.site, old_redirect_title)  # Get page object from plain title
            new_redirect = pywikibot.Page(self.site, new_redirect_title)
            self.init_redirects(old_redirect, new_redirect)
            self.fix_links(old_redirect, new_redirect)


def main(*args):
    redirectfile = None
    oldredirect = None
    newredirect = None
    summary = None
    fix_double_redirects = True
    redirects = []

    local_args = pywikibot.handle_args(args)

    for arg in local_args:
        if arg.startswith("-redirectfile"):
            if len(arg) == 13:
                redirectfile = pywikibot.input(
                    u'What file do you want the old and new redirects to be taken from?')
            else:
                redirectfile = arg[14:]
        elif arg.startswith("-oldredirect"):
            if len(arg) == 12:
                oldredirect = pywikibot.input(
                    u'What is the old redirect that you would like to move?')
            else:
                oldredirect = arg[13:]
        elif arg.startswith("-newredirect"):
            if len(arg) == 12:
                newredirect = pywikibot.input(
                    u'What is the new redirect you would like the old redirect to be moved to?')
            else:
                newredirect = arg[13:]
        elif arg.startswith("-summary"):
            if len(arg) == 8:
                summary = pywikibot.input(
                    u'What summary would you like to use?')
            else:
                summary = arg[9:]
        elif arg.startswith("-nofixdredirects"):
            fix_double_redirects = False
    if redirectfile and (oldredirect or newredirect):
        pywikibot.output("Not using redirect file due to old redirect or new redirect being set.")
    if redirectfile and not oldredirect and not newredirect:
        with codecs.open(redirectfile, 'r', config.textfile_encoding) as f:
            for line in f.readlines():
                if(line.startswith("#")):
                    continue
                try:
                    line_eval = ast.literal_eval(line)
                except:
                    pywikibot.error("Redirect file contains an invalid line!")
                else:
                    if(type(line_eval) == tuple):
                        if(len(line_eval) == 2):
                            redirects.append(line_eval)
                        else:
                            pywikibot.error("Redirect file contains an invalid tuple!")
                    else:
                        pywikibot.error("Redirect file contains a line that isn't a tuple!")

    bot = RedirectBot(summary)
    bot.run(redirects)

if __name__ == "__main__":
    main()
