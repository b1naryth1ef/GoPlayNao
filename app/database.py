from peewee import *
from playhouse.postgres_ext import *
from datetime import *
from dateutil.relativedelta import relativedelta
from flask import request
from steam import getSteamAPI
from util import human_readable
import bcrypt, json, redis, random, string, time

db = PostgresqlExtDatabase('ns2pug', user="b1n", password="b1n", threadlocals=True)
redis = redis.Redis()
steam = getSteamAPI()

attrs = ['years', 'months', 'days', 'hours', 'minutes', 'seconds']

SESSION_ID_SIZE = 32
get_random_number = lambda size: ''.join([random.choice(string.ascii_letters + string.digits)
    for i in range(size)])

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

    ips = ArrayField(CharField, default=[])
    blocked = ArrayField(CharField, default=[])

    # Permissions
    level = IntegerField(default=0)
    # Gameplay
    rank = IntegerField(default=0)

    def isBanned(self):
        return Ban.getActiveBanQuery((Ban.user == self.id) | (Ban.steamid == self.steamid)).count()

    def isOnline(self):
        value = redis.get("user:%s:ping" % self.id) or 0
        if (time.time() - float(value)) < 30:
            return True
        return False

    @classmethod
    def steamGetOrCreate(cls, id):
        # We do not allow players with an "active" VAC ban on record to play
        ban = steam.getBanInfo(id)
        if ban is not None and ban < 365:
            raise Exception("User has VAC ban that is newer than a year!")

        try:
            u = User.get(User.steamid == str(id))
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
        if request.remote_addr not in self.ips:
            self.ips.append(request.remote_addr)
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

    def getFriendsWithQuery(self, user):
        return Friendship.select().where(
            (((Friendship.usera == user) & (Friendship.userb == self)) |
            ((Friendship.usera == self) & (Friendship.userb == user)))
            & Friendship.active == True)

    def getFriendsQuery(self):
        return Friendship.select().where(((Friendship.usera == self) | (Friendship.userb == self))
            & (Friendship.active == True))

    def isFriendsWith(self, user):
        return bool(self.getFriendsWithQuery(user).count())

    def friendRequest(self, user):
        i = Invite()
        i.from_user = self
        i.to_user = user
        i.invitetype = InviteType.INVITE_TYPE_FRIEND
        i.save()
        i.notify()

    def getStats(self):
        DAY = (60 * 60 * 24)
        a, b = [], []
        for i, day in enumerate(xrange(0, 30)):
            a.append([(time.time() - (DAY * day)) * 1000, random.randint(1, 10)])
            b.append([(time.time() - (DAY * day)) * 1000, random.randint(1, 5)])

        return {"skill": a, "kd": b}

    def push(self, data):
        redis.publish("user:%s:push" % self.id, json.dumps(data))

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

    @classmethod
    def getActiveBanQuery(cls, ref):
        return Ban.select().where((Ban.active == True) & (Ban.end < datetime.utcnow()) & ref)

    def format(self):
        return {
            "id": self.id,
            "user": self.user.format(),
            "steamid": self.steamid,
            "created": int(self.start.strftime("%s")),
            "start": int(self.start.strftime("%s")) if self.start else "",
            "end": int(self.end.strftime("%s")) if self.end else "",
            "reason": self.reason,
            "source": self.source,
            "duration": human_readable(self.end-self.start)
                if self.end and self.start else "forever"
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
    SERVER_MATCH = 1
    SERVER_DEV = 2
    SERVER_PRIV = 3
    SERVER_OTHER = 4

class ServerRegion():
    REGION_NA = 0
    REGION_NA_IL = 1

class Server(BaseModel):
    name = CharField()
    region = IntegerField(default=ServerRegion.REGION_NA)
    hash = CharField()
    hosts = ArrayField(CharField)

    lastping = DateTimeField(default=datetime.utcnow)

    mode = IntegerField(default=ServerType.SERVER_MATCH)

    owner = ForeignKeyField(User)
    active = BooleanField()

    @classmethod
    def getFreeServer(cls):
        free = []
        for server in Server.select().where((Server.mode == ServerType.SERVER_MATCH) &
                (Server.active == True)):
            if Match.select().where((Match.server == server) &
                    (Match.state != MatchState.MATCH_STATE_FINISH)).count():
                continue
            free.append(server)
        return free

    def setup(self, match):
        map_name = Map.get(Map.id == match.config['map']).name
        redis.publish("server:%s" % self.id, json.dumps({
            "pid": 2,
            "match": match.id,
            "map": map_name,
            "players": "|".join(map(lambda i: convert_steamid(i.steamid), match.getPlayers()))
        }))

    def findWaitingMatch(self):
        return Match.get((Match.server == self) & state == MatchState.MATCH_STATE_PRE)

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
    private = BooleanField(default=True)
    state = IntegerField(default=LobbyState.LOBBY_STATE_CREATE)
    created = DateTimeField(default=datetime.utcnow)
    queuedat = DateTimeField(default=datetime.utcnow)
    members = ArrayField(IntegerField, 5)
    config = JSONField()

    @classmethod
    def getNew(cls, user, maps=[]):
        self = cls()
        self.owner = user
        self.invited = []

        # Default Config
        self.config = {
            "type": "ranked",
            "region": 0,
            "ringer": False
        }
        self.setMaps(maps)
        self.save()
        self.cleanup()
        self.joinLobby(user)
        return self

    def getMatch(self):
        try:
            return Match.get(Match.lobbies.contains(self.id) &
                        (Match.state == MatchState.MATCH_STATE_PRE) &
                        (Match.mtype == MatchType.MATCH_TYPE_LOBBY))
        except Match.DoesNotExist:
            return None

    def setMaps(self, maps=[]):
        maps = [Map.get(Map.name == i).id for i in maps]
        self.config['maps'] = maps or [i.id for i in
            Map.select().where(Map.level == self.owner.level)]

    def canJoin(self, user):
        if self.owner == user:
            return True

        if str(user.id) in self.members:
            return True

        for i in Invite.select().where((Invite.ref == self.id) & (Invite.to_user == user)):
            if i.valid():
                return True

        return False

    def format(self, tiny=True):
        base = {
            "id": self.id,
            "state": self.state,
            "members": [User.get(User.id == i).format() for i in self.members],
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
        action['lobby'] = self.id
        for user in self.members:
            redis.publish("user:%s:push" % user, json.dumps(action))

    def startQueue(self):
        if self.state == LobbyState.LOBBY_STATE_SEARCH: return
        self.state = LobbyState.LOBBY_STATE_SEARCH
        self.queuedat = datetime.utcnow()
        self.save()
        self.sendAction({
            "type": "state",
            "state": self.state,
            "msg": "Queue started"
        })
        redis.publish("lobby-queue", json.dumps({
            "tag": "match",
            "id": self.id
        }))

    def stopQueue(self):
        if self.state == LobbyState.LOBBY_STATE_IDLE: return
        self.state = LobbyState.LOBBY_STATE_IDLE
        self.save()
        self.sendAction({
            "type": "state",
            "state": self.state,
            "msg": "Queue stopped"
        })
        # TODO: handle this state within workers

    def cleanup(self):
        for key in redis.keys("lobby:%s:*" % self.id):
            redis.delete(key)

    def joinLobby(self, u):
        self.members.append(u.id)
        self.sendAction({
            "type": "join",
            "member": u.format(),
            "msg": "%s joined the lobby" % u.username
        })
        redis.set("user:%s:lobby:%s:ping" % (u.id, self.id), time.time())

    def userLeave(self, u, msg="%s has left the lobby"):
        self.sendAction({
            "type": "quit",
            "member": u.id,
            "msg": msg % u.username
        })

        self.members.remove(u.id)
        if self.state == LobbyState.LOBBY_STATE_SEARCH:
            self.stopQueue()

    def kickUser(self, u):
        self.userLeave(u, msg="%s was kicked from the lobby")
        for i in Invite.select().where((Invite.ref == self.id) & (Invite.to_user == u)):
            if i.valid():
                i.state = InviteState.INVITE_EXPIRED
                i.save()

    def getSkillDifference(self, other):
        """
        TODO: get a avg skill diff for two lobbies
        """
        return 0

    def delete(self):
        """
        TODO: kick users and gc this
        """
        return None

class InviteType(object):
    INVITE_TYPE_LOBBY = 1
    INVITE_TYPE_RINGER = 2
    INVITE_TYPE_FRIEND = 3
    INVITE_TYPE_TEAM = 4  # Hint of future plans

class InviteState(object):
    INVITE_WAITING = 1
    INVITE_EXPIRED = 2
    INVITE_ACCEPTED = 3
    INVITE_DENIED = 4

class Invite(BaseModel):
    state = IntegerField(default=InviteState.INVITE_WAITING)
    from_user = ForeignKeyField(User, related_name="invites_from")
    to_user = ForeignKeyField(User, related_name="invites_to")
    invitetype = IntegerField()
    ref = IntegerField(null=True)
    created = DateTimeField(default=datetime.utcnow)
    duration = IntegerField(default=0)
    expiresat = DateTimeField(null=True)

    def valid(self):
        if self.duration:
            if (self.created + relativedelta(seconds=self.duration)) < datetime.utcnow():
                return False
        if self.expiresat:
            if self.expiresat < datetime.utcnow():
                return False
        if self.state != InviteState.INVITE_WAITING:
            return False
        return True

    @classmethod
    def getQuery(cls, a, b):
        return (((Invite.from_user == a) & (Invite.to_user == b)) |
            ((Invite.from_user == b) & (Invite.to_user == a)))

    def getMsg(self):
        if self.invitetype == InviteType.INVITE_TYPE_LOBBY:
            return "%s has invited you to a lobby!" % (self.from_user.username)
        elif self.invitetype == InviteType.INVITE_TYPE_FRIEND:
            return "%s has invited you to be their friend!" % (self.from_user.username)
        return ""

    def getUrl(self):
        if self.invitetype == InviteType.INVITE_TYPE_LOBBY:
            return "/lobby/%s" % self.ref
        elif self.invitetype == InviteType.INVITE_TYPE_FRIEND:
            return "/friends"
        return ""

    @classmethod
    def createLobbyInvite(cls, fromu, tou, lobby):
        self = cls()
        self.from_user = fromu
        self.to_user = tou
        self.invitetype = InviteType.INVITE_TYPE_LOBBY
        self.ref = lobby.id
        self.save()
        return self

    def notify(self):
        self.to_user.push({
            "type": "invite",
            "data": {
                "msg": self.getMsg(),
                "url": self.getUrl()
            }
        })

    def format(self):
        return {
            "id": self.id,
            "from": self.from_user.format(),
            "to": self.to_user.format(),
            "type": self.invitetype,
            "ref": self.ref,
        }

class Friendship(BaseModel):
    usera = ForeignKeyField(User, related_name="friendshipa")
    userb = ForeignKeyField(User, related_name="friendshipb")
    active = BooleanField(default=True)

    @classmethod
    def create(cls, a, b, invite=None):
        self = cls()
        self.usera = a
        self.userb = b
        self.save()
        return self

    def format(self):
        return {
            "usera": self.usera.format(),
            "userb": self.userb.format(),
            "active": self.active,
        }

    def getNot(self, u):
        return self.usera if self.usera != u else self.userb

class MapType(BaseModel):
    MAP_TYPE_BOMB = 1
    MAP_TYPE_HOSTAGE = 2

class Map(BaseModel):
    title = CharField()
    name = CharField()
    image = CharField()

    custom = BooleanField(default=False)
    level = IntegerField(default=0)
    mtype = IntegerField()

    def cache_image(self):
        pass

    def format(self):
        return {
            "title": self.title,
            "name": self.name,
            "id": self.id,
            "custom": self.custom
        }

class Session(object):
    db = redis

    LIFETIME = (60 * 60 * 24) * 14  # 14 days

    @classmethod
    def create(cls, user, source_ip):
        while True:
            id = get_random_number(SESSION_ID_SIZE)
            if not cls.db.exists("us:%s" % id):
                break

        cls.db.set("us:%s" % id, json.dumps(
            {
                "user": user.id,
                "time": time.time(),
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

class MatchType(object):
    MATCH_TYPE_LOBBY = 1

class MatchState(object):
    # Accepting
    MATCH_STATE_PRE = 1
    # Waiting for joins
    MATCH_STATE_SETUP = 2
    # Playing
    MATCH_STATE_PLAY = 3
    # It's over m8
    MATCH_STATE_FINISH = 4
    # LOL WAT
    MATCH_STATE_OTHER = 5

class Match(BaseModel):
    lobbies = ArrayField(IntegerField)
    config = JSONField()
    server = ForeignKeyField(Server)
    mtype = IntegerField(default=MatchType.MATCH_TYPE_LOBBY)
    state = IntegerField(default=MatchState.MATCH_STATE_PRE)
    size = IntegerField(default=10)
    created = DateTimeField(default=datetime.utcnow)

    def getLobbies(self):
        for lob in self.lobbies:
            yield Lobby.get(Lobby.id == lob)

    def cleanup(self):
        redis.delete("match:%s:accepted" % self.id)

    def getAccepted(self):
        return redis.smembers("match:%s:accepted" % self.id)

    def accept(self, u):
        redis.sadd("match:%s:accepted" % self.id, u.id)

    def getPlayers(self):
        for lobby in self.getLobbies():
            for player in lobby.members:
                yield User.get(User.id == player)

    def setDefaultConfig(self):
        self.config = {
            "map": "de_nuke"
        }

    def format(self, forServer=False):
        data = {
            "players": [i.steamid for i in self.getPlayers()],
            "mtype": self.mtype,
            "state": self.state,
            "id": self.id
        }
        if forServer:
            data['players'] = ','.join(data['players'])

        data.update(self.config)
        return data

def load_default_maps():
    print "Loading default maps..."
    with open("content/maps.json", "r") as f:
        data = json.load(f)
    for item in data:
        m = Map()
        m.title = item['title']
        m.name = item['name']
        m.image = item['image']
        m.mtype = item['mtype']
        m.save()
        print "  Loaded map %s, %s" % (m.title, m.id)

if __name__ == "__main__":
    for table in [User, Server, Ban, BanLog, Lobby, Invite, Friendship, Map, Match]:
        table.drop_table(True, cascade=True)
        table.create_table(True)

    load_default_maps()

    u = User()
    u.username = "test"
    u.steamid = 1337
    u.save()

    u1 = User()
    u1.username = "Yolo Swaggings"
    u1.steamid = 1333337
    u1.save()
    u1.friendRequest(u)

    b = Ban()
    b.user = u1
    b.reason = "Yolo'ing too hard!"
    b.active = True
    b.source = "MMAC"
    b.save()

    s = Server()
    s.name = "Test Server #1"
    s.region = ServerRegion.REGION_NA_IL
    s.hash = get_random_number(32)
    s.hosts = ["127.0.0.1", "localhost"]
    s.owner = u
    s.active = True
    s.save()

    print "Server: %s | %s" % (s.id, s.hash)
    print "Test User: %s" % u.id
