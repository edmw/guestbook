# coding: iso-8859-1

#import cgitb
#cgitb.enable()

""" Controller for the guestbook:

    Setup a dictionary with the configuration parameters
    and call this modules run function together with the
    cgi form data.

    import Guestbook
    Guestbook.run(config, cgi.FieldStorage())
"""

# Copyright (c) 2006, Michael Baumg�rtner
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# * Redistributions of source code must retain the above copyright
#   notice, this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in
#   the documentation and/or other materials provided with the
#   distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import sys, os, os.path, time, random

try:
    import logging
except ImportError:
    logging = None

from Database import Database, DatabaseError

from Spamcheck import Spamcheck

from HTMLProducer import HTMLProducer

from HTMLTemplate import HTMLTemplate
TEMPLATE_DIR = "templates"

###########################################################################

def warning(text):
    if logging:
        logging.warning(text)

class StringHelper(object):
    def __init__(self):
        import string
        self.control_characters = \
            "".join([chr(x) for x in range(32)])
        self.control_characters_crlf = \
            "".join([chr(x) for x in range(32) if x != ord('\r') and x != ord('\n')])
        self.translate_identity = string.maketrans("","")

    def filterALPHANUM(self, text):
        if text:
            return "".join([c for c in text if c.isalnum()])
        return ""

    def stripCONTROL(self, text, crlf = True):
        if text:
            if crlf:
                return text.translate(self.translate_identity, self.control_characters)
            else:
                return text.translate(self.translate_identity, self.control_characters_crlf)
        return ""

    def stripHTML(self, text):
        from HTMLParser import HTMLParser, HTMLParseError

        if text:
            text = self.stripCONTROL(text, crlf = False)

            class Parser(HTMLParser):
                def __init__(self):
                    self.reset()
                    self.data = []
                def handle_data(self, data):
                    self.data.append(data)

            try:
                p = Parser()
                p.feed(text)
                return "".join(p.data)
            except HTMLParseError, x:
                return text

        return ""

###########################################################################

class Mailbase(object):
    def __init__(self, host, port, username, password, sender):
        self.host = host
        self.port = port
        self.username = username
        self.password = password

        self.sender = sender

    def sendMail(self, to, message, subject):
        body = "From: %s\nTo: %s\nSubject: %s\n\n%s" % (
            self.sender,
            to,
            subject,
            str(message),
        )
        sendmail = os.popen("/usr/lib/sendmail -t", "w")
        sendmail.write(body)
        sendmail.close()

    def sendMail_remote(self, to, message, subject):
        import smtplib

        if self.host:
            body = "From: %s\nTo: %s\nSubject: %s\n\n%s" % (
                self.sender,
                to,
                subject,
                str(message),
            )
            try:
                s = smtplib.SMTP(self.host, self.port)
                try:
                    if self.username:
                        s.login(self.username, self.password)
                    s.sendmail(self.sender, to, body)
                finally:
                    s.close()
            except smtplib.SMTPException, x:
                warning("error while sending mail %s" % str(x))

class Mail(object):
    def __init__(self, config):
        self.scriptURL = config["scriptURL"]

    def getUrl(self, **kw):
        import urllib
        if len(kw):
            return "%s?%s" % (self.scriptURL, urllib.urlencode(kw))
        return self.scriptURL

    def __str__(self):
        return "MAILBODY"

class OkMail(Mail):
    def __init__(self, config, entry):
        super(OkMail, self).__init__(config)

        self.entry = dict(zip(["id", "timestamp", "name", "email", "message", "rating", "hash"], entry))

        self.entry["rating"] = str(self.entry["rating"])

        t = time.localtime(self.entry["timestamp"])
        self.entry["date"] = time.strftime("%d %b %Y %H:%M:%S", t)

        u = self.getUrl(page="list")
        self.entry["url_list"] = u

        u = self.getUrl(page = "admin", action= "delete", timestamp = self.entry["timestamp"], hash = self.entry["hash"])
        self.entry["url_delete"] = u

    def __str__(self):
        return """
New Entry (%(rating)s)
------------------------------------------------

Date:
%(date)s

Name:
%(name)s

Email:
%(email)s

Message:
%(message)s

------------------------------------------------
Timestamp: %(timestamp)s Hash: %(hash)s

Show guestbook: %(url_list)s
Delete entry: %(url_delete)s
""" % self.entry

