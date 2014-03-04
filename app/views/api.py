from flask import (Blueprint, request, g, jsonify, Response, send_file)
from database import *
from util import *
from PIL import Image
from StringIO import StringIO
import json, requests

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
        user: optional, if the user is logged in this is their user id

    This endpoint is limited to 60 requests per minute.
    """
    data = {
        "success": True,
        "version": 1,
        "status": 1
    }

    if g.user:
        data['user'] = g.user.id

    return jsonify(data)

@api.route("/maps")
@limit(60)
def api_maps():
    level = 0
    if g.user:
        level = g.user.level

    data = "["+', '.join(redis.zrangebyscore("maps", min=0, max=level))+"]"

    return Response(
        response=data,
        status=200,
        mimetype="application/json")


# Valid width and height combinations
VALID_SIZES = [(300, 200), (640, 360), (640, 480), (800, 600), (1280, 720), (1920, 1080)]

@api.route("/maps/image")
@limit(300)
def api_maps_image():
    """
    This endpoints returns a stock map image resized to limited user
    specification. The endpoint caches resized images, and thus is slow
    only on the first call for a size.
    """
    args, success = require(map=int, width=int, height=int)

    valid = (args.width, args.height) in VALID_SIZES
    if not success or not valid:
        return "", 400

    try:
        m = Map.get(Map.id == args.map)
    except Map.DoesNotExist:
        return "", 404

    key = "map:image:%s:%sx%s" % (args.map, args.width, args.height)
    if redis.exists(key):
        buffered = StringIO(redis.get(key))
        buffered.seek(0)
    else:
        r = requests.get(m.image)
        r.raise_for_status()

        buffered = StringIO()
        img = Image.open(StringIO(r.content))
        img = img.resize((args.width, args.height), Image.ANTIALIAS)
        img.save(buffered, 'JPEG', quality=90)
        buffered.seek(0)
        # Images are cached for 6 hours
        redis.setex(key, buffered.getvalue(), (60 * 60 * 6))

    return send_file(buffered, mimetype='image/jpeg')

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
        q = Ban.select().where(Ban.getActiveBanQuery()
                & (Ban.id > args.after)).order_by(Ban.id).limit(100)
    elif args.page:
        q = Ban.select().where(Ban.getActiveBanQuery()).order_by(
                Ban.id).paginate(args.page or 1, 100)
    else:
        data['success'] = False
        data['msg'] = "Need either page or after for /bans/list"
        return jsonify(data)

    data['bans'] = [i.format() for i in q]
    data['size'] = len(data['bans'])
    data['total'] = Ban.select().where(Ban.getActiveBanQuery()).count()

    return jsonify(data)

@api.route("/bans/get")
@limit(120)
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

    This endpoint is limited to 120 requests per minute.
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
        b = Ban.get(q & Ban.active == True).order_by(Ban.created.desc())
    except Ban.DoesNotExist:
        return jsonify({"success": False, "msg": "No ban exists for query!"})

    data = b.format()
    data['success'] = True
    return jsonify(data)

# @api.route("/bans/ping")
# def api_bans_ping():
#     """
#     Called by a server to notify the backend a banned client tried connecting.
#     This should really never happen, becuase the backend will not allow
#     banned players to join a lobby, but we want to track these events for
#     abuse in the system regardless.

#     Arguments:
#         banid: the ban id

#     Returned:
#         ref: the added banlog for debug
#     """
#     args, success = require(banid=int)

#     if not success:
#         return jsonify({
#             "success": False,
#             "msg": "You must specify a banid for /bans/ping"
#         })

#     try:
#         ban = Ban.select().where(Ban.id == args.banid).get()
#     except Ban.DoesNotExist:
#         return jsonify({"success": False, "msg": "Inavlid banid!"})

#     id = ban.log(action=BanLogType.BAN_LOG_ATTEMPT, server=g.server.id)
#     return jsonify({"success": True, "ref": id})

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
        s = Server.get(
                Server.id == sid &
                Server.hash == shash &
                Server.hosts.contains(request.remote_addr))
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
    return Response(response=redis.get("stats_cache") or "{}",
        status=200, mimetype="application/json")

@api.route("/lobby/create", methods=['POST'])
@authed()
def api_lobby_create():
    """
    Creates a lobby. In it's current state this allows no configuration
    to be passed into the backend.

    TODO: allow config to be passed

    Returns a lobby object.
    """
    config = json.loads(request.values.get("config"))

    # Delete all other lobbies this guy owns (kinda sucks, but w/e)
    for lobby in Lobby.select().where(Lobby.owner == g.user):
        lobby.delete()

    lobby = Lobby.getNew(g.user, config.get("maps", []))
    data = lobby.format()
    data['success'] = True
    return jsonify(data)

