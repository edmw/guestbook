# coding: iso-8859-1

"""
"""

# Copyright (c) 2006, Michael Baumgärtner
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

import re

###########################################################################        

class HTMLProducer(object):
    """    Parser object.
    """
    def __init__(self, setName, makeHappy = False):
        self.setName = setName
        
        self.happy_re = list()
        self.happy_re.append(self.__build_happy_re("smiling", (r':-\)', r':\)', r':smile:')))
        self.happy_re.append(self.__build_happy_re("weeping", (r':-\(', r':\(', r':weeep:')))
        self.happy_re.append(self.__build_happy_re("laughing", (r':-\D', r':\D', r':laugh:')))
        self.happy_re.append(self.__build_happy_re("winking", (r';-\)', r';\)', r':wink:')))
        self.happy = makeHappy

    def __build_happy_re(self, name, codes):
        r = r'\1<img src="images/smilies/%s/%s.gif" />\3' % (self.setName, name)
        return [re.compile(r'(\s|^)(%s)(\s|$)' % "|".join(codes)), r]

    def makeHappy(self, line):
        for re_sub in self.happy_re:
            line = re_sub[0].sub(re_sub[1], line)
        return line

    def make(self, text):
        done = list()
        for line in text.replace("\r\n", "\n").split("\n"):
            if self.happy:
                line = self.makeHappy(line)
            done.append(line)
        return "<br />".join(done)
