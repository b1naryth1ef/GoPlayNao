#pragma semicolon 1

#include <sourcemod>
#include <sdktools>
#include <sdkhooks>
#include <socket>
#include <json>

#define VERSION "0.1"
#define MODEL "models/rxg/smokevol.mdl"
#define DURATION 18.0

new Handle:gp_host;
new Handle:gp_port;
new Handle:gp_serverid;
new Handle:gp_serverhash;

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
// The matchid
new matchid = 0;

public OnPluginStart() {
    // CVARS
    gp_host = CreateConVar("gp_host", "localhost", "The master server host");
    gp_port = CreateConVar("gp_port", "5595", "The master server port");
    gp_serverid = CreateConVar("gp_serverid", "1", "This servers ID");
    gp_serverhash = CreateConVar("gp_serverhash", "1", "This servers hash");

    // Hook events
    HookEvent("player_death", Event_PlayerDeath, EventHookMode_Post);
    HookEvent("player_connect", Event_PlayerConnect, EventHookMode_Pre);

    // Fix smoke wallhack bug, credit to mukunda for coding this
    HookEvent("smokegrenade_detonate", OnSmokeDetonated);

    OpenSocket();
}

// Opens a new socket
public OpenSocket() {
    new Handle:socket = SocketCreate(SOCKET_TCP, OnSocketError);
    decl String:host_buff[256];
    GetConVarString(gp_host, host_buff, sizeof(host_buff));
    SocketConnect(socket, OnSocketConnected, OnSocketReceive, OnSocketDisconnected, host_buff, GetConVarInt(gp_port));
}

// When the socket is opened, we send a WELCOME message to the backend to handshake
public OnSocketConnected(Handle:socket, any:arg) {
    // 64 characters, one extra for padding
    decl String:hash_buff[65];
    GetConVarString(gp_serverhash, hash_buff, sizeof(hash_buff));

    // Build new welcome packet
    new JSON:obj = json_create();
    json_set_cell(obj, "id", 0);
    json_set_cell(obj, "sid", GetConVarInt(gp_serverid));
    json_set_string(obj, "shash", hash_buff);
    json_set_cell(obj, "mid", matchid);

    decl String:encoded[1024];
    json_encode(obj, encoded, sizeof(encoded));

    SocketSend(socket, encoded);
}

// TODO: invesitage chunking size of this
public OnSocketReceive(Handle:socket, String:recv[], const dataSize, any:arg) {
    new JSON:data = json_decode(recv); 
    if(data == JSON_INVALID) { 
        LogError("JSON Decode Failed!"); 
    }

    new bool:success = false;
    if (json_get_cell(data, "bool", success) && !success) {
        return LogError("Recieved error response!");
    }
}

// TOOD: handle this situation better
public OnSocketDisconnected(Handle:socket, any:arg) {
    MatchEnd();
    CloseHandle(socket);
}

// TODO: handle this situation better
public OnSocketError(Handle:socket, const errorType, const errorNum, any:arg) {
    // 111 = conn refused, handle that gracefully
    LogError("socket error %d (errno %d)", errorType, errorNum);
    MatchEnd();
    CloseHandle(socket);
}

// Opens the math log file for reading
public MatchStart() {
    decl String:buffer[512];
    Format(buffer, sizeof(buffer), "match-log-%d.txt", matchid);
    file = OpenFile(buffer, "w");
    LogLine("STARTED!");
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

public Action:Event_PlayerConnect(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:networkid[128];
    GetEventString(event, "networkid", networkid, sizeof(networkid));

    if (!GetEventBool(event, "bot")) {
        decl String:addr[128];
        decl String:buffer[2048];
        GetEventString(event, "address", addr, sizeof(addr));
        Format(buffer, sizeof(buffer), "PlayerConnect,%d,%s,%s",
            GetEventInt(event, "userid"),
            addr,
            networkid);
        LogLine(buffer);
    }

    // if (StrContains(_clients, networkid) <= 0) {
    //     KickClient(GetEventInt(event, "userid"), "You are not part of this matchmaking session");
    // }

    return Plugin_Continue;
}

public Action:Event_PlayerDeath(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];
    decl String:weapon[64];
    GetEventString(event, "weapon", weapon, sizeof(weapon));
    Format(buffer, sizeof(buffer), "PlayerDeath,%d,%d,%d,%s,%d,%d", 
        GetEventInt(event, "userid"),
        GetEventInt(event, "attacker"),
        GetEventInt(event, "assister"),
        weapon,
        GetEventBool(event, "headshot"),
        GetEventInt(event, "penetrated"));
    LogLine(buffer);
}


// Precache the smoke bug model on map load
public OnMapStart() {
    PrecacheModel(MODEL);
}

// Smoke Bug Fix
public OnSmokeDetonated(Handle:event, const String:name[], bool:dontBroadcast) {
    new Float:pos[3];
    pos[0] = GetEventFloat( event, "x" );
    pos[1] = GetEventFloat( event, "y" );
    pos[2] = GetEventFloat( event, "z" );
    pos[2] += 40.0;
    new ent = CreateEntityByName( "prop_physics_multiplayer" );
    SetEntityModel(ent, MODEL);
    
    TeleportEntity(ent, pos, NULL_VECTOR, NULL_VECTOR);
    DispatchSpawn(ent);
    SetEntityMoveType(ent, MOVETYPE_NONE);
    AcceptEntityInput(ent, "DisableMotion");
     
    SDKHook(ent, SDKHook_ShouldCollide, OnCollision); 
    SetEdictFlags(ent, (GetEdictFlags(ent)&(~FL_EDICT_ALWAYS))|FL_EDICT_DONTSEND); // allow settransmit hooks
    
    CreateTimer(DURATION, KillVolume, EntIndexToEntRef(ent), TIMER_FLAG_NO_MAPCHANGE);
}
 
// Smoke Bug Fix
public bool:OnCollision(entity, collisiongroup, contentsmask, bool:originalResult) {
    if (collisiongroup == 13 || collisiongroup == 0) {
        return false; // grenades and bullets should not clip
    }
    
    // RIP CHICKENS
    return true;
}

// Smoke Bug Fix
public Action:KillVolume( Handle:timer, any:ref ) {
    new ent = EntRefToEntIndex(ref);
    if (ent == INVALID_ENT_REFERENCE) {
        return  Plugin_Handled;
    }

    if (IsValidEntity(ent)) { 
        AcceptEntityInput(ent, "Kill");
    }
    return Plugin_Handled;
}