###########################################################################

class Resource(object):
    def __init__(self):
        self.headers = dict()

    def emitHeaders(self, contenttype, charset = None):
        if contenttype:
            if charset:
                self.headers["Content-type"] = "%s; charset=%s" % (contenttype, charset)
            else:
                self.headers["Content-type"] = contenttype
        for key, value in self.headers.items():
            sys.stdout.write("%s: %s\n" % (key, value))
        sys.stdout.write("\n")

    def emit(self):
        raise # abstract class

class HTTPResource(Resource):
    codes = {
        302: "302 Found",
        304: "304 Not Modified",
    }

    def __init__(self, code):
        super(HTTPResource, self).__init__()

        self.code = code

    def emit(self):
        print "Status: %s" % self.codes[self.code]
        self.emitHeaders(None)

###########################################################################

class Page(Resource):
    pageName = None

    def __init__(self, setName,templateDir = None):
        super(Page, self).__init__()
        self.charset = None

        if self.pageName:
            templateData = self.__read(templateDir, setName, self.pageName)
            if templateData:
                self.template = HTMLTemplate(self.render, templateData)
            else:
                self.template = None
        else:
            self.template = None

    def __read(self, templateDir, setName, pageName):
        if templateDir:
            fileName = os.path.join(templateDir, TEMPLATE_DIR, setName, pageName)
        else:
            fileName = os.path.join(os.path.abspath(os.curdir), TEMPLATE_DIR, setName, pageName)
        file = open(fileName)
        if file:
            return file.read()

        return None

    def render(self, template):
        pass

    def emit(self):
        if self.template:
            self.emitHeaders("text/html", self.charset)
            print self.template.render()
        else:
            self.emitHeaders("text/plain")
            print "ERROR EMITTING PAGE"

###########################################################################

class BasePage(Page):
    pageName = None

    def __init__(self, config):
        super(BasePage, self).__init__(config["templateSet"],config["scriptSRC"])
        self.charset = config["charset"]

        self.dateformat = config["dateFormat"]
        self.timeformat = config["timeFormat"]

        import locale
        l = locale.getlocale()
        if not l[0]:
            l = locale.getdefaultlocale()
        self.encoding = l[1]

        self.scriptURL = config["scriptURL"]

    def getUrl(self, **kw):
        import urllib
        if len(kw):
            return "%s?%s" % (self.scriptURL, urllib.urlencode(kw))
        return self.scriptURL

    def formatDate(self, timestamp):
        t = time.localtime(timestamp)
        if self.dateformat:
            s = time.strftime(self.dateformat, t)
            return unicode(s, self.encoding).encode(self.charset)
        else:
            return str(t)

    def formatTime(self, timestamp):
        t = time.localtime(timestamp)
        if self.timeformat:
            s = time.strftime(self.timeformat, t)
            return unicode(s, self.encoding).encode(self.charset)
        else:
            return str(t)

    def setContent(self, template, name, content, raw = False):
        try:
            attr = getattr(template, name)
            if not raw:
                attr.content = content
            else:
                attr.raw = content
        except AttributeError: pass

    def setAttribute(self, template, name, attribute, value):
        try:
            attr = getattr(template, name)
            attr.atts[attribute] = value
        except AttributeError: pass

    def appendAttribute(self, template, name, attribute, value):
        if hasattr(template, name):
            try:
                attr = getattr(template, name)
                v = attr.atts[attribute]
                if v and len(v) > 1:
                    v = "%s %s" % (v, value)
                else:
                    v = value
                attr.atts[attribute] = v
            except AttributeError:
                try:
                    attr.atts[attribute] = value
                except AttributeError: pass
            except KeyError: pass

    def getAttribute(self, template, name, attribute):
        if hasattr(template, name):
            try:
               attr = getattr(template, name)
               return attr.atts[attribute]
            except AttributeError: pass
        return None

    def deleteAttribute(self, template, name, attribute):
        if hasattr(template, name):
            try:
                attr = getattr(template, name)
                del attr.atts[attribute]
            except KeyError: pass

    def render(self, template):
        self.setAttribute(template, "form_link", "href", self.getUrl(page='form'))
        self.setAttribute(template, "list_link", "href", self.getUrl(page='list'))

