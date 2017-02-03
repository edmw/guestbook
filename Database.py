# coding: iso-8859-1

""" Database layer for the guestbook:

    Initialize the database object with database name, hostname,
    username and password and optional a prefix for the table
    names. Afterwards use the methods of the problem domain.
    A database connection will be opened automatically the first
    time it will be needed. Don't forget to close the connection.

    database = Database(database, hostname, username, password)
    try:
        database. ...()
    finally:
        database.close()

    All database errors will be wrapped into a DatabaseError Exception.
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

import MySQLdb

SPACE = chr(32)

###########################################################################

class DatabaseError(Exception):
    """    Database error exception
    """
    def __init__(self, text):
        self.text = text
    def __str__(self):
        return self.text

###########################################################################

class Database(object):
    """    Database object
    """
    def __init__(self, database, host, username, password, prefix = ""):
        """ Initializes the database object.
        """
        self.database = database
        self.host = host
        self.username = username
        self.password = password

        self.prefix = prefix

        self.connection = None

    def tablename(self, name):
        """    Builds a tablename with an (optional) given prefix.
        """
        if self.prefix:
            return "%s_%s" % (self.prefix, name)
        return name

    def open(self):
        """    Opens the database connection.
        """
        try:
            self.connection = MySQLdb.connect(
                   host = self.host,
                   user = self.username,
                   passwd = self.password,
                   db = self.database
               )
        except MySQLdb.Error, e:
            raise DatabaseError("Error %d: %s" % (e.args[0], e.args[1]))

    def close(self):
        """    Closes database the connection if open.
        """
        if self.connection:
            self.connection.close()

    def cursor(self):
        """    Returns a cursor, opens the database connection if necessary.
        """
        if not self.connection: self.open()

        if self.connection:
            return self.connection.cursor()

        return None

    def execute(self, statement, function, variables = None):
        """    Executes the given statement and returns the result of the
                given function called with the resulting cursor.
        """
        result = None
        try:
            cursor = self.cursor()
            try:
                cursor.execute(statement, variables)
                result = function(cursor)
            finally:
                cursor.close()
            return result
        except MySQLdb.Error, e:
            raise DatabaseError("Error %d: %s" % (e.args[0], e.args[1]))

    def execute_insert(self, statement, data):
        """    Executes the given insert statement.
        """
        try:
            cursor = self.cursor()
            try:
                cursor.execute(statement, data)
            finally:
                cursor.close()
            return
        except MySQLdb.Error, e:
            raise DatabaseError("Error %d: %s" % (e.args[0], e.args[1]))

    def selectNumberOfEntries(self):
        """    Selects the number of guestbook entries stored in the database.
        """
        return self.execute(
            SPACE.join((
                  "SELECT COUNT(*)",
                  "FROM %s" % self.tablename("entries"),
            )),
            lambda c: int(c.fetchone()[0])
        )

    def selectEntries(self, s, m):
        """    Selects guestbook entries stored in the database.

                Selects m rows beginning from row s.
        """
        return self.execute(
            SPACE.join((
                 "SELECT id, timestamp, name, email, message, rating, hash",
                 "FROM %s" % self.tablename("entries"),
                 "WHERE rating = 0",
                 "ORDER BY id DESC",
                 "LIMIT %s, %s",
             )),
            lambda c: c.fetchall(),
            (s, m)
        )

    def insertEntry(self, secret, name, email, message, rating):
        """    Inserts guestbook entry to the database.
        """
        import time
        timestamp = int(time.time())
        import sha
        hash = sha.new(secret)
        hash.update(str(timestamp))
        hash.update(str(name))
        hash.update(str(email))
        hash.update(str(message))
        self.execute_insert(
            SPACE.join((
                "INSERT INTO %s" % self.tablename("entries"),
                "(timestamp, name, email, message, rating, hash)"
                "VALUES"
                "(%s, %s, %s, %s, %s, %s)"
            )),
            (timestamp, name, email, message, rating, hash.hexdigest())
        )
        return [None, timestamp, name, email, message, rating, hash.hexdigest()]

    def deleteEntryById(self, id, hash):
        self.execute(
            SPACE.join((
                "DELETE FROM %s" % self.tablename("entries"),
                "WHERE",
                "id = %s",
                "AND",
                "hash = %s",
            )),
            lambda c: c,
            (id, hash)
        )

    def deleteEntryByTimestamp(self, timestamp, hash):
        self.execute(
            SPACE.join((
                "DELETE FROM %s" % self.tablename("entries"),
                "WHERE",
                "timestamp = %s",
                "AND",
                "hash = %s",
            )),
            lambda c: c,
            (timestamp, hash)
        )

    def __fetchCode(self, cursor):
        code = cursor.fetchone()
        if code:
            code = code[0]
        return code

    def selectCode(self, id):
        """    Selects guestbook code stored in the database.
        """
        import time
        timestamp = int(time.time()) - 3600*4
        return self.execute(
            SPACE.join((
                 "SELECT code",
                 "FROM %s" % self.tablename("codes"),
                 "WHERE id = %s and timestamp > %s",
             )),
            self.__fetchCode,
            (id, timestamp)
        )

    def insertCode(self, id, code):
        """    Inserts guestbook code into the database.
        """
        import time
        timestamp = int(time.time())
        return self.execute_insert(
           SPACE.join((
               "INSERT INTO %s" % self.tablename("codes"),
               "(id, timestamp, code)"
               "VALUES"
               "(%s, %s, %s)"
           )),
           (id, timestamp, code)
        )

    def deleteCode(self, id):
        """    Deletes guestbook code from the database.
        """
        return self.execute(
            SPACE.join((
                "DELETE FROM %s" % self.tablename("codes"),
                "WHERE id = %s",
            )),
            lambda x: x,
            (id)
        )
