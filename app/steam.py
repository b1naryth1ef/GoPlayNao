import requests, re
from pyquery import PyQuery
from config import STEAM_KEY

def if_len(a, b):
    if len(a):
        return a
    return b

class WorkshopEntity(object):
    def __init__(self, id, title, desc, game, user):
        self.id = id
        self.title = title
        self.desc = desc
        self.game = game
        self.user = user
        self.tags = []

class WorkshopFile(WorkshopEntity):
    def __init__(self, *args):
        super(WorkshopFile, self).__init__(*args)

        self.size = None
        self.posted = None
        self.updated = None
        self.thumb = None
        self.images = []

class WorkshopCollection(WorkshopEntity):
    def __init__(self, *args):
        super(WorkshopCollection, self).__init__(*args)

        self.files = []

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

    def getBanInfo(self, id):
        r = requests.get("http://steamcommunity.com/profiles/%s" % id)
        r.raise_for_status()
        q = PyQuery(r.content)
        bans = q(".profile_ban_status")
        if len(bans):
            return int(bans[0].text_content().split("day(s)", 1)[0].rsplit("\t", 1)[-1].strip())
        return None

    def getWorkshopFile(self, id):
        r = requests.get("http://steamcommunity.com/sharedfiles/filedetails/", params={"id": id})
        r.raise_for_status()
        q = PyQuery(r.content)

        print "Queryin on %s" % id

        breadcrumbs = [(i.text, i.get("href")) for i in q(".breadcrumbs")[0]]
        if not len(breadcrumbs):
            raise Exception("Invalid Workshop ID!")

        gameid = int(breadcrumbs[0][1].rsplit("/", 1)[-1])
        userid = re.findall("steamcommunity.com/(profiles|id)/(.*?)$",
            breadcrumbs[-1][1])[0][-1].split("/", 1)[0]
        title = q(".workshopItemTitle")[0].text

        desc = if_len(q(".workshopItemDescription"),
            q(".workshopItemDescriptionForCollection"))[0].text

        if len(breadcrumbs) == 3:
            size, posted, updated = [[x.text for x in i]
                for i in q(".detailsStatsContainerRight")][0]

            wf = WorkshopFile(id, title, desc, gameid, userid)
            wf.size = size
            wf.posted = posted
            wf.updated = updated
            wf.tags = [i[1].text.lower() for i in q(".workshopTags")]
            thumbs = q(".highlight_strip_screenshot")
            base = q(".workshopItemPreviewImageEnlargeable")
            if len(thumbs):
                wf.images = [i[0].get("src").rsplit("/", 1)[0]+"/" for i in thumbs]
            elif len(base):
                wf.images.append(base[0].get("src").rsplit("/", 1)[0]+"/")
            if len(q(".workshopItemPreviewImageMain")):
                wf.thumb = q(".workshopItemPreviewImageMain")[0].get("src")
            else:
                wf.thumb = wf.images[0]

            return wf
        elif len(breadcrumbs) == 4 and breadcrumbs[2][0] == "Collections":
            wc = WorkshopCollection(id, title, desc, gameid, userid)
            for item in q(".workshopItem"):
                id = item[0].get("href").rsplit("?id=", 1)[-1]
                wc.files.append(self.getWorkshopFile(id))
            return wc

def getSteamAPI():
    return SteamAPI(STEAM_KEY)
