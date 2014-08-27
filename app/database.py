from peewee import *
from playhouse.postgres_ext import *
from datetime import *
from dateutil.relativedelta import relativedelta
from flask import request
from steam import SteamAPI
from util import human_readable, convert_steamid
from util.impulse import Entity

from util.badges import Badge, BADGE_BETA_TESTER

import config

import bcrypt, json, redis, random, string, time, logging


log = logging.getLogger(__name__)
db = PostgresqlExtDatabase('ns2pug', user="b1n", password="b1n", threadlocals=True, port=5433)
redis = redis.Redis()
steam = SteamAPI.new()

attrs = ['years', 'months', 'days', 'hours', 'minutes', 'seconds']

SESSION_ID_SIZE = 32
get_random_number = lambda size: ''.join([random.choice(string.ascii_letters + string.digits)
    for i in range(size)])

class BaseModel(Model):
    class Meta:
        database = db

class UserLevel(object):
    USER_LEVEL_BASE = 0
    USER_LEVEL_MOD = 90
    USER_LEVEL_ADMIN = 100

DEFAULT_ADMINS = [
    "76561198037632722"
]

class User(BaseModel, Entity):
    username = CharField()
    description = TextField(default="")
    email = CharField(null=True)
    steamid = CharField(null=True)

    active = BooleanField(default=True)
    join_date = DateTimeField(default=datetime.utcnow)
    last_login = DateTimeField(default=datetime.utcnow)

    ips = ArrayField(CharField, default=[])
    blocked = ArrayField(CharField, default=[])

    # Permissions
    level = IntegerField(default=UserLevel.USER_LEVEL_BASE)

    # Settings
    settings = JSONField(default={
        "notifications": {
            "sound": True,
            "desktop": True,
        }
    })

    # Rank and impulse
    rank = IntegerField(default=0)
    impulse = FloatField(default=0)
    stats = JSONField(default={
        "achieve": {}
    })

    # Badges
    badges = ArrayField(IntegerField, default=[])

    @classmethod
    def get_level(self, s):
        if s == "admin":
            return UserLevel.USER_LEVEL_ADMIN

    @classmethod
    def steamGetOrCreate(cls, id):
        """
        Gets or creates a user based on a steamid. Raises an exception if
        the user is banned.
        """
        # We do not allow players with an "active" VAC ban on record to play
        ban = steam.getBanInfo(id)
        if ban is not None and ban < 365:
            raise Exception("User has VAC ban that is newer than a year!")

        # During beta, only allow a set list of hardcoded steam id's
        if config.IS_BETA:
            allowed = steam.getGroupMembers("goplaymm")
            if str(id) not in allowed:
                raise Exception("This user is not authorized to join the private beta!")

        try:
            u = User.get(User.steamid == str(id))
        except User.DoesNotExist:
            data = steam.getUserInfo(id)
            u = User()
            u.username = data['personaname']
            u.steamid = id

            # Default admin level (for beta)
            if str(id) in DEFAULT_ADMINS:
                u.level = UserLevel.USER_LEVEL_ADMIN

            u.save()

        if config.IS_BETA:
            u.award_badge(BADGE_BETA_TESTER)

        return u

    def award_badge(self, badge):
        if not isinstance(badge, Badge):
            raise Exception("Value %s is not a badge!" % badge)

        if badge in self.badges:
            log.warning("Cannot award previously awarded badge %s to %s",
                badge, self.id)
            return

        self.badges.append(badge.id)
        self.save()

    def updateName(self):
        """
        Updates a username based on the users steam profile name
        """
        data = steam.getUserInfo(self.steamid)
        self.username = data['personaname']
        self.save()

    def getActiveBansQuery(self):
        return (Ban.getActiveBanQuery() &
                    ((Ban.user == self.id) | (Ban.steamid == self.steamid)))

    def getActiveBans(self):
        """
        Returns an active ban query which returns all active bans for this user,
        in order of the end date.
        """
        return Ban.select().where(self.getActiveBansQuery()).order_by(Ban.end)

    def isOnline(self):
        """
        Returns true if the user is considered online by the system.
        """
        value = redis.get("user:%s:ping" % self.id) or 0
        if (time.time() - float(value)) < 30:
            return True
        return False

    def checkPassword(self, pw):
        return bcrypt.hashpw(pw, self.password) == self.password

    def login(self):
        self.last_login = datetime.utcnow()
        if request.remote_addr not in self.ips:
            self.ips.append(request.remote_addr)
        self.save()
        return Session.create(self, request.remote_addr)

    def format(self, with_friendship=None):
        base = {
            "id": self.id,
            "steamid": self.steamid,
            "username": self.username
        }

        if with_friendship:
            base['friendship'] = {}
            base['friendship']['id'] = with_friendship.id
            base['friendship']['started'] = with_friendship.created

        return base

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

    def getFriendRequests(self):
        return Invite.select().where(
            (Invite.invitetype == InviteType.INVITE_TYPE_FRIEND) &
            (Invite.to_user == self) &
            (Invite.state == InviteState.INVITE_WAITING))

    def getStats(self):
        DAY = (60 * 60 * 24)
        a, b = [], []
        for i, day in enumerate(xrange(0, 30)):
            a.append([(time.time() - (DAY * day)) * 1000, random.randint(1, 10)])
            b.append([(time.time() - (DAY * day)) * 1000, random.randint(1, 5)])

        return {"skill": a, "kd": b}

    def push(self, data):
        redis.publish("user:%s:push" % self.id, json.dumps(data))

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
    hostname = CharField()
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
                    MatchState.getValidStateQuery()).count():
                continue
            free.append(server)
        return free

    def setup(self, match):
        map_name = match.mapp.name
        redis.publish("server-%s" % self.id, json.dumps({
            "tag": "match",
            "map": map_name,
            "id": match.id,
            "players": "|".join(map(lambda i: str(convert_steamid(i.steamid)), match.getPlayers())),
            "teama": "|".join(map(lambda i: str(convert_steamid(i.steamid)), match.getTeamA())),
            "teamb": "|".join(map(lambda i: str(convert_steamid(i.steamid)), match.getTeamB()))
        }))

    def findWaitingMatch(self):
        return Match.get((Match.server == self) & (Match.state == MatchState.MATCH_STATE_PRE))

    def format(self):
        return {
            "id": self.id,
            "region": self.region,
            "ip": self.hostsname,
        }

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
    members = ArrayField(IntegerField, 5, default=[])
    config = JSONField()

    @staticmethod
    def getNew(user, maps=[]):
        self = Lobby()
        self.owner = user

        # Default Config
        self.config = {
            "type": "ranked",
            "region": 0,
            "ringer": False
        }
        self.setMaps(maps)
        self.save()
        self.joinLobby(user)
        return self

    def getMembers(self):
        for member in self.members:
            yield User.get(User.id == member)

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

        # This is here to handle cases where users refresh the lobby page
        #  and we don't want to query the penis off of invites.
        if user.id in self.members:
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
            "owner": self.owner.id,
            "queuedat": self.queuedat
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

    def cleanup(self):
        self.stopQueue()
        self.sendAction({"type": "delete"})

    def joinLobby(self, u):
        if u.id not in self.members:
            self.members.append(u.id)
            self.save()
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

        if u.id in self.members:
            self.members.remove(u.id)
            self.save()

        if self.state == LobbyState.LOBBY_STATE_SEARCH:
            self.stopQueue()

    def kickUser(self, u):
        # Delete from members
        if u.id in self.members:
            self.members.remove(u.id)
            self.save()

        self.sendAction({
            "type": "kick",
            "member": u.id,
            "msg": "%s was kicked from the lobby" % u.username
        })
        for i in Invite.select().where((Invite.ref == self.id) & (Invite.to_user == u)):
            if i.valid():
                i.state = InviteState.INVITE_EXPIRED
                i.save()

    def getSkill(self):
        return map(lambda i: i.rank, self.getMembers()) / len(self.members)

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

    @classmethod
    def createFriendRequest(cls, usera, userb):
        i = Invite()
        i.from_user = usera
        i.to_user = userb
        i.invitetype = InviteType.INVITE_TYPE_FRIEND
        i.save()
        i.notify()
        return i

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
    created = DateTimeField(default=datetime.utcnow)
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
    MATCH_STATE_INVALID = 0
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

    @staticmethod
    def getValidStateQuery():
        return ((Match.state != MatchState.MATCH_STATE_INVALID) &
            (Match.state != MatchState.MATCH_STATE_OTHER))

