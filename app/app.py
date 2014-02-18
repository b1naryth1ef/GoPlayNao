from flask import Flask, g, session, request
from views.public import public
from views.api import api
from database import User, redis

app = Flask(__name__)
app.secret_key = "change_me"

app.register_blueprint(public)
app.register_blueprint(api)

@app.before_request
def beforeRequest():
    g.user = None
    g.server = None

    # Normal session
    if request.cookies.get("sid"):
        s = Session.find(request.cookies.get("sid"))
        if not s:
            del request.cookies['sid']
        g.user = User.select().where(User.id == s['user']).get(0)

    # Server
    if request.values.get("sid"):
        if not redis.exists("ss:%s" % request.values.get("sid")):
            return jsonify({"success": False, "error": 1, "msg": "Session Expired"})
        s = redis.get("ss:%s" % request.values.get("sid"))
        try:
            s = Server.select().where(Server.id == s).get()
        except Server.DoesNotExist:
            redis.delete("ss:%s" % request.values.get("sid"))
            return jsonify({"success": False, "error": 2, "msg": "Session Corrupted!"})
        g.server = s

if __name__ == "__main__":
    app.run(debug=True)