"""
The worker is a simple schedule based job queue that fires off jobs on a
regular basis to keep things up to date and running.
"""
import time, random, thread, json
from steam import SteamAPI
from database import *
from dateutil.relativedelta import relativedelta
from datetime import datetime
from storage import STORAGE
import itertools, tempfile, sqlite3

schedules = {}

s = SteamAPI.new()

def schedule(**kwargs):
    """
    Schedules a task
    """
    def deco(f):
        schedules[f.__name__] = (datetime.utcnow(), relativedelta(**kwargs), f)
        return f
    return deco

LOBBY_TIMEOUT = 15

@schedule(hours=4)
def task_update_names():
    """
    Updates all usernames in the system
    """
    for user in User.select().where():
        user.updateName()

@schedule(seconds=5)
def task_user_timeout():
    return
    for lobby in Lobby.select().where((Lobby.state != LobbyState.LOBBY_STATE_UNUSED) &
            (Lobby.state != LobbyState.LOBBY_STATE_PLAY)):
        for member in lobby.members:
            u = User.select().where(User.id == member).get()
            if (time.time() - float(redis.get("user:%s:lobby:%s:ping" % (member, lobby.id)) or 0)) > 20:
                lobby.sendAction({
                    "type": "quit",
                    "member": u.id,
                    "msg": "%s timed out from the lobby!" % u.username
                })
                redis.srem("lobby:%s:members" % lobby.id, u.id)
                lobby.save()

@schedule(seconds=5)
def task_lobby_timeout():
    # TODO: fix/test
    return
    """
    If a user times out from a lobby, time them out
    """
    for lobby in Lobby.select().where((Lobby.state != LobbyState.LOBBY_STATE_UNUSED)):
        for member in lobby.members:
            u = User.select().where(User.id == member).get()
            if not redis.exists("lobby:ping:%s:%s" % (lobby.id, member)):
                continue
            if (time.time() - float(redis.get("lobby:ping:%s:%s" % (lobby.id, member)))) > 20:
                print redis.get("lobby:ping:%s:%s" % (lobby.id, member))
                print "Cleaning up member!"
                lobby.sendAction({
                    "type": "quit",
                    "member": u.id,
                    "msg": "%s timed out from the lobby!" % u.username
                })
                redis.srem("lobby:%s:members" % lobby.id, u.id)
                lobby.save()

@schedule(minutes=5)
def task_lobby_cleanup():
    for lobby in Lobby.select().where(Lobby.state != LobbyState.LOBBY_STATE_UNUSED):
        if len(lobby.members): continue
        print "Cleaning up lobby: %s" % lobby.id
        lobby.state = LobbyState.LOBBY_STATE_UNUSED
        lobby.cleanup()
        lobby.save()

# Our workshop ID
WORKSHOP_ID = "231287804"

@schedule(minutes=5)
def task_load_workshop_maps():
    q = s.getWorkshopFile(WORKSHOP_ID)

    for item in q.files:
        map_name = item.title
        if not item.title.startswith("de_"):
            map_name = "de_" + item.title.lower()

        q = Map.select().where(Map.name == map_name)
        if q.count():
            q = q[0]
        else:
            q = Map()
            q.name = map_name
            if "hostage" in item.tags:
                q.mtype = MapType.MAP_TYPE_HOSTAGE
            else:
                q.mtype = MapType.MAP_TYPE_BOMB
            q.custom = True

        q.title = item.title
        q.image = item.thumb or item.images[0]
        q.save()

    redis.delete("maps")
    for mp in Map.select():
        print "Adding map %s to maps cache!" % mp.title
        redis.zadd("maps", json.dumps(mp.format()), mp.level)

