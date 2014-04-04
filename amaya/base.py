from ircmess import IRCLine
from select import select
import socket

class IRCBot:
    def __init__(self, host, port, nick="AmayaTest1", user="amaya", gecos="Amaya 0.1"):
        self.link = socket.socket()
        self.link.connect((host, port))

        self.__buf = ""

        self.host = host
        self.nick = nick
        self.user = user
        self.gecos = gecos

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

