from flask import Blueprint, render_template, flash, redirect, request, g, session, jsonify
from database import *
from util import *
import time, json

api = Blueprint('api', __name__, url_prefix='/api')

@api.route("/info")
@limit(60)
def api_info():
    """
    Returns information regarding the API's state, version and whether the
    current requester is logged in as a user.

    Returned:
        version: The API version, this is for external services.
        status: 1 on OK, -1 on ERR, >1 on other errors (TBD)
        user: optional, if the user is logged in this is their username

    This endpoint is limited to 60 requests per minute.
    """
    data = {
        "success": True,
        "version": 1,
        "status": 1
    }

    if g.user:
        data['user'] = g.user.username

    return jsonify(data)

@api.route("/bans/list")
@limit(120)
def api_bans_list():
    """
    Returns a list of steamid's that have active bans in the system. To get
    more information about a specific ban, use /bans/get.

    Arguments:
        The after and page arguments are exclusive and cannot be mixed.
        page: The page number. Each page returns 100 steamids.
        after: A ban number to start from, can be used in combination with
            size to virtually tail the ban list.

    Returned:
        size: The number of returned steamid's
        bans: A list of banned steamids.

    This endpoint is limited to 120 requests per minute.
    """

    args, _ = require(page=int, after=int)
    data = {
        "success": True,
        "size": 0,
        "bans": []
    }

    if args.after:
        q = Ban.select().where(Ban.id > args.after).order_by(Ban.id).limit(100)
    elif args.page:
        q = Ban.select().order_by(Ban.id).paginate(args.page or 1, 100)
    else:
        data['success'] = False
        data['msg'] = "Need either page or after for /bans/list"
        return jsonify(data)

    data['bans'] = [i.format() for i in q]
    data['size'] = len(data['bans'])

    return jsonify(data)

@api.route("/bans/get")
@limit(60)
def api_bans_get():
    """
    Returns the first active ban for a steamid, banid, or userid. It's
    possible within the system for a user to have multiple active bans,
    however this call will always only return ONE ban.

    Arguments:
        All the arguments in this call are exclusive and cannot be mixed.
        steamid: A steamid to query for.
        banid: A banid to query for.
        userid: A userid to query for

    Returned:
        id: banid
        userid: userid (if any)
        steamid: steamid (if any)
        created: created date
        start: start date (if any)
        end: end date (if any, null = perma)
        reason: the ban reason (if any)
        source: the banner (if any)
        duration: human readable duration

    This endpoint is limited to 60 requests per minute.
    """
    args, _ = require(steamid=int, banid=int, userid=int)

    if not any([args.steamid, args.banid, args.userid]):
        return jsonify({
            "success": False,
            "msg": "You must specify either steamid or banid for /bans/get"
        })

    if args.steamid:
        q = (Ban.steamid == args.steamid)
    if args.banid:
        q = (Ban.id == args.banid)
    if args.userid:
        q = (Ban.user == args.userid)

    try:
        b = Ban.select().where(q & Ban.active == True).order_by(Ban.created.desc()).get()
    except Ban.DoesNotExist:
        return jsonify({"success": False, "msg": "No ban exists for query!"})

    data = b.format()
    data['success'] = True
    return jsonify(data)

@api.route("/bans/ping")
@server()
def api_bans_ping():
    """
    Called by a server to notify the backend a banned client tried connecting.
    This should really never happen, becuase the backend will not allow
    banned players to join a lobby, but we want to track these events for
    abuse in the system regardless.

    Arguments:
        banid: the ban id

    Returned:
        ref: the added banlog for debug
    """
    args, success = require(banid=int)

    if not success:
        return jsonify({
            "success": False,
            "msg": "You must specify a banid for /bans/ping"
        })

    try:
        ban = Ban.select().where(Ban.id == args.banid).get()
    except Ban.DoesNotExist:
        return jsonify({"success": False, "msg": "Inavlid banid!"})

    id = ban.log(action=BanLogType.BAN_LOG_ATTEMPT, server=g.server.id)
    return jsonify({"success": True, "ref": id})

@api.route("/servers/register")
@limit(30)
def api_servers_register():
    """
    Method to register a server session on the backend. This is similar to
    most major API methods, in that it uses cookieless auth to hit the
    backend API. The server simply registers with it's id and secret hash,
    and retrieves a sessionid (limited by IP) that it can use for most requests.

    Arguments:
        sid: server id
        shash: server hash

    Returned:
        sessionid: the sessionid created

    This endpoint is limited to 30 requests per minute to prevent DoS and 
    brute force attacks.
    """
    args, success = require(sid=int, shash=str)

    if not success:
        return jsonify({
            "success": False,
            "msg": "Registering a server requires an id and hash!"
        })

    try:
        s = Server.select().where(
            Server.id == sid &
            Server.hash == shash &
            Server.hosts.contains(request.remote_addr)).get()
        sid = s.createSession()
    except Server.DoesNotExist:
        return jsonify({
            "success": False,
            "msg": "Invalid server id or hash!"
        })

    return jsonify({
        "success": True,
        "sessionid": sid
    })

@api.route("/stats")
@limit(60)
def api_stats():
    """
    Method that returns stats on the pug infastructure including server,
    match and player stats.

    Returned:
        current:
            players:
                search: Players searching for pug
                playing: Players playing
            servers:
                open: Availbile servers
                used: Servers being used/private
            matches: current number of matches being played

    This endpoint is limited to 60 requests per minute
    """
    return jsonify({
        "current": {
            "players": {
                "searching": 123,
                "playing": 300
            },
            "servers": {
                "open": 5,
                "used": 22,
            },
            "matches": 38
        }
    })

@api.route("/lobby/create", methods=['POST'])
@authed()
def api_lobby_create():
    lobby = Lobby.getNew(g.user)
    data = lobby.format()
    data['success'] = True
    return jsonify(data)

@api.route("/lobby/poll")
@authed()
def api_lobby_poll():
    args, success = require(id=int, last=int)

    if not args.id:
        return jsonify({
            "success": False,
            "msg": "Polling lobbies requires a lobby id!"
        })

    try:
        lobby = Lobby.select().where(Lobby.id == args.id).get()
    except Lobby.DoesNotExist:
        return jsonify({
            "success": False,
            "msg": "No lobby with that id exists!"
        })

    if not g.user.id in lobby.members:
        return jsonify({
            "success": False,
            "msg": "You do not have permission to poll that lobby!"
        })

    last = args.last or 0
    data = lobby_notes.get(lobby.id, last)
    return jsonify({
        "success": True,
        "size": len(data),
        "data": data
    })

@api.route("/lobby/chat")
@authed()
def api_lobby_chat():
    args, success = require(id=int, msg=str)

    if args.id == None:
        return jsonify({
            "success": False,
            "msg": "Chatting lobbies requires a lobby id!"
        })

    try:
        lobby = Lobby.select().where(Lobby.id == args.id).get()
    except Lobby.DoesNotExist:
        return jsonify({
            "success": False,
            "msg": "No lobby with that id exists!"
        })

    if not g.user.id in lobby.members:
        return jsonify({
            "success": False,
            "msg": "You do not have permission to chat that lobby!"
        })

    lobby_notes.push(lobby.id, {
        "type": "chat",
        "from": g.user.username,
        "msg": args.msg
    })
    return jsonify({
        "success": True
    })
