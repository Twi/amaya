class ConnectionError(Exception):
    def __init__(self, string):
        self.string = string
    def __repr__(self):
        return "<ConnectionError: %s>" % self.string

