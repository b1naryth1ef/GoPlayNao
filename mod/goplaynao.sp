#pragma semicolon 1

#include <sourcemod>
#include <sdktools>
#include <sdkhooks>

#define VERSION "0.1"

public Plugin:myinfo = 
{
    name = "GoPlayNao",
    author = "B1naryTh1ef",
    description = "Matchmaking Plugin for CSGO",
    version = VERSION,
    url = "github.com/b1naryth1ef/goplaynao"
}


new Handle:file = INVALID_HANDLE;
new Handle:gpn_matchid = INVALID_HANDLE;
new Handle:gpn_clients = INVALID_HANDLE;

public OnPluginStart() {
    gpn_matchid = CreateConVar("gpn_matchid", "0", "The Match ID for the current match", FCVAR_PROTECTED);
    gpn_clients = CreateConVar("gpn_clients", "", "The list of clients for the current match", FCVAR_PROTECTED);
    HookEvent("player_death", Event_PlayerDeath, EventHookMode_Post);
    HookEvent("player_connect", Event_PlayerConnect, EventHookMode_Pre);
}

public MatchStart() {
    new _matchid;
    if (gpn_matchid == INVALID_HANDLE) {
        _matchid = 0;
    } else {
        _matchid = GetConVarInt(gpn_matchid);
    }

    decl String:buffer[512];
    Format(buffer, sizeof(buffer), "match-log-%d.txt", _matchid);
    file = OpenFile(buffer, "w");
    LogLine("STARTED!");
}

public OnPluginStop() {
    FlushFile(file);
    CloseHandle(file);
}

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
    decl String:_clients[2048];
    GetEventString(event, "networkid", networkid, sizeof(networkid));
    GetConVarString(gpn_clients, _clients, sizeof(_clients));

    if (!GetEventBool(event, "bot")) {
        decl String:addr[128];
        decl String:buffer[2048];
        GetEventString(event, "address", addr, sizeof(addr));
        Format(buffer, sizeof(buffer), "PlayerConnect,%L,%s,%s",
            GetEventInt(event, "userid"),
            addr,
            networkid);
        LogLine(buffer);
    }

    if (StrContains(_clients, networkid) <= 0) {
        KickClient(GetEventInt(event, "userid"), "You are not part of this matchmaking session");
    }

    return Plugin_Continue;
}

public Action:Event_PlayerDeath(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];
    decl String:weapon[64];
    GetEventString(event, "weapon", weapon, sizeof(weapon));
    Format(buffer, sizeof(buffer), "PlayerDeath,%L,%L,%L,%s,%d,%d", 
        GetEventInt(event, "userid"),
        GetEventInt(event, "attacker"),
        GetEventInt(event, "assister"),
        weapon,
        GetEventBool(event, "headshot"),
        GetEventInt(event, "penetrated"));
    LogLine(buffer);
}