class ErrorPage(BasePage):
    pageName = "error"

    title = "ERROR"
    message = "ERROR"

    def render(self, template):
        super(ErrorPage, self).render(template)

        template.title.content = self.title
        template.message.content = self.message

class AdminPage(BasePage):
    pageName = "admin"

    title = "ADMIN"
    message = "MESSAGE"

    def render(self, template):
        super(AdminPage, self).render(template)

        template.title.content = self.title
        template.message.content = self.message

class EntryPage(BasePage):
    """    Page for one single entry.
            Not directly used.
    """
    pageName = None

    def __init__(self, config):
        super(EntryPage, self).__init__(config)

        self.producer = HTMLProducer(config["producerSet"], makeHappy = True)

    def formatText(self, text):
        text = text \
            .replace('&', '&amp;') \
            .replace('<', '&lt;') \
            .replace('>', '&gt;') \
            .replace('"', '&quot;')
        return self.producer.make(text)

    def renderEntry(self, node, item):
        num = item[0]
        entry = item[1]
        self.setContent(node, "id", entry[0])
        self.setContent(node, "date", self.formatDate(entry[1]))
        self.setContent(node, "time", self.formatTime(entry[1]))

        if not entry[3]:
            self.setContent(node, "name", entry[2])
            self.setContent(node, "email","")
        else:
            # with email
            # email will not be displayed
            self.setContent(node, "name", entry[2])
            self.setContent(node, "email", "")
            #old code to display email
            #self.setContent(node, "email", entry[2])
            #self.setAttribute(node, "email", "href", "mailto:%s" % entry[3])

        self.setContent(node, "message", self.formatText(entry[4]), raw = True)

        self.setContent(node, "num", str(num))

class ListPage(EntryPage):
    """    Page for a list of entries.
            Extends Entry Page.
    """
    pageName = "list"

    def renderPrevious(self, node, index):
        if self.firstEntryIndex <= 0:
            self.deleteAttribute(node, "previous_link", "href")
        else:
            self.setAttribute(node, "previous_link", "href", self.getUrl(page='list', index=index))

    def renderNext(self, node, index):
        if self.lastEntryIndex >= self.numberOfEntries - 1:
            self.deleteAttribute(node, "next_link", "href")
        else:
            self.setAttribute(node, "next_link", "href", self.getUrl(page='list', index=index))

    def render(self, template):
        super(ListPage, self).render(template)

	if getattr(self, "success", None) is not None:
            template.thanks.emit()

        self.setContent(template, "number_of_entries", str(self.numberOfEntries))
        self.setContent(template, "number_of_entries_per_page", str(self.numberOfEntriesPerPage))
        self.setContent(template, "first_entry_index", str(self.firstEntryIndex + 1))
        self.setContent(template, "last_entry_index", str(self.lastEntryIndex + 1))

        if self.firstEntryIndex <= 0:
            self.appendAttribute(template, "previous", "class", "disabled")
            self.appendAttribute(template, "previous_bottom", "class", "disabled")
        index = self.firstEntryIndex - self.numberOfEntriesPerPage
        template.previous.repeat(self.renderPrevious, (index,))
        template.previous_bottom.repeat(self.renderPrevious, (index,))
        if self.lastEntryIndex >= self.numberOfEntries - 1:
            self.appendAttribute(template, "next", "class", "disabled")
            self.appendAttribute(template, "next_bottom", "class", "disabled")
        index = self.firstEntryIndex + self.numberOfEntriesPerPage
        template.next.repeat(self.renderNext, (index,))
        template.next_bottom.repeat(self.renderNext, (index,))

        num = self.numberOfEntries - self.firstEntryIndex
        template.entry.repeat(self.renderEntry, zip(range(num, num - len(self.entries), -1), self.entries))

