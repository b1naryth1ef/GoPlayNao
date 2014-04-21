#pragma semicolon 1

#include <sourcemod>
#include <sdktools>
#include <sdkhooks>
#include <socket>
#include <json>

#define VERSION "1"

new Handle:gp_host;
new Handle:gp_port;
new Handle:gp_serverid;
new Handle:gp_players;
new Handle:gp_matchid;
new Handle:gp_teama;
new Handle:gp_teamb;
new Handle:socket;

new String:PLAYERS[1024];
new String:TEAMA[1024];
new String:TEAMB[1024];
new TEAM_TEAM = 1;

public Plugin:myinfo = 
{
    name = "GoPlayNao",
    author = "B1naryTh1ef",
    description = "Matchmaking Plugin for CS:GO",
    version = VERSION,
    url = "github.com/b1naryth1ef/goplaynao"
}

public OnPluginStart() {
    // CVARS
    gp_host = CreateConVar("gp_host", "localhost", "The master server host");
    gp_port = CreateConVar("gp_port", "5595", "The master server port");
    gp_serverid = CreateConVar("gp_serverid", "1", "This servers ID");
    gp_players = CreateConVar("gp_players", "", "Players allowed in this match");
    gp_matchid = CreateConVar("gp_matchid", "0", "The match ID");
    gp_teama = CreateConVar("gp_teama", "", "Team A");
    gp_teamb = CreateConVar("gp_teamb", "", "Team B");

    GetConVarString(gp_teama, TEAMA, sizeof(TEAMA));
    GetConVarString(gp_teamb, TEAMB, sizeof(TEAMB));
    GetConVarString(gp_players, PLAYERS, sizeof(PLAYERS));

    LogMessage("Starting GOTV Demo...");

    // Use %d instead of %s to save a buffer
    ServerCommand("tv_record match_%d\n", GetConVarInt(gp_matchid));

    // Hook events
    HookEvent("player_death", Event_PlayerDeath, EventHookMode_Post);
    HookEvent("player_hurt", Event_PlayerHurt, EventHookMode_Post);
    HookEvent("item_purchase", Event_ItemPurchase, EventHookMode_Post);
    HookEvent("bomb_beginplant", Event_BombBeginPlant, EventHookMode_Post);
    HookEvent("bomb_abortplant", Event_BombAbortPlant, EventHookMode_Post);
    HookEvent("bomb_planted", Event_BombPlanted, EventHookMode_Post);
    HookEvent("bomb_defused", Event_BombDefused, EventHookMode_Post);
    HookEvent("bomb_exploded", Event_BombExploded, EventHookMode_Post);
    HookEvent("bomb_dropped", Event_BombDropped, EventHookMode_Post);
    HookEvent("bomb_pickup", Event_BombPickup, EventHookMode_Post);
    HookEvent("announce_phase_end", HookHalftime, EventHookMode_Post);
    HookEvent("cs_win_panel_match", HookMatchEnd, EventHookMode_Post);

    AddCommandListener(HookJoinTeam, "jointeam");

    OpenSocket();
}

// Opens a new socket
public OpenSocket() {
    socket = SocketCreate(SOCKET_TCP, OnSocketError);
    decl String:host_buff[256];
    GetConVarString(gp_host, host_buff, sizeof(host_buff));
    SocketConnect(socket, OnSocketConnected, OnSocketReceive, OnSocketDisconnected, host_buff, GetConVarInt(gp_port));
}

public OnSocketConnected(Handle:s, any:arg) {}

// TODO: investigate chunking size of this
public OnSocketReceive(Handle:s, String:recv[], const dataSize, any:arg) {
    return 0;
}

// TOOD: handle this situation better
public OnSocketDisconnected(Handle:s, any:arg) {
    OpenSocket();
}

// This is generally bad, and causes matches to fail. :(
public OnSocketError(Handle:s, const errorType, const errorNum, any:arg) {
    // 111 = conn refused, handle that gracefully
    LogError("socket error %d (errno %d)", errorType, errorNum);
    MatchEnd();
    CloseSocket();
}

public CloseSocket() {
    if (socket != INVALID_HANDLE) {
        CloseHandle(socket);
    }
}

// Flushes and closes the logfile
public MatchEnd() {
    CloseSocket();
}

// TODO: derp herp and lerp
public OnPluginStop() {
    CloseSocket();
}

// This sends a log line to the socket connection for parsing
public LogLine(const String:data[]) {
    if (socket == INVALID_HANDLE) {
        return;
    }

    decl String:buffer[2048];
    Format(buffer, sizeof(buffer), "%s", data);
    SocketSend(socket, buffer);
}

// Handles client connections, prevents players not in the match from connecting
// TODO: handle admin connections smartly
public bool:OnClientConnect(client, String:msg[], maxlen) {    
    decl String:buffer[32];
    Format(buffer, sizeof(buffer), "%d", GetSteamAccountID(client));
    LogMessage("ClientID: `%s`", buffer);
    LogMessage("Clients: `%s`, %d", PLAYERS, StrContains(PLAYERS, buffer) );
    if (StrContains(PLAYERS, buffer) < 0) {
        strcopy(msg, maxlen, "You are not in this matchmaking session!");
        return false;
    }
    return true;
}

public Action:HookJoinTeam(client, const String:command[], argc) {
    if (!IsClientConnected(client) || IsFakeClient(client)) { return Plugin_Continue; }

    decl String:buffer[32];
    Format(buffer, sizeof(buffer), "%d", GetSteamAccountID(client));

    // Force the player on a team
    if (StrContains(TEAMA, buffer) <= 0) {
        CS_SwitchTeam(client, TEAM_TEAM);
    } else {
        CS_SwitchTeam(client, (TEAM_TEAM == 1 ? 2 : 1));
    }
    return Plugin_Handled;
}

