from flask import Flask, g, session, request
from flask.ext.openid import OpenID
from steam import getSteamAPI

from views.public import public
from views.api import api
from database import User, redis, Session, Lobby
from util import flashy, limit

from worker import run

import sys, os, time, thread

app = Flask(__name__)
oid = OpenID(app)
steam = getSteamAPI()
app.secret_key = "change_me"

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

if __name__ == "__main__":
    app.run(debug=True)