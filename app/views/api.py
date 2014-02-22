from flask import Blueprint, render_template, flash, redirect, request, g, session, jsonify
from database import *
from util import *
import time, json

api = Blueprint('api', __name__, url_prefix='/api')

#from app import sockets

#@sockets.route("/api/poll")
# @api.route("/poll")
# @authed()
# @socket()
# def api_lobby_poll_socket(ws):
#     # Loop over redis, pull in data, forward too frontend
#     print "wow..."
#     ps = redis.pubsub()
#     ps.subscribe("user:%s:push" % g.user.id)
#     for item in ps.listen():
#         if item['type'] == 'message':
#             ws.send(item['data'])
#     return

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
    """
    Creates a lobby
    """
    lobby = Lobby.getNew(g.user)
    data = lobby.format()
    data['success'] = True
    return jsonify(data)

def pre_lobby(id):
    """
    Helper function for lobby-related endpoints
    """
    if id == None:
        return jsonify({
            "success": False,
            "msg": "Endpoint requires a lobby id!"
        })

    try:
        lobby = Lobby.select().where(Lobby.id == id).get()
    except Lobby.DoesNotExist:
        return jsonify({
            "success": False,
            "msg": "No lobby with that id exists!"
        })

    if not g.user.id in lobby.members:
        return jsonify({
            "success": False,
            "msg": "You do not have permission to that lobby!"
        })
    return lobby

@api.route("/lobby/info")
@authed()
def api_lobby_info():
    args, _ = require(id=int)

    lobby = pre_lobby(args.id)
    if not isinstance(lobby, Lobby):
        return lobby

    return jsonify({
        "success": True,
        "lobby": lobby.format()
    })

@api.route("/lobby/chat", methods=['POST'])
@authed()
def api_lobby_chat():
    args, success = require(id=int, msg=str)

    if not success:
        return jsonify({
            "success": False,
            "msg": "Lobby chat expects both a lobby id and a message!"
        })

    lobby = pre_lobby(args.id)
    if not isinstance(lobby, Lobby):
        return lobby

    if not args.msg.strip():
        return jsonify({
            "succcess": False,
            "msg": "Lobby chat messages must contain something!"
        })

    lobby.sendChat(g.user, args.msg)
    return jsonify({
        "success": True
    })

@api.route("/lobby/action", methods=['POST'])
@authed()
def api_lobby_action():
    args, success = require(id=int, action=str)

    if not success:
        return jsonify({
            "success": False,
            "msg": "Lobby action expects lobby id and action!"
        })

    lobby = pre_lobby(args.id)
    if not isinstance(lobby, Lobby):
        return lobby

    if args.action not in ['leave', 'join', 'edit', 'start', 'stop']:
        return jsonify({
            "success": False,
            "msg": "Invalid lobby action `%s`!" % args.action
        })

    if args.action == "leave":
        lobby.stopQueue()
        pass

    if args.action == "join":
        lobby.stopQueue()
        pass

    if lobby.owner != g.user:
        return jsonify({
            "success": False,
            "msg": "You must be the lobby owner to modify the lobby!"
        })

    if args.action == "start":
        errors = []
        for member in lobby.members:
            u = User.select().where(User.id == member).get()
            if not u.canPlay():
                errors.append(u.username)

        if len(errors):
            word = "they have" if len(errors) > 1 else "has an"
            word2 = "bans" if len(errors) > 1 else "ban"
            lobby.sendAction({"type": "msg", "msg": "%s cannot queue, %s active %s!" % (', '.join(errors), word, word2)})
            return jsonify({"success": False, "msg": "%s users in the lobby cannot play!" % len(errors)})

        if lobby.state in [LobbyState.LOBBY_STATE_CREATE, LobbyState.LOBBY_STATE_IDLE]:
            lobby.startQueue()
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "msg": "Lobby Already Queued"})
    if args.action == "stop":
        if lobby.state in [LobbyState.LOBBY_STATE_SEARCH]:
            lobby.stopQueue()
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "msg": "Lobby Not Queued!"})

