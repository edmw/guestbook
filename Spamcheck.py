# coding: iso-8859-1

""" Spamcheck for the guestbook:

    Initialize the spamcheck object with apikey. Afterwards use
    the methods of the problem domain.
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

import os, logging

import urllib.request, urllib.parse, urllib.error
import urllib.request, urllib.error, urllib.parse

###########################################################################

class SpamcheckError(Exception):
    """    Spamcheck error exception
    """
    def __init__(self, text):
        self.text = text
    def __str__(self):
        return self.text

###########################################################################

class Spamcheck(object):

    HAM = 0
    UNKNOWN = 50
    SPAM = 100

    base_url = 'rest.akismet.com/1.1/'

    """    Spamcheck object
    """
    def __init__(self, api_key):
        """ Initializes the spamcheck object.
        """
        self.api_key = api_key

        self.user_agent = "Guestbook/1.0"

    def _get_url(self):
        return 'http://%s.%s' % (self.api_key, self.base_url)

    def _request(self, url, data, headers):
        logging.debug("request url=%s" % url)
        try:
            f = urllib.request.urlopen(urllib.request.Request(url, data, headers))
            response = f.read()
        except Exception as e:
            raise SpamcheckError(str(e))
        logging.debug("response=%s" % response)
        return response

    def _build_data_from_environment(self, comment):
        data = {}
        try:
            data['user_ip'] = os.environ['REMOTE_ADDR']
        except KeyError:
            raise SpamcheckError("No 'user_ip' supplied")
        try:
            data['user_agent'] = os.environ['HTTP_USER_AGENT']
        except KeyError:
            raise SpamcheckError("No 'user_agent' supplied")
        data.setdefault('referrer', os.environ.get('HTTP_REFERER', 'unknown'))
        data.setdefault('permalink', '')
        data.setdefault('comment_type', 'comment')
        data.setdefault('comment_author', '')
        data.setdefault('comment_author_email', '')
        data.setdefault('comment_author_url', '')
        data.setdefault('comment_content', comment)
        #data.setdefault('SERVER_ADDR', os.environ.get('SERVER_ADDR', ''))
        #data.setdefault('SERVER_ADMIN', os.environ.get('SERVER_ADMIN', ''))
        #data.setdefault('SERVER_NAME', os.environ.get('SERVER_NAME', ''))
        #data.setdefault('SERVER_PORT', os.environ.get('SERVER_PORT', ''))
        #data.setdefault('SERVER_SIGNATURE', os.environ.get('SERVER_SIGNATURE', ''))
        #data.setdefault('SERVER_SOFTWARE', os.environ.get('SERVER_SOFTWARE', ''))
        #data.setdefault('HTTP_ACCEPT', os.environ.get('HTTP_ACCEPT', ''))
        data.setdefault('blog', 'sushi-tsu.info')
        return data

    def check(self, comment):
        """    Checks the given comment. Returns ``True`` for spam and ``False`` for ham.

                If the connection to Akismet fails then the ``HTTPError`` or ``URLError`` will be
                raised.
        """
        if self.api_key is None:
            raise SpamcheckError("API key not set")

        data = self._build_data_from_environment(comment)

        url = '%scomment-check' % self._get_url()
        headers = { 'User-Agent': self.user_agent }

        response = self._request(url, urllib.parse.urlencode(data, doseq=True), headers)
        response = response.lower()
        if response == 'true':
            return True
        elif response == 'false':
            return False
        else:
            raise SpamcheckError('missing required argument.')