class FormPage(EntryPage):
    """    Page for a entry form.
            Extends Entry Page.
    """
    pageName = "form"

    def __init__(self, config):
        super(FormPage, self).__init__(config)

        self.hiddenValues = list()
        self.hiddenValues.append(("page", "form"))
        self.hiddenValues.append(("action", "save"))

        # values
        self.name = ""
        self.email = ""
        self.message = ""

        self.preview = None

        self.errors = list()

    def renderCodeContainer(self, template, value):
        pass

    def renderHiddenValues(self, template, value):
        self.setAttribute(template, "hidden_input", "name", value[0])
        self.setAttribute(template, "hidden_input", "value", value[1])

    def renderInput(self, template, name, value, has_error):
        container = getattr(template, "%s_container" % name, template)
        con = "%s_input" % name
        self.setAttribute(container, con, "name", name)
        if name == "message":
	    self.setContent(container, con, value)
        else:
            self.setAttribute(container, con, "value", value)
        if container is not template:
           if has_error:
               container.atts['class'] = container.atts['class'] + " has-error"
           container.emit()
        if has_error:
           getattr(template, "%s_error" % name).emit()


    def renderForm(self, template):
        self.renderInput(template, "name", self.name, "name" in self.errors)
        self.renderInput(template, "email", self.email, "email" in self.errors)
        self.renderInput(template, "message", self.message, "message" in self.errors)
        self.renderInput(template, "code", self.code, "code" in self.errors)

        url = self.getUrl(type = "image", captcha = self.captcha)
        self.setAttribute(template, "code", "src", url)
        self.hiddenValues.append(("captcha", self.captcha))

        template.hidden_values.repeat(self.renderHiddenValues, self.hiddenValues)

    def render(self, template):
        super(FormPage, self).render(template)

        if self.preview:
            template.entry.repeat(self.renderEntry, [(1, self.preview)])

        self.setAttribute(template, "form", "action", self.getUrl())
        self.setAttribute(template, "form", "method", "post")
        template.form.emit(self.renderForm)

    def validate(self):
        self.errors = list()
        # validate values
        if self.name:
            pass
        else:
            # name is required
            self.errors.append("name")

        if self.message:
            if len(self.message) < 6 or len(self.message) > 2000:
                # message must be between 6 and 2000 characters long
                self.errors.append("message")
        else:
            # message is required
            self.errors.append("message")

        return self.errors

class OkPage(BasePage):
    pageName = "ok"

###########################################################################

class Image(Resource):
    def __init__(self):
        super(Image, self).__init__()

        self.image = None

    def render(self, template):
        pass

    def emit(self):
        self.render()

        if self.image:
            self.emitHeaders("image/png")
            self.image.save(sys.stdout, "PNG")
        else:
            self.emitHeaders("text/plain")
            print "ERROR EMITTING IMAGE"

class CaptchaImage(Image):
    def __init__(self, text, fontfilename, fontsize):
        super(CaptchaImage, self).__init__()

        self.text = text

        self.fontfilename = fontfilename
        self.fontsize = fontsize
        self.font = None

        self.backgroundcolor = 0xffffff
        self.foregroundcolor = 0x000000

    def getFont(self):
        import ImageFont
        if not self.font:
            if self.fontfilename.endswith(".ttf"):
                self.font = ImageFont.truetype(self.fontfilename, self.fontsize)
            elif self.fontfilename.endswith(".pil"):
                self.font = ImageFont.load(self.fontfilename)
            else:
                raise "Unrecognized font type '%s'" % (self.fontfilename[self.fontfilename.rfind(".")+1:])
        return self.font

    def render(self):
        import Image
        import ImageFont
        import ImageDraw

        font = self.getFont()
        dim = font.getsize(self.text)
        image = Image.new('RGB', (dim[0]+5,dim[1]+5), self.backgroundcolor)
        imagedraw = ImageDraw.Draw(image)
        imagedraw.text((3,3), self.text, font = font, fill=self.foregroundcolor)
        self.image = image