class Match(BaseModel):
    lobbies = ArrayField(IntegerField)
    config = JSONField()
    server = ForeignKeyField(Server)
    mapp = ForeignKeyField(Map)
    mtype = IntegerField(default=MatchType.MATCH_TYPE_LOBBY)
    state = IntegerField(default=MatchState.MATCH_STATE_PRE)
    size = IntegerField(default=10)
    level = IntegerField(default=0)
    created = DateTimeField(default=datetime.utcnow)
    result = JSONField(default={})

    teama = ArrayField(IntegerField)
    teamb = ArrayField(IntegerField)

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

    def getTeam(self, team):
        t = self.teama if team.lower() == "a" else self.teamb
        for lobby in t:
            lobby = Lobby.get(Lobby.id == lobby)
            for player in lobby.members:
                yield User.get(User.id == player)

    def getTeamA(self): return self.getTeam("a")

    def getTeamB(self): return self.getTeam("b")

    def setDefaultConfig(self):
        self.config = {
            "map": self.mapp.name
        }

    def format(self, forServer=False):
        data = {
            "players": [i.steamid for i in self.getPlayers()],
            "state": self.state,
            "id": self.id
        }
        if forServer:
            data['players'] = ','.join(data['players'])
        else:
            data['server'] = self.server.format()

        data.update(self.config)
        return data

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
    match = ForeignKeyField(Match, null=True)

    @classmethod
    def getActiveBanQuery(cls, ref=()):
        return (Ban.active == True) & ((Ban.end >> None) | (Ban.end < datetime.utcnow()))

    def getDurationString(self):
        return human_readable(self.end-self.start) if self.end and self.start else "forever"

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
            "duration": self.getDurationString()
        }

    @classmethod
    def forUser(cls, u, reason, source):
        self = cls()
        self.user = u
        self.steamid = u.steamid
        self.reason = reason
        self.source = source
        self.active = True
        self.save()
        return self

