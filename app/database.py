from peewee import *
from playhouse.postgres_ext import *
from datetime import *
from flask import request, g
from steam import getSteamAPI
import bcrypt, json, redis, random, string, time

db = PostgresqlExtDatabase('ns2pug', user="b1n", password="b1n", threadlocals=True)
redis = redis.Redis()
steam = getSteamAPI()

SESSION_ID_SIZE = 32
get_random_number = lambda size: ''.join([random.choice(string.ascii_letters + string.digits) for i in range(size)])

class BaseModel(Model):
    class Meta:
        database = db

class User(BaseModel):
    username = CharField()
    email = CharField(null=True)
    steamid = CharField(null=True)

    active = BooleanField(default=True)
    join_date = DateTimeField(default=datetime.utcnow)
    last_login = DateTimeField(default=datetime.utcnow)

    level = IntegerField(default=0)

    @classmethod
    def steamGetOrCreate(cls, id):
        try:
            u = User.select().where(User.steamid == str(id)).get()
        except User.DoesNotExist:
            data = steam.getUserInfo(id)
            u = User()
            u.username = data['personaname']
            u.steamid = id
            u.save()
        return u

    def checkPassword(self, pw):
        return bcrypt.hashpw(pw, self.password) == self.password

    def login(self):
        self.last_login = datetime.utcnow()
        self.save()
        return Session.create(self, request.remote_addr)

    def isValid(self):
        return self.active and self.level >= 0

    def canPlay(self):
        return True

    def format(self):
        return {
            "id": self.id,
            "steamid": self.steamid,
            "username": self.username
        }

class Ban(BaseModel):
    user = ForeignKeyField(User, null=True)
    steamid = IntegerField(null=True)

    created = DateTimeField(default=datetime.utcnow)
    start = DateTimeField(default=datetime.utcnow)
    end = DateTimeField(null=True)

    reason = CharField()
    active = BooleanField()

    source = CharField()

    # Match Reference
    # match = ForeignKeyField(Match, null=True)

    def format(self):
        return {
            "id": self.id,
            "userid": self.user.id,
            "steamid": self.steamid,
            "created": int(self.start.strftime("%s")),
            "start": int(self.start.strftime("%s")),
            "end": int(self.end.strftime("%s")),
            "reason": self.reason,
            "source": self.source,
            "duration": human_readable(self.end-self.start) if self.end and self.start else ""
        }

    def log(self, action=None, user=None, server=None):
        log = BanLog()
        log.action = action or BanLogType.BAN_LOG_GENERIC
        log.user = user
        log.server = server
        log.ban = self
        log.save()
        return log.id

class ServerType():
    SERVER_PUG = 1
    SERVER_DEV = 2
    SERVER_PRIV = 3
    SERVER_OTHER = 4

class Server(BaseModel):
    name = CharField()
    region = CharField()
    rcon = CharField()
    hash = CharField()
    hosts = ArrayField(CharField)

    lastping = DateTimeField()

    mode = IntegerField(default=ServerType.SERVER_PUG)

    owner = ForeignKeyField(User)
    active = BooleanField()

    def createSession(self):
        while True:
            id = get_random_number(SESSION_ID_SIZE)
            if not redis.exists("ss:%s" % id):
                break

        redis.setex("ss:%s" % id, self.id, cls.LIFETIME)
        return id

    def getActiveMatch(self): pass

class BanLogType(object):
    BAN_LOG_GENERIC = 1
    BAN_LOG_ERROR = 2
    BAN_LOG_ATTEMPT = 3
    BAN_LOG_ESCALATE = 4
    BAN_LOG_EXTEND = 5
    BAN_LOG_EXPIRE = 6
    BAN_LOG_INVALIDATE = 7

class BanLog(BaseModel):
    """
    Logs an action that happened to a ban
    """
    action = IntegerField(default=BanLogType.BAN_LOG_GENERIC)
    ban = ForeignKeyField(Ban)
    user = ForeignKeyField(User, null=True)
    server = ForeignKeyField(Server, null=True)
    created = DateTimeField(default=datetime.utcnow)

class LobbyState(object):
    LOBBY_STATE_CREATE = 1
    LOBBY_STATE_IDLE = 2
    LOBBY_STATE_SEARCH = 3
    LOBBY_STATE_PLAY = 4
    LOBBY_STATE_UNUSED = 5

