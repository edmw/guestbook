# coding: iso-8859-1

# Example configuration

# See the values in the following section and change them for your needs.
# But don't remove one or some of these values. If you want to unset a
# value change it to None or an empty string.

title = "Guestbook"

# charset: select the charset in which the generated html will be delivered
# charset: note that the used templates also have to use this charset
charset = "utf-8"

# language: select the language for generated texts
language = "en"

# datetimeformat:
dateFormat = "%A, %d. %B %Y"
timeFormat = "%H:%M"

# template
templateSet = "guestbook-en"
templateInlineMessages = True

# converter
producerSet = "default"

# database
database = "..."
databaseHost = "..."
databaseUsername = "..."
databasePassword = "..."
databasePrefix = "..."

# mail
mailHost = "..."
mailPort = 25
mailUsername = None
mailPassword = None
mailSender = "guestbook@..."

# spamcheck
spamAPIKey = "..."

# image
imageFontname = "hartin.pil"
imageFontsize = 25
imageBackgroundcolor = 0xcefbff
imageForegroundcolor = 0x000000

# guestbook
numberOfEntriesPerPage = 25

# admin
adminSecret = "..."
adminEmail = "..."

def get():
    return dict([(k, v) for k, v in globals().items() if not k.startswith("__")])
