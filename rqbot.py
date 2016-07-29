import logging
import sys

import urllib2 #pip ???
import xml.etree.ElementTree

import random
from collections import deque

from irc.bot import SingleServerIRCBot #pip install irc


import config #Make config.py to keep password out of this file

# config
HOST = config.HOST #'irc.twitch.tv'
PORT = config.PORT #6667
USERNAME = config.USERNAME #bot account's username
PASSWORD = config.PASSWORD  # http://www.twitchapps.com/tmi/
#CHANNEL = config.CHANNEL #argv


"""
!addlist [name]
!rq
!rqop
!rqed

"""


url_a = "http://myanimelist.net/malappinfo.php?u="
url_b = "&status=all&type=anime"

valid_names = set()
invalid_names = set()

anime_names = set()
ops = deque()
eds = deque()

def get_anime_list(name):
    if name in valid_names:
        return name + "'s list already loaded"
    #
    if name in invalid_names:
        return "Invalid list: " + name
    #

    url = url_a + name + url_b

    s = urllib2.urlopen(url)
    contents = s.read()
    tree = xml.etree.ElementTree.fromstring(contents)

    if len(tree.findall("error")) == 1:
        invalid_names.add(name)
        return "Invalid list: " + name
    #

    valid_names.add(name)

    new_anime = []

    for anime in tree.findall('anime'):
        title = anime.find('series_title').text
        if name not in anime_names:
            new_anime.append(title)
        #
    #

    global ops
    global eds


    anime_names.update(new_anime)
    random.shuffle(new_anime)
    ops += new_anime
    random.shuffle(new_anime)
    eds += new_anime

    return str(len(new_anime)) + " new anime added to the mix from " + name

#




def _get_logger():
    logger_name = 'vbot'
    logger_level = logging.DEBUG
    log_line_format = '%(asctime)s | %(name)s - %(levelname)s : %(message)s'
    log_line_date_format = '%Y-%m-%dT%H:%M:%SZ'
    logger_ = logging.getLogger(logger_name)
    logger_.setLevel(logger_level)
    logging_handler = logging.StreamHandler(stream=sys.stdout)
    logging_handler.setLevel(logger_level)
    logging_formatter = logging.Formatter(log_line_format, datefmt=log_line_date_format)
    logging_handler.setFormatter(logging_formatter)
    logger_.addHandler(logging_handler)
    return logger_

logger = _get_logger()


class VBot(SingleServerIRCBot):

    VERSION = '1.0.0'

    def __init__(self, host, port, nickname, password, channel):
        logger.debug('VBot.__init__ (VERSION = %r)', self.VERSION)
        SingleServerIRCBot.__init__(self, [(host, port, password)], nickname, nickname)
        self.channel = channel
        self.viewers = []

    def on_welcome(self, connection, event):
        logger.debug('VBot.on_welcome')
        connection.join(self.channel)
        connection.privmsg(event.target, 'Hello world!')

    def on_join(self, connection, event):
        logger.debug('VBot.on_join')
        nickname = self._parse_nickname_from_twitch_user_id(event.source)
        self.viewers.append(nickname)

        if nickname.lower() == connection.get_nickname().lower():
            connection.privmsg(event.target, 'Anime list request bot joined.')

    def on_part(self, connection, event):
        logger.debug('VBot.on_part')
        nickname = self._parse_nickname_from_twitch_user_id(event.source)
        self.viewers.remove(nickname)

    def on_pubmsg(self, connection, event):
        logger.debug('VBot.on_pubmsg')
        message = event.arguments[0]
        logger.debug('message = %r', message)
        # Respond to messages starting with !
        if message.startswith("!"):
            self.do_command(event, message[1:])

    def do_command(self, event, message):
        message_parts = message.split()
        command = message_parts[0]
        
        logger.debug('VBot.do_command (command = %r)', command)

        if command == "version":
            version_message = 'Version: %s' % self.VERSION
            self.connection.privmsg(event.target, version_message)
        
        elif command == "count_viewers":
            num_viewers = len(self.viewers)
            num_viewers_message = 'Viewer count: %d' % num_viewers
            self.connection.privmsg(event.target, num_viewers_message)
        
        elif command == 'exit':
            self.die(msg="")

        #Anime bot stuff
        elif command == "addlist":
            #TODO len
            if len(message_parts) == 1:
                re = "no name given"
            else:
                re = get_anime_list(message_parts[1])
            self.connection.privmsg(event.target, re)

        elif command in {"rq", "rqop", "rqed"}:
            if len(anime_names) == 0:
                re = "Add a list first (!addlist name)"
            else:
                l = None
                r = None

                if command == "rq":
                    command = random.choice(["rqop", "rqed"])
                #
                if command == "rqop":
                    l = ops
                    r = " op"
                else:
                    l = eds
                    r = " ed"
                #
                if len(l) == 0:
                    l += random.shuffle(list(anime_names))
                #
                name = l.popleft()

                re = "!sr " + name + r
            #

            self.connection.privmsg(event.target, re)

        else:
            logger.error('Unrecognized command: %r', command)

    @staticmethod
    def _parse_nickname_from_twitch_user_id(user_id):
        # nickname!username@nickname.tmi.twitch.tv
        return user_id.split('!', 1)[0]

#end class


def main():
    if len(sys.argv) == 1:
        print "Use channel to join as an argument"
        return
    #
    CHANNEL = sys.argv[1]
    if not CHANNEL.startswith("#"): CHANNEL = "#" + CHANNEL
    my_bot = VBot(HOST, PORT, USERNAME, PASSWORD, CHANNEL)
    my_bot.start()


if __name__ == '__main__':
    main()