// Handles half time switching of teams
public Action:HookHalftime(Handle:event, const String:name[], bool:dontBroadcast) {
    TEAM_TEAM = 2;
    for (new client = 1; client <= MaxClients; client++) {
        if(IsValidClient(client) || IsBot(client)) {
            SwapClient(client)
        }
    }
}

// Handles match end
// TODO: this should post the winner and stats (big payload) to the wrapper
public Action:HookMatchEnd(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];
    Format(buffer, sizeof(buffer), "9999")
    LogLine(buffer);
    return Plugin_Continue;
}

// Switches a clients team
SwapClient(client) {
    new team = GetClientTeam(client);

    if(team == CS_TEAM_CT) {
        CS_SwitchTeam(client,CS_TEAM_T);
        SetEntityModel(client,modelT[GetRandomInt(0,3)]);
    } else if(team == CS_TEAM_T) {
        CS_SwitchTeam(client,CS_TEAM_CT);
        SetEntityModel(client,modelCT[GetRandomInt(0,3)]);
    }
}

// -- SOCKET LOGGERS --

public Action:Event_PlayerConnect(Handle:event, const String:name[], bool:dontBroadcast) {
    // Log the player connect message
    decl String:networkid[128];
    decl String:addr[128];
    decl String:buffer[2048];
    GetEventString(event, "networkid", networkid, sizeof(networkid));
    GetEventString(event, "address", addr, sizeof(addr));
    Format(buffer, sizeof(buffer), "0,%d,%s,%s",
        GetEventInt(event, "userid"),
        addr,
        networkid);
    LogLine(buffer);
    return Plugin_Continue;
}

// -- Begin game log code --
public Action:Event_PlayerDeath(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];
    decl String:weapon[64];
    GetEventString(event, "weapon", weapon, sizeof(weapon));
    Format(buffer, sizeof(buffer), "1,%d,%d,%d,%s,%d,%d", 
        GetEventInt(event, "userid"),
        GetEventInt(event, "attacker"),
        GetEventInt(event, "assister"),
        weapon,
        GetEventBool(event, "headshot"),
        GetEventInt(event, "penetrated"));
    LogLine(buffer);
}

// player_hurt
public Action:Event_PlayerHurt(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];
    decl String:weapon[64];
    GetEventString(event, "weapon", weapon, sizeof(weapon));
    Format(buffer, sizeof(buffer), "2,%d,%d,%i,%i,%s,%i,%b,%b",
        GetEventInt(event, "userid"),
        GetEventInt(event, "attacker"),
        GetEventInt(event, "health"),
        GetEventInt(event, "armor"),
        weapon,
        GetEventInt(event, "dmg_health"),
        GetEventInt(event, "dmg_armor"),
        GetEventInt(event, "hitgroup"));
    LogLine(buffer);
}

// item_purchase
public Action:Event_ItemPurchase(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];
    decl String:weapon[64];
    GetEventString(event, "weapon", weapon, sizeof(weapon));
    Format(buffer, sizeof(buffer), "3,%i,%i,%s",
        GetEventInt(event, "userid"),
        GetEventInt(event, "team"),
        weapon);
    LogLine(buffer);
}

// bomb_beginplant
public Action:Event_BombBeginPlant(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];
    Format(buffer, sizeof(buffer), "4,%i,%i",
        GetEventInt(event, "userid"),
        GetEventInt(event, "site"));
    LogLine(buffer);
}

// bomb_abortplant
public Action:Event_BombAbortPlant(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];
    Format(buffer, sizeof(buffer), "5,%i,%i",
        GetEventInt(event, "userid"),
        GetEventInt(event, "site"));
    LogLine(buffer);
}

// bomb_planted
public Action:Event_BombPlanted(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];
    Format(buffer, sizeof(buffer), "6,%i,%i",
        GetEventInt(event, "userid"),
        GetEventInt(event, "site"));
    LogLine(buffer);
}

// bomb_defused
public Action:Event_BombDefused(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];
    Format(buffer, sizeof(buffer), "7,%i,%i",
        GetEventInt(event, "userid"),
        GetEventInt(event, "site"));
    LogLine(buffer);
}

// bomb_exploded
public Action:Event_BombExploded(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];
    Format(buffer, sizeof(buffer), "8,%i,%i",
        GetEventInt(event, "userid"),
        GetEventInt(event, "site"));
    LogLine(buffer);
}

// bomb_dropped
public Action:Event_BombDropped(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];
    Format(buffer, sizeof(buffer), "9,%i,%i",
        GetEventInt(event, "userid"),
        GetEventFloat(event, "entindex"));
    LogLine(buffer);
}

// bomb_pickup
public Action:Event_BombPickup(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];
    Format(buffer, sizeof(buffer), "10,%i",
        GetEventInt(event, "userid"));
    LogLine(buffer);
}

// bomb_begindefuse
public Action:Event_BombBeginDefuse(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];
    Format(buffer, sizeof(buffer), "11,%i,%b",
        GetEventInt(event, "userid"),
        GetEventBool(event, "haskit"));
    LogLine(buffer);
}

// bomb_abortdefuse
public Action:Event_BombAbortDefuse(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];
    Format(buffer, sizeof(buffer), "12,%i",
        GetEventInt(event, "userid"));
    LogLine(buffer);
}
