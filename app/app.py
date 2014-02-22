# Flask
from flask import Flask, g, session, request
from flask.ext.openid import OpenID
from flask.ext.socketio import SocketIO, emit

# Util
from steam import getSteamAPI
from database import User, redis, Session, Lobby
from util import flashy, limit

# Internal
from worker import run
from views.public import public
from views.api import api

# Global
import sys, os, time, thread, json, gevent

app = Flask(__name__)
app.secret_key = "change_me"

socketio = SocketIO(app)
oid = OpenID(app)

steam = getSteamAPI()

app.register_blueprint(public)
app.register_blueprint(api)

@app.route("/login")
@oid.loginhandler
@limit(20)
def login():
    """
    Login URL for steam openid, limited to 20 requests a minute
    """
    if g.user is not None:
        return flashy("You are already logged in!")
    return oid.try_login('http://steamcommunity.com/openid')

@app.route("/logout")
@limit(20)
def logout():
    if g.user:
        resp = flashy("You have been logged out!", "success")
        resp.set_cookie('sid', '', expires=0)
        return resp
    return flashy("You are not logged in!")

@app.route("/test/<id>")
def test(id):
    g.user = User.select().where(User.id == id).get()
    resp = flashy("Welcome back %s!" % g.user.username, "success")
    resp.set_cookie("sid", g.user.login(), expires=time.time() + Session.LIFETIME)
    return resp

@app.route("/join/<id>")
def jointest(id):
    l = Lobby.select().where(Lobby.id == id).get() 
    l.members.append(g.user.id)
    l.save()
    l.sendAction({
        "type": "join",
        "member": g.user.format()
    })
    return flashy("Yay!", "success")

@oid.after_login
def create_or_login(resp):
    match = steam.steam_id_re.search(resp.identity_url)
    g.user = User.steamGetOrCreate(match.group(1))
    resp = flashy("Welcome back %s!" % g.user.username, "success")
    resp.set_cookie("sid", g.user.login(), expires=time.time() + Session.LIFETIME)
    return resp

@app.before_request
def beforeRequest():
    g.user = None
    g.server = None

    # Normal session
    if request.cookies.get("sid"):
        s = Session.find(request.cookies.get("sid"))
        if s:
            try:
                g.user = User.select().where(User.id == s['user']).get()
            except User.DoesNotExist:
                resp = flashy("Wow! Something really went wrong. Contact support!")
                resp.set_cookie('sid', '', expires=0)
                return resp

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

def socket_loop(data):
    s, user = data
    ps = redis.pubsub()
    ps.subscribe(["global", "user:%s:push" % user.id])
    for item in ps.listen():
        if item['type'] == 'message':
            data = json.loads(item['data'])
            print "Sending %s" % data
            if 'lobby' in data:
                s.emit("lobby", data)
            else:
                s.emit('global', data)

@socketio.on('connect', namespace="/api/poll")
def socket_connect():
    """
    This has some fucking magical ass shit in it. Lets explain.

    Flask has this awesome little thing called the request context, which
    is the reason things like "request" and "g" work the way they do. Sure,
    it's a ton of magic, but it's usefull. Unless you use websockets and need
    an ongoing loop. This function HAS to exit for socketio too parse NEW
    emissions from the client, so we start a greenlet joined too the socket
    (when the socket dies, the greenlet will too AFAIK), and pass it the WS.

    This took me hours. :(
    """
    beforeRequest()
    ns = request.namespace.socket['/api/poll']
    ns.spawn(socket_loop, (request.namespace.socket['/api/poll'], g.user))

@socketio.on("ping", namespace="/api/poll")
def socket_ping(data):
    # We pull the user id ourselves to avoid excessive DB queries
    if request.cookies.get("sid"):
        s = Session.find(request.cookies.get("sid"))
        if s:
            redis.set("user:%s:ping" % s['user'], time.time())
            if 'lobby' in data:
                redis.set("user:%s:lobby:%s:ping" % (s['user'], data['lobby']), time.time())

@app.template_filter("json")
def filter_json(i):
    return json.dumps(i)

if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s',
                    filename='log.log',
                    filemode='w')
    socketio.run(app)