import time, random, thread
from database import *
from dateutil.relativedelta import relativedelta
from datetime import datetime

schedules = {}
tasks = {}

def schedule(**kwargs):
    def deco(f):
        schedules[f.__name__] = (datetime.utcnow(), relativedelta(**kwargs), f)
        return f
    return deco

def repeat(f):
    def deco():
        while True:
            f()
    return deco

LOBBY_TIMEOUT = 15

@schedule(seconds=5)
def task_lobby_timeout():
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
                    "type": "timeout",
                    "member": u.format(),
                    "msg": "%s timedout from the lobby" % u.username
                })
                lobby.members.remove(member)
                lobby.save()

@schedule(minutes=5)
def task_lobby_cleanup():
    for lobby in Lobby.select().where(Lobby.state != LobbyState.LOBBY_STATE_UNUSED):
        if len(lobby.members): continue
        print "Cleaning up lobby: %s" % lobby.id
        lobby.state = LobbyState.LOBBY_STATE_UNUSED
        lobby.cleanup()
        lobby.save()


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

@repeat
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