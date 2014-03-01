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
    for lobby in Lobby.select().where((Lobby.state != LobbyState.LOBBY_STATE_UNUSED) & (Lobby.state != LobbyState.LOBBY_STATE_PLAY)):
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

    for server in Server.select().where((Server.mode == ServerType.SERVER_MATCH) & Server.active == True):
        if Match.select.where((Match.server == server) &
                (Match.state != MatchState.MATCH_STATE_FINISH)):
            data['current']['servers']['used'] += 1
            data['current']['matches'] += 1

    data['current']['servers']['free'] = Server.select().where((Server.mode == ServerType.SERVER_MATCH)
        & Server.active == True).count() - data['current']['servers']['used']

    redis.set("stats_cache", json.dumps(data))
    redis.publish("global", json.dumps({"type": "stats", "data": data}))


class MatchFinder(object):
    def run(self):
        pass

    # def limit_maps(self, configs):
    #     """
    #     Takes a list of lobby configs, and returns a dictionary of map names
    #     to rankings. This filters out all maps that are not acceptable
    #     """
    #     maps, maps_lim = {}, {}

    #     map_configs = map(lambda i: i["maps"], configs)
    #     for mapli in map_configs:
    #         for m, r in mapli.items():
    #             if m in maps:
    #                 maps[m] += r
    #             else:
    #                 maps[m] = r

    #     acceptable_maps = filter(lambda a: a[1][0] == len(map_configs), maps.items())
    #     return dict(map(lambda a: (a[0], a[1][1]), acceptable_maps))

    #     return dict()

    # def choose_map(self, maps):
    #     """
    #     This function takes in a list of lobby configurations and returns
    #     a single map that is the best choice based on these. This works on
    #     a simple additivie-ranking method which takes the highest ranked match,
    #     or a random choice of the highest ranked matches.
    #     """
    #     maps = {}

    #     for cfg in configs:
    #         for mp in cfg.get("maps", []):
    #             name, rank = mp['name'], mp['rank']
    #             if name not in maps:
    #                 maps[name] = rank
    #                 continue
    #             maps[name] += rank

    #     results = sorted(maps.items(), key=lambda a: -a[1])

    #     # Check if we have multiple matches
    #     if results[0][1] != results[1][1]:
    #         return results[0][0]

    #     # We have a few canidates, choose a random one
    #     pool = []
    #     for result in results:
    #         if result[1] == results[0][1]:
    #             pool.append(result[0])
    #     return random.choice(pool)

    def get_shared(self, *args):
        """
        Returns a set of shared items between a infinite (?) amount of lists.

        TOOD: maybe this could suck less?
        """
        maps = set(args[0])
        for mmap in maps:
            for arg in args:
                if mmap not in arg:
                    maps.remove(mmap)
        return maps

    def all_comb(self, obj):
        for index in xrange(0, len(obj)):
            for comb in itertools.combinations(obj, index):
                yield comb

    def get_teams(self, lobbies, max_skill):
        for comb in self.all_comb(lobbies):
            teama, teamb = [], []
            for entry in comb:
                if len(teama) < 5:
                    teama.append(entry)
                else:
                    teamb.append(entry)

            skilla = sum(map(lambda z: z.getSkillDifference(), teama))
            skillb = sum(map(lambda z: z.getSkillDifference(), teamb))

            if abs(skilla - skillb) >= max_skill:
                return teama, teamb

        return None, None

    def find_match(self, l):
        MAX_SKILL_DIFF = 5

        valid_lobbies = []
        possible_matches = []

        # Get a set of possible lobbies based on map and region selection
        for item in Lobby.select().where((Lobby.state == LobbyState.LOBBY_STATE_SEARCH)).order_by(Lobby.created):
            if not self.get_shared(l.config['maps'], item.config['maps']):
                print "Could not find shared maps between %s and %s" % (l.id, item.id)
                break
            if l.region != item.region:
                print "Region does not match between %s and %s" % (l.id, item.id)
                break
            valid_lobbies.append(item)

        if not len(valid_lobbies):
            print "No valid lobbies found for %s" % l.id
            return None, None

        # Generate ALL possible 5v5 matches
        for comb in self.all_comb(valid_lobbies):
            # Matches have 10 players y0 dawg
            if reduce(lambda i: len(i.getMembers()), comb) == 10:
                possible_matches.append(comb)

        # If we don't have any break out
        if not len(possible_matches):
            print "No possible matches found for %s" % l.id
            return None, None

        # Sort the list by queued time, results in older first
        possible_matches.sort(key=lambda i: i.queuedat)
        for match in possible_matches:
            # We'll have a hodge podge of maps in this result, limit matches
            #  that do not actually share maps together
            maps = self.get_shared(match)
            if not maps:
                continue

            a_team, b_team = self.get_teams(match, MAX_SKILL_DIFF)
            if not a_team or not b_team:
                continue

            return maps, (a_team, b_team)

        print "No matches found for %s" % l.id
        return None, None

    def loop(self):
        ps = redis.pubsub()
        ps.subscribe("lobby-queue")

        for item in ps.listen():
            if item['type'] == "message":
                try:
                    lobby = Lobby.select().where(Lobby.id == item['data']).get()
                except Lobby.DoesNotExist: continue

                if lobby.state != LobbyState.LOBBY_STATE_SEARCH: continue

                maps, teams = self.find_match(lobby)
                if not maps:
                    continue

                for lobby in (x+y):
                    lobby.sendAction({"type": "match"})

FINDER = MatchFinder()

def schedule(**kwargs):
    def deco(f):
        schedules[f.__name__] = (datetime.utcnow(), relativedelta(**kwargs), f)
        return f
    return deco

def run():
    thread.start_new_thread(FINDER.loop, ())
    # Run once on startup
    thread.start_new_thread(task_load_workshop_maps, ())
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