###########################################################################

class Controller(object):
    def __init__(self, config, database):
        self.config = config
        self.database = database

    def run(self, fields):
        raise # abstract class

class PageController(Controller):
    def __init__(self, config, database):
        super(PageController, self).__init__(config, database)

        self.mailbase = Mailbase(*[config[k] for k in ("mailHost", "mailPort", "mailUsername", "mailPassword", "mailSender",)])

        self.spamcheck = Spamcheck(*[config[k] for k in ("spamAPIKey",)])

    def createCode(self):
        import sha

        code = str(random.randint(10000, 99999))

        s = sha.new()
        s.update(str(time.time()))
        s.update(str(random.random()))
        s.update(code)
        hash = "%s-%s" % (s.hexdigest(), int(time.time()))

        return hash, code

    def runAdmin(self,  fields):
        sh = StringHelper()

        timestamp = sh.filterALPHANUM(fields.getfirst("timestamp", None))
        hash = sh.filterALPHANUM(fields.getfirst("hash", None))

        page = AdminPage(self.config)

        if timestamp and hash:
            # which action to execute?
            action = sh.filterALPHANUM(fields.getfirst("action", None).lower())

            if action == "delete":
                self.database.deleteEntryByTimestamp(timestamp, hash)

                page.title = "Ok"
                page.message = "Entry deleted!"

            else:
                page.title = "Error"
                page.message = "no action"

        else:
            page.title = "Error"
            page.message = "no entry"

        return page

    def runForm(self, fields):
        sh = StringHelper()

        name = sh.stripHTML(fields.getfirst("name", None))
        email = sh.stripHTML(fields.getfirst("email", None))
        message = sh.stripHTML(fields.getfirst("message", None))

        code = sh.stripCONTROL(fields.getfirst("code", "").strip())
        captcha = sh.stripCONTROL(fields.getfirst("captcha", "").strip())

        # form page
        page = FormPage(self.config)
        # setup form page
        page.name = name
        page.email = email
        page.message = message
        page.code = code
        page.captcha = captcha

        # which action to execute? default is initialize form
        action = sh.filterALPHANUM(fields.getfirst("action", "init").lower())
        if action == "save":
            # validate page
            errors = page.validate()

            if len(errors) == 0:
                # if the entry is valid

                if fields.getfirst("preview", None):
                    # preview entry
                    date = int(time.time())
                    page.preview = [0, date, name, email, message]

                else:
                    # verify code
                    realcode = self.database.selectCode(captcha)
                    if realcode:
                        if code and code.strip() == realcode:
                            # remove code
                            self.database.deleteCode(captcha)

                            # check spam
                            try:
                                rating = Spamcheck.SPAM if self.spamcheck.check(message) else Spamcheck.HAM
                            except HTTPError as x:
                                logging.error("Spamcheck HTTP Error: %s" % str(x))
                                rating = Spamcheck.UNKNOWN
                            except SpamcheckError as x:
                                logging.error("Spamcheck Error: %s" % str(x))
                                rating = Spamcheck.UNKNOWN

                            # insert entry
                            entry = self.database.insertEntry(
                                 self.config["adminSecret"], name, email, message, rating)

                            # send mail
                            mail = OkMail(self.config, entry)
                            self.mailbase.sendMail(
                                 self.config["adminEmail"], mail, "[%s] New entry" % self.config["title"])

                            # display ok page
                            if "templateInlineMessages" in self.config:
                                resource = HTTPResource(302)
                                resource.headers["Location"] = page.getUrl(page="list", index=0, success="True")
                                return resource
                            else:
                                page = OkPage(self.config)

                        else:
                            page.errors.append("code")

                    else:
                        # IMPROVMENT: generate new code if none or expired
                        page = ErrorPage(self.config)
                        page.title = "Error"
                        page.message = "Your code has expired!"

        elif action == "show":
            # ALTERNATIVE: check code and emit error if none or expired
            pass

        else:
            # create code
            captcha, code = self.createCode()
            self.database.insertCode(captcha, code)
            resource = HTTPResource(302)
            resource.headers["Location"] = page.getUrl(page = "form", action = "show", captcha = captcha)
            return resource

        return page

    def runList(self, fields):
        # list page
        page = ListPage(self.config)

	page.success = fields.getfirst("success", None) if fields else None

        numberOfEntries = self.database.selectNumberOfEntries()
        numberOfEntriesPerPage = self.config["numberOfEntriesPerPage"]

        # index of first entry
        index = int(fields.getfirst("index", 0)) if fields else 0
        # keep it into bounds of 0 to number of entries
        if index < 0:
            firstEntryIndex = 0
        elif index >= numberOfEntries:
            firstEntryIndex = numberOfEntries - numberOfEntriesPerPage
        else:
            firstEntryIndex = index

        # index of last entry
        index = firstEntryIndex + numberOfEntriesPerPage
        # keep it into bounds of number of entries per page to number of entries
        if index > numberOfEntries:
            lastEntryIndex = numberOfEntries - 1
        else:
            lastEntryIndex = index - 1

        entries = self.database.selectEntries(firstEntryIndex, numberOfEntriesPerPage)

        # setup list page
        page.numberOfEntries = numberOfEntries
        page.numberOfEntriesPerPage = numberOfEntriesPerPage
        page.firstEntryIndex = firstEntryIndex
        page.lastEntryIndex = lastEntryIndex
        page.entries = entries

        return page

    def run(self, fields):
        sh = StringHelper()

        # which page to display? default is list page
        page = fields.getfirst("page", "list").lower()

        if page == "admin":
            page = self.runAdmin(fields)

        elif page == "form":
            page = self.runForm(fields)

        else:
            page = self.runList(fields)

        return page