def pre_lobby(id):
    """
    Helper function for lobby-related endpoints
    """
    if id is None:
        return jsonify({
            "success": False,
            "msg": "Endpoint requires a lobby id!"
        })

    try:
        lobby = Lobby.get(Lobby.id == id)
    except Lobby.DoesNotExist:
        return jsonify({
            "success": False,
            "msg": "No lobby with that id exists!"
        })

    print lobby.members, lobby.id
    if not g.user.id in lobby.members:
        return jsonify({
            "success": False,
            "msg": "You do not have permission to that lobby!"
        })
    return lobby

@api.route("/lobby/edit", methods=['POST'])
@authed()
def api_lobby_edit():
    args, _ = require(id=int)

    lobby = pre_lobby(args.id)
    if not isinstance(lobby, Lobby):
        return lobby

    if lobby.owner != g.user:
        return jsonify({
            "success": False,
            "msg": "You do not have permission to edit that lobby!"
        })

    data = json.loads(request.values.get("config"))
    lobby.setMaps(data.get('maps', []))
    lobby.save()

    return jsonify({
        "success": True,
    })

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

    if args.action not in ['quit', 'start', 'stop', 'kick', 'accept']:
        return jsonify({
            "success": False,
            "msg": "Invalid lobby action `%s`!" % args.action
        })

    if args.action == "accept":
        m = lobby.getMatch()
        if not m:
            return jsonify({
                "success": False,
                "msg": "No match to accept!"
            })

        # TODO: match accept time check
        m.accept(g.user)
        accepted = len(m.getAccepted())

        # If we're G2G
        if accepted == m.size:
            lobby.state = LobbyState.LOBBY_STATE_PLAY
            lobby.save()
            m.state = MatchState.MATCH_STATE_SETUP
            m.server.setup(m)
            m.save()

        for lob in m.getLobbies():
            lob.sendAction({
                "type": "accept",
                "num": accepted,
                "id": m.id,
                "size": m.size
            })
        return jsonify({"success": True})

    if args.action == "quit":
        lobby.stopQueue()
        lobby.userLeave(g.user)
        return {"success": True}

    if args.action == "kick":
        try:
            u = User.get(User.id == request.values.get("user"))
        except User.DoesNotExist:
            return jsonify({
                "success": False,
                "msg": "Invalid User!"
            })

        if lobby.owner == u:
            return jsonify({
                "success": False,
                "msg": "Cannot kick yourself!"
            })

        if str(u.id) not in lobby.members:
            return jsonify({
                "success": False,
                "msg": "User not in lobby!"
            })

        lobby.kickUser(u)
        return jsonify({"success": True})

    if lobby.owner != g.user:
        return jsonify({
            "success": False,
            "msg": "You must be the lobby owner to modify the lobby!"
        })

    if args.action == "start":
        errors = []
        for member in lobby.members:
            u = User.get(User.id == member)
            if not u.canPlay():
                errors.append(u.username)

        if len(errors):
            word = "they have" if len(errors) > 1 else "has an"
            word2 = "bans" if len(errors) > 1 else "ban"
            lobby.sendAction({"type": "msg", "msg": "%s cannot queue, %s active %s!" %
                (', '.join(errors), word, word2)})
            return jsonify({"success": False, "msg": "%s users in the lobby cannot play!" %
                len(errors)})

        if len(lobby.members) > 5:
            lobby.sendAction(
                {"type": "msg", "msg": "Queue cannot be started with more than 5 players!"})
            return jsonify({
                "success": False,
                "msg": "You cannot queue with more than 5 players!"
            })

        if lobby.state in [LobbyState.LOBBY_STATE_CREATE, LobbyState.LOBBY_STATE_IDLE]:
            lobby.startQueue()
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "msg": "Lobby cannot be queued!"})

    if args.action == "stop":
        if lobby.state in [LobbyState.LOBBY_STATE_SEARCH]:
            lobby.stopQueue()
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "msg": "Lobby not queued!"})