@schedule(seconds=30)
def task_stats_cache():
    data = {
        "current": {
            "players": {
                "searching": 0,
                "playing": 0
            },
            "lobbies": {
                "searching": 0,
                "playing": 0
            },
            "servers": {
                "open": 0,
                "used": 0,
            },
            "matches": 0
        }
    }

    for lobby in Lobby.select().where(Lobby.state == LobbyState.LOBBY_STATE_SEARCH):
        data['current']['players']['searching'] += len(lobby.members)
        data['current']['lobbies']['searching'] += 1

    for lobby in Lobby.select().where(Lobby.state == LobbyState.LOBBY_STATE_PLAY):
        data['current']['players']['playing'] += len(lobby.members)
        data['current']['lobbies']['playing'] += 1

    for server in Server.select().where((Server.mode == ServerType.SERVER_MATCH)
            & Server.active == True):
        if Match.select().where((Match.server == server) &
                (Match.state != MatchState.MATCH_STATE_FINISH)):
            data['current']['servers']['used'] += 1
            data['current']['matches'] += 1

    data['current']['servers']['free'] = (Server.select().where(
        (Server.mode == ServerType.SERVER_MATCH) &
        Server.active == True).count()) - data['current']['servers']['used']

    redis.set("stats_cache", json.dumps(data))
    redis.publish("global", json.dumps({"type": "stats", "data": data}))


def get_base_match_stats():
    return {
        # Duration in seconds
        "duration": 0,

        # Rounds played
        "rounds": 0,

        # "teama" or "teamb" or None (tie)
        "winner": None,

        # Team stats
        "teama": {
            "players": {},
            "score": 0
        },

        "teamb": {
            "players": {},
            "score": 0
        },

        # The rank and impulse from this match
        "rank": [0, 0],

        # Data on rounds
        "rounds": []
    }

def get_base_player_stats():
    return {
        "kills": 0,
        "deaths": 0,
        "assists": 0,
        "score": 0,
        "shots": {
            "fired": 0,
            "missed": 0,
            "hit": 0,
        },

        # Hit locations
        "hits": {
            "body": 0,
            "head": 0,
            "chest": 0,
            "stomach": 0,
            "left_arm": 0,
            "right_arm": 0,
            "left_leg": 0,
            "right_leg": 0,
        }
    }

def get_base_round_stats():
    return {
        # Teama or Teamb
        "winner": None,

        # Method for the round being won
        "method": None,
    }

@schedule(minutes=1)
def task_match_consumer():
    """
    Builds some stuff async after matches finish
    """

    matches = Match.select().where((Match.result['parsed'] == False) & (
        Match.state == MatchState.MATCH_STATE_FINISH))

    for match in matches:
        f = STORAGE.getFile(match.result['files']['log'])
        data = json.load(f)

        match.result['stats'] = get_base_match_stats()

        for event in data:
            pass

        # TODO: fill in json stats
        # TODO: also make a chat log