class ImageController(Controller):
    def __init__(self, config, database):
        super(ImageController, self).__init__(config, database)

    def run(self, fields):
        captcha = fields.getfirst("captcha", None)

        if os.environ.has_key("HTTP_IF_NONE_MATCH"):
            etag = os.environ["HTTP_IF_NONE_MATCH"]
            if etag == captcha:
                return HTTPResource(304)

        code = self.database.selectCode(captcha)

        image = CaptchaImage(str(code), self.config["imageFontfilename"], self.config["imageFontsize"])
        image.backgroundcolor = self.config["imageBackgroundcolor"]
        image.foregroundcolor = self.config["imageForegroundcolor"]
        image.headers["ETag"] = captcha
        image.headers["Cache-Control"] = "max-age=3600, must-revalidate"

        return image

###########################################################################

def initLogger(filename):
    if filename and logging:
        logging.basicConfig(filename = filename, filemode = "a", level = logging.DEBUG)

def run(config, fields):

    initLogger(config["scriptLogfilename"])

    try:
        database = Database(*[config[k] for k in ("database", "databaseHost", "databaseUsername", "databasePassword", "databasePrefix")])

        try:
            type = fields.getfirst("type", "page")
            if type == "page":
                resource = PageController(config, database).run(fields)
            elif type == "image":
                resource = ImageController(config, database).run(fields)
            else:
                resource = ErrorPage(config)
                resource.title = "Error"
                resource.message = "Invalid resource type"

        finally:
            database.close()

    except DatabaseError, de:
        resource = ErrorPage(config)
        resource.title = "Database Error"
        resource.message = de.text

    # emit resource
    resource.emit()

    #import cgi
    #print "Content-type: text/html\n\n"
    #print cgi.print_environ()
