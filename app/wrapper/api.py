import requests

class GoPlayServerAPI(object):
    def __init__(self, serverid, serverhash):
        self.serverid = serverid
        self.serverhash = serverhash

    