class ReportState(object):
    REPORT_STATE_OPEN = 1
    REPORT_STATE_CLOSED = 2
    REPORT_STATE_INVALID = 3
    REPORT_STATE_VALID = 4
    REPORT_STATE_OTHER = 5

class ReportType(object):
    REPORT_TYPE_GENERIC = 1
    REPORT_TYPE_CHEAT = 2
    REPORT_TYPE_GRIEF = 3
    REPORT_TYPE_EXPLOIT = 4
    REPORT_TYPE_MALICIOUS = 5

class Report(BaseModel):
    ufrom = ForeignKeyField(User, "reports_from")
    uto = ForeignKeyField(User, "reports_to")
    ref = IntegerField()
    msg = TextField()
    state = IntegerField(default=ReportState.REPORT_STATE_OPEN)
    rtype = IntegerField(default=ReportType.REPORT_TYPE_GENERIC)
    created = DateTimeField(default=datetime.utcnow)

class Forum(BaseModel):
    title = CharField()
    perm_view = IntegerField(default=0)
    perm_post = IntegerField(default=0)
    order = IntegerField()
    parent = ForeignKeyField("self", "children", null=True)
    category = BooleanField(default=False)

    @classmethod
    def getPermQuery(cls, view):
        return (Forum.perm_view <= view)

    def format(self, as_level=0):
        data = {
            "title": self.title,
            "perms": {
                "view": self.perm_view,
                "post": self.perm_post
            },
            "order": self.order,
            "posts": ForumPost.select().where(ForumPost.forum == self).count()
        }

        if self.parent:
            data['parent'] = self.parent.id

        data['children'] = []
        for child in self.children:
            if child.perm_view > as_level: continue
            data['children'].append(child.format())
        return data

class ForumPost(BaseModel):
    author = ForeignKeyField(User)
    forum = ForeignKeyField(Forum)
    thread = ForeignKeyField("self")
    title = CharField(null=True)
    content = TextField()
    created = DateTimeField(default=datetime.utcnow)
    updated = DateTimeField(default=datetime.utcnow)

    locked = BooleanField(default=False)
    hidden = BooleanField(default=False)
    deleted = BooleanField(default=False)

    @classmethod
    def getThreadParentQuery(cls):
        return (ForumPost.thread >> None)

    @classmethod
    def getValidQuery(cls):
        return ((ForumPost.locked == False) & (ForumPost.hidden == False))

    def format(self, level):
        return {
            "author": self.author.id,
            "forum": self.forum.id,
            "thread": self.thread.id,
            "title": self.title,
            "content": self.content,
            "created": self.created,
            "updated": self.updated,
            "deleted": self.deleted
        }

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

def create_forums():
    cat1 = Forum(title="GoPlayMM", perm_view=0, perm_post=100, order=0, category=True)
    cat1.save()

    f1 = Forum(title="News & Updates", perm_view=0, perm_post=100, order=0, parent=cat1)
    f1.save()
    f2 = Forum(title="General Discussion", perm_view=0, perm_post=1, order=0, parent=cat1)
    f2.save()

TABLES = [User, Server, Ban, Lobby, Invite, Friendship, Map, Match, Report, Forum, ForumPost]

if __name__ == "__main__":
    for table in TABLES:
        table.drop_table(True, cascade=True)
        table.create_table(True)

    load_default_maps()
    create_forums()

    u = User()
    u.username = "test"
    u.steamid = 1337
    u.save()

    u1 = User()
    u1.username = "Yolo Swaggings"
    u1.steamid = 1333337
    u1.save()
    Invite.createFriendRequest(u1, u)

    b = Ban.forUser(u1, "yoloing and swagging way too hard", "b1n")

    s = Server()
    s.name = "Test Server #1"
    s.region = ServerRegion.REGION_NA_IL
    s.hash = '1'
    s.hostname = "localhost"
    s.hosts = ["127.0.0.1", "localhost"]
    s.owner = u
    s.active = True
    s.save()

    from worker import task_load_workshop_maps
    task_load_workshop_maps()

    print "Server: %s | %s" % (s.id, s.hash)
    print "Test User: %s" % u.id
