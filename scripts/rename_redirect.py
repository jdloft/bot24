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

"""

from __future__ import unicode_literals

__version__ = '$Id$'

import ast
import codecs
import os
import time
import re

import pywikibot
from pywikibot import Bot, config, pagegenerators

docuReplacements = {
    '&params;': pagegenerators.parameterHelp
}


class LinkLog():
    def __init__(self, file):
        if os.path.exists(os.path.abspath(file)) and os.path.getsize(file) > 0:
            pywikibot.output("Link log exists. Log items will be appended.")
            self.log = codecs.open(os.path.abspath(file), 'a', 'utf-8')
            self.log.write("\n\n========================================")
            self.log.write("\nStarted run on: " + time.strftime("%c"))
            self.log.write("\nRedirects:")
        else:
            pywikibot.output("Using %s as the link log." % file)
            self.log = codecs.open(os.path.abspath(file), 'w', 'utf-8')
            self.log.write("Started run on: " + time.strftime("%c"))
            self.log.write("\n\n----------------------------------------"
                           + "\nRedirects:")
        self.replaced = {}
        self.skipped = {}

    def new_redirect(self, old_redirect, new_redirect, target):
        self.log.write(u"\n" + old_redirect + u" -> " + new_redirect + u" => " + target)

    def save(self):
        self.log.write("\n\n----------------------------------------"
                       + "\nSkipped:")
        for page_title, count in self.skipped.iteritems():
            self.log.write(u"\n" + page_title + u":"
                           u"\n    " + str(count) + u" link(s) skipped")
        self.log.write("\n\n----------------------------------------"
                       + "\nReplaced:")
        for page_title, count in self.replaced.iteritems():
            self.log.write(u"\n" + page_title + u":"
                           u"\n    " + str(count) + u" link(s) replaced")
        self.log.write("\n\n----------------------------------------"
                       + "\nFinished run on: " + time.strftime("%c") + "\n")
        self.log.close()


class RedirectBot(Bot):
    def __init__(self, summary, redirect_titles, fix_double_redirects, link_log, gen_factory, **kwargs):
        super(RedirectBot, self).__init__(**kwargs)
        self.site = pywikibot.Site()
        if summary:
            self.summary = summary
        else:
            self.summary = u"Fix link to old redirect after redirect was moved"
        self.redirects = []
        for old_redirect_title, new_redirect_title in redirect_titles:
            self.redirects.append((pywikibot.Page(self.site, old_redirect_title),
                                   pywikibot.Page(self.site, new_redirect_title)))
        self.fix_double_redirects = fix_double_redirects
        self.link_log = link_log
        self.gen_factory = gen_factory
        self.page_list = {}
        self.saved_pages = 0

    def init_redirects(self, old_redirect, new_redirect, fail_creation_conflict=False):
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

        if(self.fix_double_redirects):
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

                try:
                    new_redirect.save(self.summary)
                    self.saved_pages += 1
                except pywikibot.PageCreatedConflict:
                    if fail_creation_conflict:
                        pywikibot.error("A page creation conflict has occurred at %s. Failing..." % new_redirect.title())
                        return
                    else:
                        pywikibot.error("A page creation conflict has occured at %s. Retrying..." % new_redirect.title())
                        self.init_redirects(old_redirect, new_redirect, fail_creation_conflict=True)
        self.link_log.new_redirect(old_redirect.title(), new_redirect.title(), destination.title())

    def replace_links(self, to_replace, replacement, text, dry=False):
        replaced = 0
        old_text = text
        link_pattern = re.compile(
            r'(?<=\[\[)(?P<title>.*?)(?:#(?P<section>.*?))?(?:\|.*?)?(?=\]\])')
        curpos = 0

        while True:
            match = link_pattern.search(text, pos=curpos)
            if not match:
                break
            if not match.group('title').strip():
                curpos = match.end()
                continue
            title = match.group('title')
            if title.startswith("File:") or title.startswith("Category:"):
                curpos = match.end('title')
                continue
            if title == to_replace:
                replaced += 1
                text = text[0:match.start('title')] + replacement + text[match.end('title'):len(text)]
                curpos = match.end('title') + (len(text) - len(old_text))
            curpos = match.end('title')
        if dry:
            return replaced
        else:
            return (replaced, text)

    def fix_links(self, old_redirect, new_redirect, page):
        replaced = 0
        skipped = 0
        old_text = page.text
        table = re.compile(
            r'\{\|.*\|\}', flags=re.S)

        if(page.namespace() == 0):
            if(page.title().startswith("List of") or page.title().startswith("Channel")):
                (replaced, page.text) = self.replace_links(old_redirect.title(), new_redirect.title(), page.text)
                if(replaced > 0):
                    try:
                        self.link_log.replaced[page.title()] += replaced
                    except KeyError:
                        self.link_log.replaced[page.title()] = replaced
            else:
                tablepos = 0
                while True:
                    table_match = table.search(page.text, pos=tablepos)
                    if not table_match:
                        break
                    table_text = table_match.group(0)
                    (table_replaced, table_text) = self.replace_links(old_redirect.title(), new_redirect.title(), table_text)
                    page.text = page.text[0:table_match.start()] + table_text + page.text[table_match.end():len(page.text)]
                    tablepos = table_match.end() + (len(page.text) - len(old_text))
                    replaced += table_replaced

                tablepos = 0
                while True:
                    table_match = page.text.find("{{Mexico TV station table/top}}", tablepos)
                    table_match_end = page.text.find("|}", table_match)
                    if(table_match == -1):
                        break
                    table_text = page.text[table_match:table_match_end]
                    (table_replaced, table_text) = self.replace_links(old_redirect.title(), new_redirect.title(), table_text)
                    page.text = page.text[0:table_match] + table_text + page.text[table_match_end:len(page.text)]
                    tablepos = table_match_end + (len(page.text) - len(old_text))
                    replaced += table_replaced

                tablepos = 0
                while True:
                    table_match = page.text.find("{{Mexico TV station table/top2}}", tablepos)
                    table_match_end = page.text.find("|}", table_match)
                    if(table_match == -1):
                        break
                    table_text = page.text[table_match:table_match_end]
                    (table_replaced, table_text) = self.replace_links(old_redirect.title(), new_redirect.title(), table_text)
                    page.text = page.text[0:table_match] + table_text + page.text[table_match_end:len(page.text)]
                    tablepos = table_match_end + (len(page.text) - len(old_text))
                    replaced += table_replaced

                skipped = self.replace_links(old_redirect.title(), new_redirect.title(), page.text, True)
                if(replaced > 0):
                    try:
                        self.link_log.replaced[page.title()] += replaced
                    except KeyError:
                        self.link_log.replaced[page.title()] = replaced
                if(skipped > 0):
                    try:
                        self.link_log.skipped[page.title()] += skipped
                    except KeyError:
                        self.link_log.skipped[page.title()] = skipped
        else:
            (replaced, page.text) = self.replace_links(old_redirect.title(), new_redirect.title(), page.text)
            if(replaced > 0):
                try:
                    self.link_log.replaced[page.title()] += replaced
                except KeyError:
                    self.link_log.replaced[page.title()] = replaced

    def run(self):
        for old_redirect, new_redirect in self.redirects:
            pywikibot.output("\nMoving %s to %s." % (old_redirect.title(), new_redirect.title()))
            self.init_redirects(old_redirect, new_redirect)
            generator = self.gen_factory.getCombinedGenerator(gen=old_redirect.getReferences(content=True))
            pywikibot.output("Checking for eligible links for replacement")
            for page in generator:
                pywikibot.output("Checking: %s" % page.title())
                try:
                    self.fix_links(old_redirect, new_redirect, self.page_list[page.title()][1])
                except KeyError:
                    self.page_list[page.title()] = (page.text, page)  # Save old page text in tuple, page will be mutated by fix_links
                    self.fix_links(old_redirect, new_redirect, self.page_list[page.title()][1])

        for page_title, (original_text, page) in self.page_list.iteritems():
            if(original_text == page.text):
                continue

            pywikibot.output("Saving: %s" % page.title())
            edit_try = 1
            while(edit_try <= 3):
                pywikibot.showDiff(original_text, page.text)
                if not page.botMayEdit():  # Explicit call just to be safe
                    pywikibot.error("Editing by bots restricted on %s." % page.title())
                if not page.canBeEdited():
                    pywikibot.error("Editing protected on %s." % page.title())

                try:
                    self.saved_pages += 1
                    page.save(self.summary)
                    break
                except pywikibot.EditConflict:
                    if(edit_try < 3):
                        pywikibot.error("An edit conflict has occurred at %s. Retrying..." % page.title(asLink=True))
                        edit_try += 1
                        self.fix_links(old_redirect, new_redirect, self.page_list[page.title()][1])
                        original_text = self.page_list[0]
                        page = self.page_list[1]
                    else:
                        pywikibot.output("An edit conflict has occurred at %s more than 3 times. Skipping..." % page.title(asLink=True))
                        break
        pywikibot.output("\nPages saved: " + str(self.saved_pages))


def main(*args):
    redirectfile = None
    oldredirect = None
    newredirect = None
    summary = None
    fix_double_redirects = True
    link_log = None
    redirects = []

    local_args = pywikibot.handle_args(args)
    gen_factory = pagegenerators.GeneratorFactory()

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
        elif arg.startswith("-linklog"):
            if len(arg) == 8:
                link_log = pywikibot.input(
                    u'What file would you like to use for the link log?')
            else:
                link_log = LinkLog(arg[9:])
        else:
            gen_factory.handleArg(arg)

    if redirectfile and (oldredirect or newredirect):
        pywikibot.output("Not using redirect file due to old redirect or new redirect being set.")
    if redirectfile and not oldredirect and not newredirect:
        with codecs.open(redirectfile, 'r', config.textfile_encoding) as f:
            for line_number, line in enumerate(f.readlines()):
                if(line.startswith("#")):
                    continue
                try:
                    line_eval = ast.literal_eval(line)
                except ValueError:
                    pywikibot.error("The redirect file contains an invalid line at line %s." % (line_number + 1))
                else:
                    if(type(line_eval) == tuple):
                        if(len(line_eval) == 2):
                            redirects.append(line_eval)
                        else:
                            pywikibot.error("The redirect file contains an invalid tuple at line %s." % (line_number + 1))
                    else:
                        pywikibot.error("Redirect file contains a line that isn't a tuple!")
    elif oldredirect and newredirect:
        redirects.append((oldredirect, newredirect))
    elif oldredirect or newredirect:
        pywikibot.error("Only one of -oldredirect or -newredirect was set.")
        return
    else:
        pywikibot.error("None of -oldredirect and -newredirect or -redirectfile specified!")
        return

    bot = RedirectBot(summary, redirects, fix_double_redirects, link_log, gen_factory)
    bot.run()
    link_log.save()


if __name__ == "__main__":
    main()