@api.route("/users/search", methods=["POST"])
@authed()
def api_users_search():
    args, success = require(query=str)

    if not success:
        return jsonify({
            "success": False,
            "msg": "You must give a query to search!"
        })

    u = User.select().where(User.username ** (args.query)).limit(25)

    return jsonify({
        "success": True,
        "results": [i.format() for i in u]
    })

@api.route("/users/friend", methods=['POST'])
@authed()
def api_users_friend():
    args, success = require(id=int)

    if not success:
        return jsonify({
            "success": False,
            "msg": "You must give a user id to friend a user!"
        })

    try:
        u = User.select().where(User.id == args.id).get()
    except User.DoesNotExist:
        return jsonify({
            "success": False,
            "msg": "No user with that id!"
        })

    if u.isFriendsWith(g.user):
        return jsonify({
            "success": False,
            "msg": "Already friends with that user!"
        })

    waiting = Invite.select().where(
        Invite.getQuery(g.user, u) &
        (Invite.state == InviteState.INVITE_WAITING))

    # If there is an invite waiting to be accepted by either party, display that
    if waiting.count():
        w = waiting.get()
        if w.from_user == g.user:
            return jsonify({
                "success": False,
                "msg": "You've already invited that user to be your friend!"
            })
        else:
            return jsonify({
                "success": False,
                "msg": "That user has already invited you to be their friend!"
            })

    denied = Invite.select().where(
        (Invite.to_user == u) &
        (Invite.from_user == g.user)
        (Invite.state == InviteState.INVITE_DENIED))

    # If WE have invited that user, and they denied, display the invite as waiting
    if denied.count():
        return jsonify({
            "success": False,
            "msg": "You've already invited that user to be your friend!"
        })

    g.user.friendRequest(u)
    return jsonify({"success": True})

@api.route("/users/unfriend", methods=['POST'])
@authed()
def api_users_unfriend():
    args, success = require(id=int)

    if not success:
        return jsonify({
            "success": False,
            "msg": "You must give a friendship id to unfriend a user!"
        })

    try:
        f = Friendship.select().where(Friendship.id == args.id).get()
    except Friendship.DoesNotExist:
        return jsonify({
            "success": False,
            "msg": "Invalid Friendship ID!"
        })

    f.delete().execute()
    return jsonify({"success": True})

@api.route("/users/stats")
@authed()
def api_users_stats():
    args, success = require(id=int)

    if not success:
        return jsonify({
            "success": False,
            "msg": "You must give a user id to view user stats!"
        })

    try:
        u = User.select().where(User.id == args.id).get()
    except User.DoesNotExist:
        return jsonify({
            "success": False,
            "msg": "User does not exist!"
        })
    return jsonify({"success": True, "stats": u.getStats()})

@api.route("/invites/accept", methods=['POST'])
@authed()
def api_invites_accept():
    args, success = require(id=int)

    if not success:
        return jsonify({
            "success": False,
            "msg": "You must give an invite id to accept an invite!"
        })

    try:
        i = Invite.select().where(Invite.id == args.id).get()
    except Invite.DoesNotExist:
        return jsonify({
            "success": False,
            "msg": "Invalid invite ID!"
        })

    if i.invitetype == InviteType.INVITE_TYPE_FRIEND:
        Friendship.create(g.user, i.to_user, i)
        i.update(state=InviteState.INVITE_ACCEPTED).where(Invite.id == id).execute()
        return jsonify({"success": True})

@api.route("/invites/deny", methods=['POST'])
@authed()
def api_invites_deny():
    args, success = require(id=int)

    if not success:
        return jsonify({
            "success": False,
            "msg": "You must give an invite id to reject an invite!"
        })

    try:
        i = Invite.select().where(Invite.id == args.id).get()
    except Invite.DoesNotExist:
        return jsonify({
            "success": False,
            "msg": "Invalid invite ID!"
        })

    i.update(state=InviteState.INVITE_DENIED).where(Invite.id == id).execute()
    return jsonify({"success": True})