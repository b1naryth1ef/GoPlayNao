from peewee import *
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

    def format(self):
        return {
            "id": self.id,
            "userid": self.user.id,
            "steamid": self.steamid,
            "created": int(self.start.strftime("%s")),
            "start": int(self.start.strftime("%s")),
            "end": int(self.end.strftime("%s")),
            "reason": self.reason,
            "source": self.source
        }

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