from klein import run, route
from util import JsonResponse, allow, APIError, params, authed
from database import create_session, get_redis

@allow("GET")
@route('/api')
def api_index(request):
    """
    Returns basic information about the API.

    version: an incrementing API version (for the public, internally we
        only support the current version #)
    status: a status integer indiciating the state of the system,
        1: OK
        2: HIGH_LOAD (limited request rate)
        3: EXTREME_LOAD (requests may end or die, system is in a bad state)
        -1: INACTIVE OR UNAVALIBILE
    """
    status = get_redis().get("status")
    return JsonResponse({
        "version": 1,
        "status": status,
    })

@allow("POST")
@route('/api/login')
@params(username=str, password=str)
def api_login(request, username, password):
    """
    Allows a user to authenticate within the system. Takes a username/password
    as post variables, returns json response and maybe a cookie session.
    """
    if username == "b1n" and password == "b1n":
        sessid = create_session(1)
        request.addCookie("session", sessid)
        return JsonResponse({
            "username": username,
            "session": sessid
        })
    return APIError("Invalid Login Credentials", 401)

@allow("POST")
@authed()
@route('/api/logout')
def api_logout(request):
    sessid = request.getCookie("session")
    if not sessid:
        return APIError("Not Logged In!", 400)
    delete_session(sessid)
    return JsonResponse({
        "msg": "You have been logged out successfully!"
    })

@route("/api/bans/list")
def api_bans_list(request):
    bans = get_redis().lrange("bans", 0, -1)
    return JsonResponse({
        "size": len(bans),
        "bans": bans
    })

@route("/api/bans/get")
@params(steamid=str)
def api_bans_get(request, steamid):
    r = get_redis()
    if r.exists("ban:%s" % steamid):
        data = r.hgetall("ban:%s" % steamid)
        data.update({
            "active": True,
            "id": steamid,
        })
        return JsonResponse(data)
    return APIError("No Such Ban", 404)

# Client
# Lobby: represents a group of players looking for a game, either open or
#  private. Lobbyid's stay active for 1 month, and then are GC'd/expired.

# Match: represents a present or past match which includes data on the server,
#  players, and stats within. Matchid's never expire

# Player: represents a user in the system. One per steamid.

# /api returns information about the api, incl. version and status

# /api/login - logs into the api
# /api/logout - logs out of the api

# /api/bans/list - list of all bans by steamid. PUBLIC!
# /api/ban/get- get more detailed information about a ban for a steamid, reason, duration, and punisher, PUBLIC!

# /api/client/poll - js polling API
# /api/client/info - returns information about the current user

# /api/lobbies/list - list lobbies relevant to player (open/shared)
# /api/lobbies/get - get detailed information on a lobby, needs lobbyid
# /api/lobbies/create - create a new lobby, returns a lobbyid
# /api/lobbies/poll - js polling API for a lobby
# /api/lobbies/action - fire an action on this lobby, kicks, edits, configs /etc

# /api/matches/list - list matches relevant to player
# /api/matches/get - get detailed information on match, needs matchid
# /api/matches/stats - get stats on the match (detailed)

# /api/players/get - get information on a specific player, given playerid
# /api/players/search - search for a player in the system, multi-param
# /api/players/friend - add a friend given playerid
# /api/players/stats - get specific stats on a player
# /api/players/invite - invite a player to a lobby

# SERVER
# /api/matches/start - starts a match given serverid and lobbyid
# /api/matches/heartbeat - keeps a match alive given serverid and lobbyid
# /api/matches/end - ends an ongoing match
# /api/lobbies/config - gets a server configuration from a lobby id
# /api/servers/poll - polls for a match to load

# PRIVATE
# /api/bans/add - add a ban for a steamid
# /api/bans/rmv - remove a ban for a steamid
# /api/servers/list - list active servers


run("localhost", 8080)