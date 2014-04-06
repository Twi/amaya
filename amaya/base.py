from exceptions import ConnectionError
from ircmess import IRCLine
from select import select

import socket
import ssl

class IRCBot:
    """
    An IRCBot is a class that maintains a connection with a remote IRC server
    and keeps track of channel members, information about the remote server,
    and other things that the protocol gives that users might find useful.
    """

    def __init__(self, host, port, ssl=False, nick="AmayaTest1", user="amaya",
            gecos="Amaya 0.1", netname="ExampleNet", nickservpass=None,
            encoding="UTF-8", sasl=False, debug=False, autojoin=[]):
        """
        Args: remote host to connect to, port number to connect to

        Keyword args:
         - ssl: Whether or not to use SSL for the connection
         - nick: nickname of bot
         - user: ident the bot uses
         - gecos: real name of the bot
         - netname: Name of the network you're connecting to
         - nickservpass: Password to use for authentication
         - encoding: Character encoding to use
         - sasl: Whether or not to attempt SASL authentication
        """

        # Lots of variables, no way around this.
        self.link = socket.socket()
        self.link.connect((host, port))

        self.__buf = ""

        self.host = host
        self.ssl = ssl
        self.nick = nick
        self.user = user
        self.gecos = gecos
        self.netname = netname
        self.nickservpass = nickservpass
        self.encoding = encoding
        self.sasl = sasl
        self.debug = debug
        self.autojoin = []

        self.servername = ""
        self.ircdver = ""
        self.snomask = ""
        self.loggedinas = ""

        self.ircdumodes = []
        self.umodes = []
        self.channels = {}
        self.clients = {} # XXX: Is this a good idea?
        self.isupport = {}

        if self.ssl:
            ssl.wrap_socket(self.link)

        # Get a list of IRCv3 CAPs
        self.send_line("CAP LS")

        # If we aren't using SASL, we can just directly send NICK and USER
        if not self.sasl:
            self.send_line("NICK %s" % self.nick)
            self.send_line("USER {0} {0} {0} :{1}".format(user, gecos))

    def send_line(self, line):
        """
        Takes in a raw line and sends it to the server. Don't use this without
        good reason.
        """

        if debug:
            print(">>>", line)

        self.link.send(bytes("%s\r\n" % line, "UTF-8"))

    # The following functions are high level binds to common IRC client commands

    def join(self, channel):
        """
        Join a channel and set up the appropriate data structures.
        """

        self.channels[channel.upper()] = {}

        self.send_line("JOIN %s" % channel)

    def part(self, channel, reason="Leaving"):
        """
        Leave a channel and forget about it.
        """

        del self.channels[channel.upper()]

        self.send_line("PART %s :%s" % (channel, reason))

    def message_like(self, kind, target, message):
        """
        NOTICE and PRIVMSG are pretty similar commands. Handle both of them
        the same.
        """

        if message == "":
            message = " "

        self.send_line("%s %s :%s" % (kind, target, message))

    def notice(self, target, message):
        """
        Sends a NOTICE to someone. Please use this over PRIVMSG. Other bots
        will not loop.
        """

        self.message_like("NOTICE", target, message)

    def privmsg(self, target, message):
        """
        Sends a PRIVMSG to someone.
        """

        self.message_like("PRIVMSG", target, message)

    # Now is select() baggage and the line scraper

    def process(self):
        """
        Call this function when you have data on the socket.
        """

        tbuf = self.link.recv(2048)
        tbuf = self.__buf + tbuf.decode('UTF-8')

        lines = tbuf.split("\r\n")

        self.__buf = lines[-1]
        lines = lines[:-1]

        for line in lines:
            self.process_line(line)

    def process_line(self, line):
        """
        Take a single line of traffic and process it.
        """

        if debug:
            print("<<<", line)

        line = IRCLine(line)
        if line.verb == "PING":
            self.send_line("PONG :%s" % line.args[-1])

        if hasattr(self, "on_%s" % line.verb):
            func = getattr(self, "on_%s" % line.verb)
            func(line)

    # Base implementation of protocol verbs
    # Numerics should be first and in numerical order

    def on_001(self, line):
        """
        RPL_WELCOME: This numeric is shown on registration. It shows the network
        name.
        """

        self.netname = line.args[-1].split()[3]

    def on_004(self, line):
        """
        RPL_MYINFO: This numeric shows the server name, ircd type and version,
        as well as user and modes it supports.
        """

        self.servername = line.args[0]
        self.ircdver = line.args[1]
        # Not scraping CMODES out here, 005 gives me a better place to find
        # what has what syntax
        self.ircdumodes = line.args[3]

        # Apparently people care about +B that it's worth just setting it if
        # available and not worrying about accidentally breaking some weird
        # bot rule.
        if "B" in self.ircdumodes:
            self.send_line("MODE %s +B" % self.nick)

    def on_005(self, line):
        """
        RPL_ISUPPORT: Shows things that the server you are connected to supports.
        This includes the list of prefixes and in some cases their meaning.
        RPL_ISUPPORT strings vary from server to server, so best effort will be
        made to support the most common ones, as well as the ones that the testnet
        supports.
        """

        isupport = line.args[1:]

        for supp in isupport:
            supp = supp.split("=")

            if len(supp) == 1:
                self.isupport[supp[0]] = None

            else:
                self.isupport[supp[0]] = supp[1]

    def on_900(self, line):
        """
        RPL_LOGGEDIN: Sent when the ircd logs you in via services sucessfully.
        Some IRC daemons send this twice when you authenticate with sasl, but
        other irc daemons only send this once.
        """

        pass

    # Put named verbs past here

    def on_CAP(self, line):
        if line.args[1] == "LS":
            for cap in line.args[-1].split():
                if cap == "sasl":
                    if self.sasl:
                        self.send_line("AUTHENTICATE PLAIN")
                elif cap == "account-notify":
                    self.send_line("CAP REQ account-notify")
                elif cap == "multi-prefix":
                    self.send_line("CAP REQ multi-prefix")
            if not self.sasl:
                self.send_line("CAP END")

    def on_ERROR(self, line):
        """
        ERROR is sent when the ircd kills off the connection forcibly.
        This should error out with something spectacular.
        """

        raise ConnectionError(line.args[-1])

