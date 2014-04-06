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
            encoding="UTF-8", sasl=False):
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

        self.servername = ""
        self.ircdver = ""
        self.snomask = ""

        self.umodes = []
        self.channels = {}
        self.isupport = {}

        if self.ssl:
            ssl.wrap_socket(self.link)

        self.send_line("NICK %s" % self.nick)
        self.send_line("USER {0} {0} {0} :{1}".format(user, gecos))

    def send_line(self, line):
        print(">>>", line)
        self.link.send(bytes("%s\r\n" % line, "UTF-8"))

    def process(self):
        tbuf = self.link.recv(2048)
        tbuf = self.__buf + tbuf.decode('UTF-8')

        lines = tbuf.split("\r\n")

        self.__buf = lines[-1]
        lines = lines[:-1]

        for line in lines:
            self.process_line(line)

    def process_line(self, line):
        print("<<<", line)
        line = IRCLine(line)
        if line.verb == "PING":
            self.send_line("PONG :%s" % line.args[-1])

        if hasattr(self, "on_%s" % line.verb):
            func = getattr(self, "on_%s" % line.verb)
            func(line)

    # Base implementation of protocol verbs

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

        # Apparently people care about +B that it's worth just setting it if
        # available and not worrying about accidentally breaking some weird
        # bot rule.
        if "B" in line.args[3]:
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

    def on_ERROR(self, line):
        """
        ERROR is sent when the ircd kills off the connection forcibly.
        This should error out with something spectacular.
        """

        raise ConnectionError(line.args[-1])