class Lobby(BaseModel):
    owner = ForeignKeyField(User)
    members = ArrayField(IntegerField)
    private = BooleanField(default=True)
    state = IntegerField(default=LobbyState.LOBBY_STATE_CREATE)
    created = DateTimeField(default=datetime.utcnow)
    config = JSONField()

    def canJoin(self, user):
        if self.owner == user:
            return True

        for i in Invite.select().where(Invite.ref == self.id & Invite.to_user == user):
            if i.valid():
                return True

        return False

    @classmethod
    def getNew(cls, user):
        self = cls()
        self.owner = user
        self.members = [user.id]
        self.invited = []
        # Default Config
        self.config = json.dumps({
            "players": {"min": 6,"max": 12,},
            "maps": [
                {'name': 'ns2_summit', 'rank': 0},
                {'name': 'ns2_tram', 'rank': 0},
                {'name': 'ns2_mineshaft', 'rank': 0},
                {'name': 'ns2_docking', 'rank': 0},
                {'name': 'ns2_veil', 'rank': 0},
                {'name': 'ns2_refinery', 'rank': 0},
                {'name': 'ns2_biodome', 'rank': 0},
                {'name': 'ns2_eclipse', 'rank': 0}
            ],
            "type": "ranked",
            "duration": "short"
        })
        self.save()
        return self

    def format(self, tiny=True):
        base = {
            "id": self.id,
            "state": self.state,
            "members": [User.select().where(User.id == i).get().format() for i in self.members],
            "owner": self.owner.id
        }
        if tiny: return base
        base['config'] = self.config
        return base

    def sendChat(self, user, msg):
        self.sendAction({
            "msg": msg,
            "from": user.username,
            "id": user.id,
            "type": "chat"
        })

    def sendAction(self, action):
        redis.rpush("action:lobby:%s" % self.id, json.dumps(action))
        if redis.llen("action:lobby:%s" % self.id) > 250:
            redis.lpop("action:lobby:%s" % self.id)

    def poll(self, start):
        redis.set("lobby:ping:%s:%s" % (self.id, g.user.id), time.time())
        return map(json.loads, redis.lrange("action:lobby:%s" % self.id, start, -1))

    def startQueue(self):
        self.state = LobbyState.LOBBY_STATE_SEARCH
        self.save()
        self.sendAction({
            "type": "state",
            "state": self.state,
            "msg": "Queue started"
        })

    def stopQueue(self):
        self.state = LobbyState.LOBBY_STATE_IDLE
        self.save()
        self.sendAction({
            "type": "state",
            "state": self.state,
            "msg": "Queue stopped"
        })

    def cleanup(self):
        redis.delete("lobby:ping:%s:*" % self.id)
        redis.delete("action:lobby:%s" % self.id)

class Notification(BaseModel):
    data = JSONField()

class InviteType(object):
    INVITE_TYPE_LOBBY = 1
    INVITE_TYPE_RINGER = 2
    INVITE_TYPE_FRIEND = 3
    INVITE_TYPE_TEAM = 4 # Hint of future plans

class Invite(BaseModel):
    from_user = ForeignKeyField(User, related_name="invites_from")
    to_user = ForeignKeyField(User, related_name="invites_to")
    invitetype = IntegerField()
    ref = IntegerField()
    created = DateTimeField(default=datetime.utcnow)
    duration = IntegerField(default=0)

    def valid(self):
        if duration:
            if (self.created + relativedelta(seconds=self.duration)) < datetime.utcnow():
                return False
        return True

    @classmethod
    def createLobbyInvite(cls, fromu, tou, lobby):
        self = cls()
        self.from_user = fromu
        self.to_user = tou
        self.invitetype = InviteType.INVITE_TYPE_LOBBY
        self.ref = lobby.id
        self.save()
        return self

class Session(object):
    db = redis

    LIFETIME = (60 * 60 * 24) * 14 # 14 days

    @classmethod
    def create(cls, user, source_ip):
        while True:
            id = get_random_number(SESSION_ID_SIZE)
            if not cls.db.exists("us:%s" % id):
                break

        cls.db.set("us:%s" % id, json.dumps(
            {
                "user": user.id,
                #"time": datetime.utcnow(),
                "ip": source_ip,
            }))
        cls.db.expire("us:%s" % id, cls.LIFETIME)

        return id

    @classmethod
    def find(cls, id):
        data = cls.db.get("us:%s" % id)
        if not data:
            return None
        return json.loads(data)

    @classmethod
    def expire(cls, id):
        return cls.db.delete("us:%s" % id)

# class Notifications(object):
#     def __init__(self, entity, single=False):
#         self.key = "{}:%s".format(entity)
#         self.single = single

#     def push(self, id, msg):
#         redis.rpush(self.key % id, json.dumps(msg))

#     def get(self, id, start=0, load=True):
#         data = redis.lrange(self.key % id, start, -1)
#         if load: data = map(json.loads, data)
#         if self.single: redis.delete(self.key % id)
#         return data

# lobby_notes = Notifications("lobby")
# user_notes = Notifications("user", True)

if __name__ == "__main__":
    for table in [User, Server, Ban, BanLog, Lobby, Invite]:
        table.drop_table(True, cascade=True)
        table.create_table(True)
