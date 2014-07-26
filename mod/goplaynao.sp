#pragma semicolon 1

#include <sourcemod>
#include <sdktools>
#include <sdkhooks>
#include <socket>
#include <json>
#include <cstrike>

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

    AddCommandListener(HookJoinTeam, "jointeam");
    AddCommandListener(HookSpectate, "spectate");

    // OpenSocket();
}

// Opens a new socket
public OpenSocket() {
    LogMessage("Socket opened!");
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
    // CloseSocket();
}

// TODO: derp herp and lerp
public OnPluginStop() {
    // CloseSocket();
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
    if (!IsClientConnected(client) || IsFakeClient(client) || IsSourceTV(client)) {
        return Plugin_Continue;
    }

    decl String:buffer[32];
    Format(buffer, sizeof(buffer), "%d", GetSteamAccountID(client));

    // Force the player on a team
    if (StrContains(TEAMA, buffer) <= 0) {
        LogMessage("Putting on TEAMA");
        CS_SwitchTeam(client, TEAM_TEAM);
    } else {
        LogMessage("Putting on TEAMB");
        CS_SwitchTeam(client, (TEAM_TEAM == 1 ? 2 : 1));
    }
    return Plugin_Continue;
}

public Action:HookSpectate(client, const String:command[], argc)  {
    PrintCenterText(client, "You can't join spectator!");
    return Plugin_Handled;
}

// Handles half time switching of teams
public Action:HookHalftime(Handle:event, const String:name[], bool:dontBroadcast) {
    TEAM_TEAM = 2;
    for (new client = 1; client <= MaxClients; client++) {
        if(IsClientConnected(client)) {
            SwapClient(client);
        }
    }
}

// Handles match end
// TODO: this should give some breath time maybe?
public Action:HookMatchEnd(Handle:event, const String:name[], bool:dontBroadcast) {
    ServerCommand("quit")
    return Plugin_Continue;
}

// Switches a clients team
SwapClient(client) {
    new team = GetClientTeam(client);

    if (team == CS_TEAM_CT) {
        CS_SwitchTeam(client, CS_TEAM_T);
    } else if (team == CS_TEAM_T) {
        CS_SwitchTeam(client,CS_TEAM_CT);
    }
}
