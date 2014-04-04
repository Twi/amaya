from base import IRCBot

class MyBot(IRCBot):
    def on_376(self, line):
        self.send_line("JOIN #ponyvilletest")

bot = MyBot("irc.yolo-swag.com", 6667)

bots = [bot]

while True:
    socks = [x.link for x in bots]
    backref = {}

    # back-reference the bots by their sockets as select()
    # returns a socket object
    for bot in bots:
        backref[bot.link] = bot

    ro, wo, eo = select(socks, [], [])

    for sock in ro:
        backref[sock].process()