@api.route("/lobby/invite", methods=['POST'])
@authed()
def api_lobby_invite():
    args, success = require(uid=int, lid=int)

    if not success:
        return jsonify({
            "success": False,
            "msg": "You must specify a user-id and lobby-id!"
        })

    try:
        u = User.get(User.id == args.uid)
    except User.DoesNotExist:
        return jsonfiy({
            "success": False,
            "msg": "No user with that id!"
        })

    try:
        l = Lobby.get(Lobby.id == args.lid)
    except Lobby.DoesNotExist:
        return jsonify({
            "success": False,
            "msg": "No lobby with that id!"
        })

    if not g.user.id in l.members:
        return jsonify({
            "success": False,
            "msg": "You cannot invite users to that lobby!"
        })

    if u.id in l.members:
        return jsonify({
            "success": False,
            "msg": "That user is already part of the lobby!"
        })

    q = Invite.select().where(
        (Invite.getQuery(g.user, u)) &
        (Invite.state == InviteState.INVITE_WAITING) &
        (Invite.invitetype == InviteType.INVITE_TYPE_LOBBY) &
        (Invite.ref == l.id))

    if q.count():
        return jsonify({
            "success": False,
            "msg": "You've already invited that user!"
        })

    i = Invite()
    i.from_user = g.user
    i.to_user = u
    i.invitetype = InviteType.INVITE_TYPE_LOBBY
    i.ref = l.id
    i.duration = (60 * 5)  # 5 minutes for lobby invites
    i.save()
    i.notify()

    l.sendAction({
        "type": "msg",
        "msg": "%s invited user %s to the lobby!" % (g.user.username, u.username),
        "cls": "success"
    })

    return jsonify({"success": True})

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

@api.route("/users/friend")  # methods=['POST'])
@authed()
def api_users_friend():
    args, success = require(id=int)

    if not success:
        return jsonify({
            "success": False,
            "msg": "You must give a user id to friend a user!"
        })

    if args.id == g.user.id:
        return jsonify({
            "success": False,
            "msg": "You cannot friend yourself!"
        })

    try:
        u = User.get(User.id == args.id)
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
        (Invite.getQuery(g.user, u)) &
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
        (Invite.from_user == g.user) &
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
        f = Friendship.get(Friendship.id == args.id)
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
        u = User.get(User.id == args.id)
    except User.DoesNotExist:
        return jsonify({
            "success": False,
            "msg": "User does not exist!"
        })
    return jsonify({"success": True, "stats": u.getStats()})

@api.route("/users/friends")
@authed()
def api_users_friends():
    """
    Returns friends for the current user

    Payload:
        {"online":[{} ...], "offline": [{} ...], "banned": [{} ...]}
    """
    q = g.user.getFriendsQuery()

    data = {"online": [], "offline": [], "banned": []}

    for entry in q:
        user = entry.getNot(g.user)
        if user.getActiveBans().count():
            data['banned'].append(user.format())
        elif user.isOnline():
            data['online'].append(user.format())
        else:
            data['offline'].append(entry.format())

    return jsonify({
        "success": True,
        "friends": data
    })

@api.route("/invites/accept", methods=['POST'])
@authed()
def api_invites_accept():
    args, success = require(id=int)

    if not success:
        return jsonify({
            "success": False,
            "msg": "You must give an invite ID to accept an invite!"
        })

    try:
        i = Invite.get((Invite.id == args.id) &
            (Invite.state == InviteState.INVITE_WAITING))
    except Invite.DoesNotExist:
        return jsonify({
            "success": False,
            "msg": "Invalid invite ID!"
        })

    if i.invitetype == InviteType.INVITE_TYPE_FRIEND:
        Friendship.create(g.user, i.from_user, i)
        i.state = InviteState.INVITE_ACCEPTED
        i.save()
        return jsonify({"success": True})

@api.route("/invites/deny", methods=['POST'])
@authed()
def api_invites_deny():
    args, success = require(id=int)

    if not success:
        return jsonify({
            "success": False,
            "msg": "You must give an invite ID to reject an invite!"
        })

    try:
        i = Invite.get((Invite.id == args.id) &
            (Invite.state == InviteState.INVITE_WAITING))
    except Invite.DoesNotExist:
        return jsonify({
            "success": False,
            "msg": "Invalid invite ID!"
        })

    i.state = InviteState.INVITE_DENIED
    i.save()
    return jsonify({"success": True})

@api.route("/match/info")
@authed()
def api_match_info():
    args, success = required(id=int)

    if not success:
        return jsonify({
            "success": False,
            "msg": "You must provide a match ID!"
        })

    try:
        m = Match.get((Match.id == args.id) & MatchState.getValidStateQuery())
    except Match.DoesNotExist:
        return jsonify({
            "success": False,
            "msg": "Invalid match ID!"
        })

    if g.user not in m.getPlayers():
        return jsonify({
            "success": False,
            "msg": "You do not have permission to view that match!"
        })

    return jsonify({
        "success": True,
        "match": m.format()
    })
