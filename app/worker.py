import time
from database import *
from dateutil.relativedelta import relativedelta
from datetime import datetime

tasks = {}

def schedule(**kwargs):
    def deco(f):
        tasks[f.__name__] = (datetime.utcnow(), relativedelta(**kwargs), f)
        return f
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

def schedule(**kwargs):
    def deco(f):
        tasks[f.__name__] = (datetime.utcnow(), relativedelta(**kwargs), f)
        return f
    return deco

def run():
    while True:
        time.sleep(1)
        for name, timeframe in tasks.items():
            last, gen, task = timeframe
            if datetime.utcnow() > last+gen:
                print "Running task %s" % name
                task()
                tasks[name] = (datetime.utcnow(), gen, task)

if __name__ == "__main__":
    run()