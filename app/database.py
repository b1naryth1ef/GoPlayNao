from peewee import *
from playhouse.postgres_ext import *
from datetime import *
from flask import request
import bcrypt, json, redis

db = SqliteDatabase('database.db', threadlocals=True)
redis = redis.Redis()

SESSION_ID_SIZE = 32
get_random_number = lambda size: ''.join([random.choice(string.ascii_letters + string.digits) for i in range(size)])

class BaseModel(Model):
    class Meta:
        database = db

class User(BaseModel):
    username = CharField()
    email = CharField()
    password = CharField()
    steamid = CharField()

    active = BooleanField(default=True)
    join_date = DateTimeField(default=datetime.utcnow)
    last_login = DateTimeField(default=datetime.utcnow)

    level = IntegerField(default=0)

    def checkPassword(self, pw):
        return bcrypt.hashpw(pw, self.password) == self.password

    def login(self):
        self.last_login = datetime.utcnow()
        self.save()
        return Session.create(self, request.remote_addr)

    def isValid(self):
        return self.active and self.level >= 0

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
            "duration": human_readable(self.end-self.start) if self.end self.start else ""
        }

    def log(self, data, action=None, user=None, server=None):
        log = BanLog()
        log.action = action or BanLogType.BAN_LOG_GENERIC
        log.user = user
        log.server = server
        log.ban = self
        log.data = data
        log.save()
        return log.id

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
    data = HStoreField()

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
                "time": datetime.utcnow(),
                "ip": source_ip,
            }))
        cls.db.expire("us:%s" % id, cls.LIFTIME)

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

if __name__ == "__main__":
    User.create_table(True)
    Ban.create_table(True)
    BanLog.create_table(True)
    Server.create_table(True)