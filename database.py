# TODO: refactor all dis
import redis
import random, string

SESSION_ID_SIZE = 32
USER_ID_SIZE = 14
get_random_id = lambda size: ''.join([random.choice(string.ascii_letters + string.digits) for i in range(size)])

REDIS_CONN = redis.Redis()

def get_redis():
    return REDIS_CONN

def create_session(user_id):
    id = get_random_id(SESSION_ID_SIZE)
    get_redis().set("s:%s" %id, user_id)
    return id

def delete_session(sess_id):
    return get_redis().delete("s:%s" % sess_id)

def get_session(sess_id):
    return get_redis().get("s:%s" % sess_id)

def get_user_id():
    r = get_redis()
    while True:
        k = get_random_id(USER_ID_SIZE)
        if not r.exists(k):
            return k

class User(object):
    kfmt = "u:%s"

    @classmethod
    def get(cls, id):
        r = get_redis()
        if r.exists(cls.kfmt % id):
            self = cls()
            self.__dict__.update(r.hgetall(cls.kfmt % id))
            return self
        return None

    @classmethod
    def create(cls, username, steamid):
        r = get_redis()
        id = get_user_id()
        r.hset(cls.kfmt % id, {
            "username": username,
            "steamid": steamid
        })


if __name__ == "__main__":
    pass