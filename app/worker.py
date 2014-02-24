import time, random, thread, json
from steam import getSteamAPI
from database import *
from dateutil.relativedelta import relativedelta
from datetime import datetime

schedules = {}
tasks = {}

s = getSteamAPI()

def schedule(**kwargs):
    def deco(f):
        schedules[f.__name__] = (datetime.utcnow(), relativedelta(**kwargs), f)
        return f
    return deco

def repeat(delay):
    def deco(f):
        def _f():
            while True:
                time.sleep(delay)
                f()
        return _f
    return deco

LOBBY_TIMEOUT = 15

@schedule(seconds=5)
def task_user_timeout():
    for lobby in Lobby.select().where((Lobby.state != LobbyState.LOBBY_STATE_UNUSED) & (Lobby.state != LobbyState.LOBBY_STATE_PLAY)):
        for member in lobby.getActiveMembers():
            u = User.select().where(User.id == member).get()
            if (time.time() - float(redis.get("user:%s:lobby:%s:ping" % (lobby.id, member)) or 0)) > 20:
                lobby.sendAction({
                    "type": "quit",
                    "member": u.format(),
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
                    "member": u.format(),
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

WORKSHOP_ID = "231287804"

@schedule(seconds=30)
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
                "searching": 120,
                "playing": 300
            },
            "servers": {
                "open": 5,
                "used": 22,
            },
            "matches": 38
        }
    }

    redis.set("stats_cache", json.dumps(data))
    redis.publish("global", json.dumps({"type": "stats", "data": data}))


class MatchFinder(object):
    def run(self):
        pass

    def limit_maps(self, configs):
        """
        Takes a list of lobby configs, and returns a dictionary of map names
        to rankings. This filters out all maps that are not acceptable
        """
        maps, maps_lim = {}, {}

        map_configs = map(lambda i: i["maps"], configs)
        for mapli in map_configs:
            for m, r in mapli.items():
                if m in maps:
                    maps[m] += r
                else:
                    maps[m] = r

        acceptable_maps = filter(lambda a: a[1][0] == len(map_configs), maps.items())
        return dict(map(lambda a: (a[0], a[1][1]), acceptable_maps))

        return dict()

    def choose_map(self, maps):
        """
        This function takes in a list of lobby configurations and returns
        a single map that is the best choice based on these. This works on
        a simple additivie-ranking method which takes the highest ranked match,
        or a random choice of the highest ranked matches.
        """
        maps = {}

        for cfg in configs:
            for mp in cfg.get("maps", []):
                name, rank = mp['name'], mp['rank']
                if name not in maps:
                    maps[name] = rank
                    continue
                maps[name] += rank

        results = sorted(maps.items(), key=lambda a: -a[1])

        # Check if we have multiple matches
        if results[0][1] != results[1][1]:
            return results[0][0]

        # We have a few canidates, choose a random one
        pool = []
        for result in results:
            if result[1] == results[0][1]:
                pool.append(result[0])
        return random.choice(pool)


FINDER = MatchFinder()

@repeat(5)
def task_find_matches():
    FINDER.run()

def schedule(**kwargs):
    def deco(f):
        schedules[f.__name__] = (datetime.utcnow(), relativedelta(**kwargs), f)
        return f
    return deco

def run():
    thread.start_new_thread(task_find_matches, ())
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