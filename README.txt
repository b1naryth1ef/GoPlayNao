Client
Lobby: represents a group of players looking for a game, either open or
 private. Lobbyid's stay active for 1 month, and then are GC'd/expired.

Match: represents a present or past match which includes data on the server,
 players, and stats within. Matchid's never expire

Player: represents a user in the system. One per steamid.

/api/info returns information about the api, incl. version and status and username
/api/stats gets global stats information

/api/bans/list - list of all bans by steamid. PUBLIC!
/api/bans/get - get more detailed information about a ban for a steamid, reason, duration, and punisher, PUBLIC!
/api/bans/ping - log a attempted connection for a banned user by steamid SERVER!
/api/bans/add - add a ban for a steamid PRIVATE!
/api/bans/rmv - remove a ban for a steamid PRIVATE!

/api/client/poll - js polling API
/api/client/info - returns information about the current user

/api/lobbies/list - list lobbies relevant to player (open/shared)
/api/lobbies/get - get detailed information on a lobby, needs lobbyid
/api/lobbies/create - create a new lobby, returns a lobbyid
/api/lobbies/poll - js polling API for a lobby
/api/lobbies/action - fire an action on this lobby, kicks, edits, configs /etc

/api/matches/list - list matches relevant to player
/api/matches/get - get detailed information on match, needs matchid
/api/matches/stats - get stats on the match (detailed)

/api/players/get - get information on a specific player, given playerid
/api/players/search - search for a player in the system, multi-param
/api/players/friend - add a friend given playerid
/api/players/stats - get specific stats on a player
/api/players/invite - invite a player to a lobby
/api/players/cooldown - Cooldown a player SERVER! (this should fire a ringer request)

SERVER
/api/matches/start - starts a match given matchid SERVER!
/api/matches/heartbeat - keeps a match alive given matchid SERVER!
/api/matches/end - ends an ongoing match SERVER!
/api/matches/config - gets a server configuration from a matchid SERVER!
/api/servers/poll - polls for a match to load SERVER!
/api/servers/register - register this server with the master, returns serverid, sessionid SERVER!
/api/servers/list - list active servers PRIVATE!


SERVER WORKFLOW:
server send /api/servers/register with serverid and serverhash, if these match
 within the database, backend creates a "server session" w/ the source IP
 locked. Server uses sessionid on rest of requests to backend.
