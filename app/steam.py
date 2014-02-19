import requests, re
from config import STEAM_KEY

class SteamAPI(object):
    steam_id_re = re.compile('steamcommunity.com/openid/id/(.*?)$')

    def __init__(self, key):
        self.key = key

    def request(self, url, data, verb="GET"):
        url = "http://api.steampowered.com/%s" % url
        data['key'] = self.key
        function = getattr(requests, verb.lower())
        resp = function(url, params=data)
        resp.raise_for_status()
        return resp.json()

    def getUserInfo(self, id):
        return self.request("ISteamUser/GetPlayerSummaries/v0001", {
            "steamids": id
        })['response']['players']['player'][0]

    def getRecentGames(self, id):
        return self.request("IPlayerService/GetRecentlyPlayedGames/v0001", {"steamid": id})

def getSteamAPI():
    return SteamAPI(STEAM_KEY)