class MatchFinder(object):
    SIZE = 2

    def get_shared(self, *args):
        """
        Returns a set of shared items between an infinite (?) amount of lists.
        """
        return reduce(lambda x, y: x & y, map(set, args))

    def all_comb(self, obj):
        """
        Returns all the possible combinations for an infinite amount of lists
        of items.
        """
        for index in xrange(1, len(obj)+1):
            for comb in itertools.combinations(obj, index):
                if comb:
                    yield comb

    def get_teams(self, lobbies):
        """
        Attempts to match to teams based on a set amount of lobbies
        """
        for comb in self.all_comb(lobbies):
            teama, teamb = [], []
            for lobby in comb:
                if map(lambda i: len(i.members), teama) < (self.SIZE / 2):
                    teama.append(lobby)
                else:
                    teamb.append(lobby)

            if not len(teama) or not len(teamb):
                continue

            skilla = map(lambda i: i.getSkill(), teama)
            skillb = map(lambda i: i.getSkill(), teama)

            if abs(skilla - skillb) > 5:
                continue
            return teama, teamb
        return None, None

    def find_match(self, l):
        valid_lobbies = []
        possible_matches = []

        # Get a set of possible lobbies based on map and region selection
        for item in Lobby.select().where(
                (Lobby.state == LobbyState.LOBBY_STATE_SEARCH)).order_by(Lobby.created):
            # Already has a match
            if Match.select().where((Match.lobbies.contains(item.id)) & (
                    MatchState.getValidStateQuery())).count():
                continue

            # No maps shared, why bother!
            if not self.get_shared(l.config['maps'], item.config['maps']):
                print "Could not find shared maps between %s and %s" % (l.id, item.id)
                break

            # TODO: We don't have a concept of regions yet, add this in when we do
            # if l.region != item.region:
            #     print "Region does not match between %s and %s" % (l.id, item.id)
            #     break
            valid_lobbies.append(item)

        if not len(valid_lobbies):
            print "No valid lobbies found for %s" % l.id
            return None, None

        # Generate ALL possible matches
        for comb in self.all_comb(valid_lobbies):
            # Limit those by valid lobby sizes
            if sum([len(i.members) for i in comb]) == self.SIZE:
                possible_matches.append(comb)

        # If we don't have any break out
        if not len(possible_matches):
            print "No possible matches found for %s" % l.id
            return None, None

        # Sort the list by queued time, results in older first
        possible_matches.sort(key=lambda i: min([x.queuedat for x in i]))
        for match in possible_matches:
            print "  Attempting to match..."
            # We'll have a hodge podge of maps in this result, limit matches
            #  that do not actually share maps together
            maps = self.get_shared(*[lob.config['maps'] for lob in match])
            if not maps:
                print "  No shared maps for match"
                continue

            # Check for blocked users, this could be a postgres query someday
            players, blocked = [], []
            for lobby in match:
                for player in lobby.members:
                    u = User.get(User.id == player)
                    players.append(u)
                    [blocked.append(i) for i in u.blocked]

            if len(set(blocked) & set(map(lambda i: i.id, players))):
                print "  Users have blocked eachother, this match will not work!"
                continue

            # Attempt to build two teams that are decently even
            a_team, b_team = self.get_teams(match)
            if not a_team or not b_team:
                print "  Could not get_teams on %s" % (match,)
                continue

            return maps, (a_team, b_team)

        print "No matches found for %s" % l.id
        return None, None

    def matchmake(self, data):
        try:
            lobby = Lobby.select().where(Lobby.id == data['id']).get()
        except Lobby.DoesNotExist: return

        if lobby.state != LobbyState.LOBBY_STATE_SEARCH: return

        maps, teams = self.find_match(lobby)
        if not teams:
            return

        servers = Server.getFreeServer()
        if not len(servers):
            lobby.sendAction({
                "msg": "A match was found but there are no free servers!",
                "cls": "warning"
            })
            print "No free server found!"
            return

        m = Match()
        m.lobbies = map(lambda i: i.id, teams[0]+teams[1])
        m.teama = map(lambda i: i.id, teams[0])
        m.teamb = map(lambda i: i.id, teams[1])
        m.config = {}
        m.server = servers[0]
        m.state = MatchState.MATCH_STATE_PRE
        m.size = self.SIZE
        m.mapp = Map.get(Map.id == random.choice(list(maps)))
        m.save()
        m.cleanup()

        for lobby in (teams[0]+teams[1]):
            lobby.sendAction({"type": "match"})

        # If not everyone accepts we send this out
        thread.start_new_thread(self.matchtimer, (m, ))

    def matchtimer(self, match):
        time.sleep(11.5)
        for lobby in match.getLobbies():
            if lobby.state == LobbyState.LOBBY_STATE_SEARCH:
                lobby.sendAction({"type": "endmatch"})
        match.state = MatchState.MATCH_STATE_INVALID
        match.save()

    def loop(self):
        ps = redis.pubsub()
        ps.subscribe("lobby-queue")

        for item in ps.listen():
            if item['type'] == "message":
                data = json.loads(item['data'])
                if data['tag'] == "match":
                    self.matchmake(data)

FINDER = MatchFinder()

def schedule(**kwargs):
    def deco(f):
        schedules[f.__name__] = (datetime.utcnow(), relativedelta(**kwargs), f)
        return f
    return deco

def run():
    thread.start_new_thread(FINDER.loop, ())
    # Run once on startup
    # thread.start_new_thread(task_load_workshop_maps, ())
    while True:
        time.sleep(1)
        for name, timeframe in schedules.items():
            last, gen, task = timeframe
            if datetime.utcnow() > last+gen:
                print "Running task %s" % name
                thread.start_new_thread(task, ())
                schedules[name] = (datetime.utcnow(), gen, task)

if __name__ == "__main__":
    run()
