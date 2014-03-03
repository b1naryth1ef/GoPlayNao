import time, random, thread, json
from steam import getSteamAPI
from database import *
from dateutil.relativedelta import relativedelta
from datetime import datetime
import itertools

schedules = {}

s = getSteamAPI()

def schedule(**kwargs):
    def deco(f):
        schedules[f.__name__] = (datetime.utcnow(), relativedelta(**kwargs), f)
        return f
    return deco

LOBBY_TIMEOUT = 15

@schedule(seconds=5)
def task_user_timeout():
    for lobby in Lobby.select().where((Lobby.state != LobbyState.LOBBY_STATE_UNUSED) &
            (Lobby.state != LobbyState.LOBBY_STATE_PLAY)):
        for member in lobby.getMembers():
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
    return
    """
    If a user times out from a lobby, time them out
    """
    for lobby in Lobby.select().where((Lobby.state != LobbyState.LOBBY_STATE_UNUSED)):
        for member in lobby.getMembers():
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
        if len(lobby.getMembers()): continue
        print "Cleaning up lobby: %s" % lobby.id
        lobby.state = LobbyState.LOBBY_STATE_UNUSED
        lobby.cleanup()
        lobby.save()

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
        data['current']['players']['searching'] += len(lobby.getMembers())
        data['current']['lobbies']['searching'] += 1

    for lobby in Lobby.select().where(Lobby.state == LobbyState.LOBBY_STATE_PLAY):
        data['current']['players']['playing'] += len(lobby.getMembers())
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


class MatchFinder(object):
    SIZE = 2

    def get_shared(self, *args):
        """
        Returns a set of shared items between a infinite (?) amount of lists.

        TOOD: maybe this could suck less?
        """
        return reduce(lambda x, y: x & y, map(set, args))

    def all_comb(self, obj):
        for index in xrange(1, len(obj)+1):
            for comb in itertools.combinations(obj, index):
                yield comb

    def get_teams(self, lobbies, max_skill):
        for comb in self.all_comb(lobbies):
            teama, teamb = [], []
            for entry in comb:
                if len(teama) < (self.SIZE / 2):
                    teama.append(entry)
                else:
                    teamb.append(entry)

            if not len(teama) or not len(teamb):
                continue

            skilla = 0  # sum(map(lambda z: z.getSkillDifference(), teama))
            skillb = 0  # sum(map(lambda z: z.getSkillDifference(), teamb))

            if abs(skilla - skillb) <= max_skill:
                return teama, teamb

        return None, None

    def find_match(self, l):
        MAX_SKILL_DIFF = 5

        valid_lobbies = []
        possible_matches = []

        # Get a set of possible lobbies based on map and region selection
        for item in Lobby.select().where(
                (Lobby.state == LobbyState.LOBBY_STATE_SEARCH)).order_by(Lobby.created):
            if not self.get_shared(l.config['maps'], item.config['maps']):
                print "Could not find shared maps between %s and %s" % (l.id, item.id)
                break
            # We don't have a concept of regions yet, add this in when we do
            # if l.region != item.region:
            #     print "Region does not match between %s and %s" % (l.id, item.id)
            #     break
            valid_lobbies.append(item)

        if not len(valid_lobbies):
            print "No valid lobbies found for %s" % l.id
            return None, None

        # Generate ALL possible 5v5 matches
        for comb in self.all_comb(valid_lobbies):
            # Matches have 10 players y0 dawg
            if not comb: continue
            if sum([len(i.getMembers()) for i in comb]) == self.SIZE:
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

            # It's possible someone has blocked someone else...
            blocks, players = [], []
            for lobby in match:
                for member in lobby.getMembers():
                    players.append(member)
                    blocks += User.select().where(User.id == member).get().blocked

            # Grab a inclusive set of blocks + players
            if len(set(blocks) & set(players)):
                print "  Users have blocked eachother, match will not work!"
                continue

            # Attempt to build two teams that are decently even
            a_team, b_team = self.get_teams(match, MAX_SKILL_DIFF)
            print a_team, b_team
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

        if not maps:
            # TODO: send msg to lobby
            print "Match found but no maps in common!"
            return

        servers = Server.getFreeServer()
        if not len(servers):
            # TODO: send msg to lobby
            print "No free server found!"
            return

        m = Match()
        m.lobbies = map(lambda i: i.id, teams[0]+teams[1])
        m.config = {"map": random.choice(list(maps))}
        m.server = servers[0]
        m.state = MatchState.MATCH_STATE_PRE
        m.size = self.SIZE
        m.save()
        m.cleanup()

        for lobby in (teams[0]+teams[1]):
            print lobby.id
            lobby.sendAction({"type": "match"})

        thread.start_new_thread(self.matchtimer, (m, ))

    def matchtimer(self, match):
        time.sleep(11)
        for lobby in match.getLobbies():
            if lobby.state == LobbyState.LOBBY_STATE_SEARCH:
                lobby.sendAction({"type": "endmatch"})

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
