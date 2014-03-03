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
new Handle:gp_serverhash;
new Handle:socket;

new MATCH_ID = -1;
new String:PLAYERS[1024];

public Plugin:myinfo = 
{
    name = "GoPlayNao",
    author = "B1naryTh1ef",
    description = "Matchmaking Plugin for CS:GO",
    version = VERSION,
    url = "github.com/b1naryth1ef/goplaynao"
}

// The logfile
new Handle:file = INVALID_HANDLE;


public OnPluginStart() {
    // CVARS
    gp_host = CreateConVar("gp_host", "localhost", "The master server host");
    gp_port = CreateConVar("gp_port", "5595", "The master server port");
    gp_serverid = CreateConVar("gp_serverid", "1", "This servers ID");
    gp_serverhash = CreateConVar("gp_serverhash", "1", "This servers hash");

    // Hook events
    // HookEvent("player_connect", Event_PlayerConnect, EventHookMode_Post);

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

    OpenSocket();
}

// Opens a new socket
public OpenSocket() {
    socket = SocketCreate(SOCKET_TCP, OnSocketError);
    decl String:host_buff[256];
    GetConVarString(gp_host, host_buff, sizeof(host_buff));
    SocketConnect(socket, OnSocketConnected, OnSocketReceive, OnSocketDisconnected, host_buff, GetConVarInt(gp_port));
}

// When the socket is opened, we send a WELCOME message to the backend to handshake
public OnSocketConnected(Handle:s, any:arg) {
    SendWelcomePacket(INVALID_HANDLE);
}

public SendWelcomePacket(Handle:timer) {
    // 64 characters, one extra for padding
    decl String:hash_buff[65];
    GetConVarString(gp_serverhash, hash_buff, sizeof(hash_buff));

    // Build new welcome packet
    new JSON:obj = json_create();
    json_set_cell(obj, "id", 0);
    json_set_cell(obj, "sid", GetConVarInt(gp_serverid));
    json_set_string(obj, "shash", hash_buff);
    json_set_cell(obj, "mid", MATCH_ID);
    json_set_cell(obj, "version", StringToInt(VERSION));

    decl String:encoded[1024];
    json_encode(obj, encoded, sizeof(encoded));

    SocketSend(socket, encoded);
}

// TODO: invesitage chunking size of this
public OnSocketReceive(Handle:s, String:recv[], const dataSize, any:arg) {
    new JSON:data = json_decode(recv); 
    if(data == JSON_INVALID) { 
        LogError("JSON Decode Failed!"); 
    }

    new bool:success = false;
    if (json_get_cell(data, "success", success) && !success) {
        decl String:error[2048];
        json_get_string(data, "msg", error, sizeof(error));
        return LogError("Recieved error response '%s'!", error);
    }

    new id = -1;
    json_get_cell(data, "pid", id);
    switch (id) {
        case 2: {
            HandlePacketTwo(data);
        }
    }

    return Plugin_Handled;
}

public HandlePacketTwo(JSON:data) {
    decl String:map_name[128];
    json_get_string(data, "map", map_name, sizeof(map_name));

    // Set the match_id
    json_get_cell(data, "match", MATCH_ID);
    LogMessage("Setting up match #%i", MATCH_ID);

    json_get_string(data, "players", PLAYERS, sizeof(PLAYERS));

    LogMessage("Changing level to %s", map_name);
    ForceChangeLevel(map_name, "New Match");
}


// TOOD: handle this situation better
public OnSocketDisconnected(Handle:s, any:arg) {
    MatchEnd();
    CloseHandle(socket);
}

// TODO: handle this situation better
public OnSocketError(Handle:s, const errorType, const errorNum, any:arg) {
    // 111 = conn refused, handle that gracefully
    LogError("socket error %d (errno %d)", errorType, errorNum);
    MatchEnd();
    CloseHandle(socket);
}

// Opens the math log file for reading
public MatchStart() {
    decl String:buffer[512];
    Format(buffer, sizeof(buffer), "match-log-%d.txt", MATCH_ID);
    file = OpenFile(buffer, "w");
    LogLine("STARTED!");
    ServerCommand("tv_record match_%d\n", MATCH_ID);
}

// Flushes and closes the logfile
public MatchEnd() {
    FlushFile(file);
    CloseHandle(file); 
}

// TODO: derp herp and lerp
public OnPluginStop() {
    MatchEnd();
}

// Logs a line to the match log
public LogLine(const String:data[]) {
    if (file == INVALID_HANDLE) {
        return;
    }

    decl String:buffer[2048];
    Format(buffer, sizeof(buffer), "%d|%s", GetTime(), data);
    WriteFileLine(file, buffer);
}

// Handles client connections
public bool:OnClientConnect(client, String:msg[], maxlen) {    
    decl String:buffer[32];
    Format(buffer, sizeof(buffer), "%d", GetSteamAccountID(client));
    if (StrContains(PLAYERS, buffer) <= 0) {
        strcopy(msg, maxlen, "You are not in this matchmaking session!");
        return false;
    }
    return true;
}

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

