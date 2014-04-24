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

    // Hook events
    HookEvent("player_connect", Event_player_connect, EventHookMode_Post);
    HookEvent("player_disconnect", Event_player_disconnect, EventHookMode_Post);
    HookEvent("player_activate", Event_player_activate, EventHookMode_Post);
    HookEvent("player_say", Event_player_say, EventHookMode_Post);
    HookEvent("team_info", Event_team_info, EventHookMode_Post);
    HookEvent("team_score", Event_team_score, EventHookMode_Post);
    HookEvent("teamplay_broadcast_audio", Event_teamplay_broadcast_audio, EventHookMode_Post);
    HookEvent("player_team", Event_player_team, EventHookMode_Post);
    HookEvent("player_class", Event_player_class, EventHookMode_Post);
    HookEvent("player_chat", Event_player_chat, EventHookMode_Post);
    HookEvent("player_score", Event_player_score, EventHookMode_Post);
    HookEvent("player_spawn", Event_player_spawn, EventHookMode_Post);
    HookEvent("player_shoot", Event_player_shoot, EventHookMode_Post);
    HookEvent("player_use", Event_player_use, EventHookMode_Post);
    HookEvent("player_changename", Event_player_changename, EventHookMode_Post);
    HookEvent("player_hintmessage", Event_player_hintmessage, EventHookMode_Post);
    HookEvent("game_newmap", Event_game_newmap, EventHookMode_Post);
    HookEvent("game_start", Event_game_start, EventHookMode_Post);
    HookEvent("game_end", Event_game_end, EventHookMode_Post);
    HookEvent("game_message", Event_game_message, EventHookMode_Post);
    HookEvent("break_breakable", Event_break_breakable, EventHookMode_Post);
    HookEvent("break_prop", Event_break_prop, EventHookMode_Post);
    HookEvent("entity_killed", Event_entity_killed, EventHookMode_Post);
    HookEvent("bonus_updated", Event_bonus_updated, EventHookMode_Post);
    HookEvent("achievement_increment", Event_achievement_increment, EventHookMode_Post);
    HookEvent("physgun_pickup", Event_physgun_pickup, EventHookMode_Post);
    HookEvent("flare_ignite_npc", Event_flare_ignite_npc, EventHookMode_Post);
    HookEvent("vote_cast", Event_vote_cast, EventHookMode_Post);
    HookEvent("player_info", Event_player_info, EventHookMode_Post);
    HookEvent("player_death", Event_player_death, EventHookMode_Post);
    HookEvent("player_hurt", Event_player_hurt, EventHookMode_Post);
    HookEvent("item_purchase", Event_item_purchase, EventHookMode_Post);
    HookEvent("bomb_beginplant", Event_bomb_beginplant, EventHookMode_Post);
    HookEvent("bomb_abortplant", Event_bomb_abortplant, EventHookMode_Post);
    HookEvent("bomb_planted", Event_bomb_planted, EventHookMode_Post);
    HookEvent("bomb_defused", Event_bomb_defused, EventHookMode_Post);
    HookEvent("bomb_exploded", Event_bomb_exploded, EventHookMode_Post);
    HookEvent("bomb_dropped", Event_bomb_dropped, EventHookMode_Post);
    HookEvent("bomb_pickup", Event_bomb_pickup, EventHookMode_Post);
    HookEvent("defuser_dropped", Event_defuser_dropped, EventHookMode_Post);
    HookEvent("defuser_pickup", Event_defuser_pickup, EventHookMode_Post);
    HookEvent("announce_phase_end", Event_announce_phase_end, EventHookMode_Post);
    HookEvent("cs_intermission", Event_cs_intermission, EventHookMode_Post);
    HookEvent("bomb_begindefuse", Event_bomb_begindefuse, EventHookMode_Post);
    HookEvent("bomb_abortdefuse", Event_bomb_abortdefuse, EventHookMode_Post);
    HookEvent("hostage_follows", Event_hostage_follows, EventHookMode_Post);
    HookEvent("hostage_hurt", Event_hostage_hurt, EventHookMode_Post);
    HookEvent("hostage_killed", Event_hostage_killed, EventHookMode_Post);
    HookEvent("hostage_rescued", Event_hostage_rescued, EventHookMode_Post);
    HookEvent("hostage_stops_following", Event_hostage_stops_following, EventHookMode_Post);
    HookEvent("hostage_rescued_all", Event_hostage_rescued_all, EventHookMode_Post);
    HookEvent("hostage_call_for_help", Event_hostage_call_for_help, EventHookMode_Post);
    HookEvent("vip_escaped", Event_vip_escaped, EventHookMode_Post);
    HookEvent("vip_killed", Event_vip_killed, EventHookMode_Post);
    HookEvent("player_radio", Event_player_radio, EventHookMode_Post);
    HookEvent("bomb_beep", Event_bomb_beep, EventHookMode_Post);
    HookEvent("weapon_fire", Event_weapon_fire, EventHookMode_Post);
    HookEvent("weapon_fire_on_empty", Event_weapon_fire_on_empty, EventHookMode_Post);
    HookEvent("weapon_outofammo", Event_weapon_outofammo, EventHookMode_Post);
    HookEvent("weapon_reload", Event_weapon_reload, EventHookMode_Post);
    HookEvent("weapon_zoom", Event_weapon_zoom, EventHookMode_Post);
    HookEvent("silencer_detach", Event_silencer_detach, EventHookMode_Post);
    HookEvent("inspect_weapon", Event_inspect_weapon, EventHookMode_Post);
    HookEvent("weapon_zoom_rifle", Event_weapon_zoom_rifle, EventHookMode_Post);
    HookEvent("player_spawned", Event_player_spawned, EventHookMode_Post);
    HookEvent("item_pickup", Event_item_pickup, EventHookMode_Post);
    HookEvent("ammo_pickup", Event_ammo_pickup, EventHookMode_Post);
    HookEvent("item_equip", Event_item_equip, EventHookMode_Post);
    HookEvent("enter_buyzone", Event_enter_buyzone, EventHookMode_Post);
    HookEvent("exit_buyzone", Event_exit_buyzone, EventHookMode_Post);
    HookEvent("buytime_ended", Event_buytime_ended, EventHookMode_Post);
    HookEvent("enter_bombzone", Event_enter_bombzone, EventHookMode_Post);
    HookEvent("exit_bombzone", Event_exit_bombzone, EventHookMode_Post);
    HookEvent("enter_rescue_zone", Event_enter_rescue_zone, EventHookMode_Post);
    HookEvent("exit_rescue_zone", Event_exit_rescue_zone, EventHookMode_Post);
    HookEvent("silencer_off", Event_silencer_off, EventHookMode_Post);
    HookEvent("silencer_on", Event_silencer_on, EventHookMode_Post);
    HookEvent("buymenu_open", Event_buymenu_open, EventHookMode_Post);
    HookEvent("buymenu_close", Event_buymenu_close, EventHookMode_Post);
    HookEvent("round_prestart", Event_round_prestart, EventHookMode_Post);
    HookEvent("round_poststart", Event_round_poststart, EventHookMode_Post);
    HookEvent("round_start", Event_round_start, EventHookMode_Post);
    HookEvent("round_end", Event_round_end, EventHookMode_Post);
    HookEvent("grenade_bounce", Event_grenade_bounce, EventHookMode_Post);
    HookEvent("hegrenade_detonate", Event_hegrenade_detonate, EventHookMode_Post);
    HookEvent("flashbang_detonate", Event_flashbang_detonate, EventHookMode_Post);
    HookEvent("smokegrenade_detonate", Event_smokegrenade_detonate, EventHookMode_Post);
    HookEvent("smokegrenade_expired", Event_smokegrenade_expired, EventHookMode_Post);
    HookEvent("molotov_detonate", Event_molotov_detonate, EventHookMode_Post);
    HookEvent("decoy_detonate", Event_decoy_detonate, EventHookMode_Post);
    HookEvent("decoy_started", Event_decoy_started, EventHookMode_Post);
    HookEvent("inferno_startburn", Event_inferno_startburn, EventHookMode_Post);
    HookEvent("inferno_expire", Event_inferno_expire, EventHookMode_Post);
    HookEvent("inferno_extinguish", Event_inferno_extinguish, EventHookMode_Post);
    HookEvent("decoy_firing", Event_decoy_firing, EventHookMode_Post);
    HookEvent("bullet_impact", Event_bullet_impact, EventHookMode_Post);
    HookEvent("player_footstep", Event_player_footstep, EventHookMode_Post);
    HookEvent("player_jump", Event_player_jump, EventHookMode_Post);
    HookEvent("player_blind", Event_player_blind, EventHookMode_Post);
    HookEvent("player_falldamage", Event_player_falldamage, EventHookMode_Post);
    HookEvent("door_moving", Event_door_moving, EventHookMode_Post);
    HookEvent("round_freeze_end", Event_round_freeze_end, EventHookMode_Post);
    HookEvent("mb_input_lock_success", Event_mb_input_lock_success, EventHookMode_Post);
    HookEvent("mb_input_lock_cancel", Event_mb_input_lock_cancel, EventHookMode_Post);
    HookEvent("nav_blocked", Event_nav_blocked, EventHookMode_Post);
    HookEvent("nav_generate", Event_nav_generate, EventHookMode_Post);
    HookEvent("player_stats_updated", Event_player_stats_updated, EventHookMode_Post);
    HookEvent("achievement_info_loaded", Event_achievement_info_loaded, EventHookMode_Post);
    HookEvent("spec_target_updated", Event_spec_target_updated, EventHookMode_Post);
    HookEvent("hltv_changed_mode", Event_hltv_changed_mode, EventHookMode_Post);
    HookEvent("cs_game_disconnected", Event_cs_game_disconnected, EventHookMode_Post);
    HookEvent("cs_win_panel_round", Event_cs_win_panel_round, EventHookMode_Post);
    HookEvent("cs_win_panel_match", Event_cs_win_panel_match, EventHookMode_Post);
    HookEvent("cs_match_end_restart", Event_cs_match_end_restart, EventHookMode_Post);
    HookEvent("cs_pre_restart", Event_cs_pre_restart, EventHookMode_Post);
    HookEvent("show_freezepanel", Event_show_freezepanel, EventHookMode_Post);
    HookEvent("hide_freezepanel", Event_hide_freezepanel, EventHookMode_Post);
    HookEvent("freezecam_started", Event_freezecam_started, EventHookMode_Post);
    HookEvent("player_avenged_teammate", Event_player_avenged_teammate, EventHookMode_Post);
    HookEvent("achievement_earned", Event_achievement_earned, EventHookMode_Post);
    HookEvent("achievement_earned_local", Event_achievement_earned_local, EventHookMode_Post);
    HookEvent("item_found", Event_item_found, EventHookMode_Post);
    HookEvent("match_end_conditions", Event_match_end_conditions, EventHookMode_Post);
    HookEvent("round_mvp", Event_round_mvp, EventHookMode_Post);
    HookEvent("player_decal", Event_player_decal, EventHookMode_Post);
    HookEvent("teamplay_round_start", Event_teamplay_round_start, EventHookMode_Post);
    HookEvent("client_disconnect", Event_client_disconnect, EventHookMode_Post);
    HookEvent("switch_team", Event_switch_team, EventHookMode_Post);
    HookEvent("write_profile_data", Event_write_profile_data, EventHookMode_Post);
    HookEvent("update_matchmaking_stats", Event_update_matchmaking_stats, EventHookMode_Post);
    HookEvent("player_reset_vote", Event_player_reset_vote, EventHookMode_Post);
    HookEvent("enable_restart_voting", Event_enable_restart_voting, EventHookMode_Post);
    HookEvent("sfuievent", Event_sfuievent, EventHookMode_Post);
    HookEvent("start_vote", Event_start_vote, EventHookMode_Post);
    HookEvent("player_given_c4", Event_player_given_c4, EventHookMode_Post);
    HookEvent("tr_player_flashbanged", Event_tr_player_flashbanged, EventHookMode_Post);
    HookEvent("tr_mark_complete", Event_tr_mark_complete, EventHookMode_Post);
    HookEvent("tr_mark_best_time", Event_tr_mark_best_time, EventHookMode_Post);
    HookEvent("tr_exit_hint_trigger", Event_tr_exit_hint_trigger, EventHookMode_Post);
    HookEvent("bot_takeover", Event_bot_takeover, EventHookMode_Post);
    HookEvent("tr_show_finish_msgbox", Event_tr_show_finish_msgbox, EventHookMode_Post);
    HookEvent("tr_show_exit_msgbox", Event_tr_show_exit_msgbox, EventHookMode_Post);
    HookEvent("reset_player_controls", Event_reset_player_controls, EventHookMode_Post);
    HookEvent("jointeam_failed", Event_jointeam_failed, EventHookMode_Post);
    HookEvent("teamchange_pending", Event_teamchange_pending, EventHookMode_Post);
    HookEvent("material_default_complete", Event_material_default_complete, EventHookMode_Post);
    HookEvent("cs_prev_next_spectator", Event_cs_prev_next_spectator, EventHookMode_Post);
    HookEvent("cs_handle_ime_event", Event_cs_handle_ime_event, EventHookMode_Post);
    HookEvent("nextlevel_changed", Event_nextlevel_changed, EventHookMode_Post);
    HookEvent("seasoncoin_levelup", Event_seasoncoin_levelup, EventHookMode_Post);

    AddCommandListener(HookJoinTeam, "jointeam");

    OpenSocket();
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
        LogMessage("Putting on TEAMA");
        CS_SwitchTeam(client, TEAM_TEAM);
    } else {
        LogMessage("Putting on TEAMB");
        CS_SwitchTeam(client, (TEAM_TEAM == 1 ? 2 : 1));
    }
    return Plugin_Continue;
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
// TODO: this should post the winner and stats (big payload) to the wrapper
public Action:HookMatchEnd(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];
    Format(buffer, sizeof(buffer), "9999");
    LogLine(buffer);
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

// -- SOCKET LOGGERS --
public Action:Event_player_connect(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];
    decl String:buff_name[64];
    GetEventString(event, "name", buff_name, sizeof(buff_name));    decl String:buff_networkid[64];
    GetEventString(event, "networkid", buff_networkid, sizeof(buff_networkid));    decl String:buff_address[64];
    GetEventString(event, "address", buff_address, sizeof(buff_address));
    Format(buffer, sizeof(buffer), "0,%s,%d,%d,%s,%s,%d",
        buff_name,
        GetEventInt(event, "index"),
        GetEventInt(event, "userid"),
        buff_networkid,
        buff_address,
        GetEventInt(event, "bot"));
    LogLine(buffer);
}



public Action:Event_player_disconnect(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];
    decl String:buff_reason[64];
    GetEventString(event, "reason", buff_reason, sizeof(buff_reason));    decl String:buff_name[64];
    GetEventString(event, "name", buff_name, sizeof(buff_name));    decl String:buff_networkid[64];
    GetEventString(event, "networkid", buff_networkid, sizeof(buff_networkid));
    Format(buffer, sizeof(buffer), "1,%d,%s,%s,%s,%d",
        GetEventInt(event, "userid"),
        buff_reason,
        buff_name,
        buff_networkid,
        GetEventInt(event, "bot"));
    LogLine(buffer);
}



public Action:Event_player_activate(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "2,%d",
        GetEventInt(event, "userid"));
    LogLine(buffer);
}



public Action:Event_player_say(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];
    decl String:buff_text[64];
    GetEventString(event, "text", buff_text, sizeof(buff_text));
    Format(buffer, sizeof(buffer), "3,%d,%s",
        GetEventInt(event, "userid"),
        buff_text);
    LogLine(buffer);
}



public Action:Event_team_info(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];
    decl String:buff_teamname[64];
    GetEventString(event, "teamname", buff_teamname, sizeof(buff_teamname));
    Format(buffer, sizeof(buffer), "4,%d,%s",
        GetEventInt(event, "teamid"),
        buff_teamname);
    LogLine(buffer);
}



public Action:Event_team_score(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "5,%d,%d",
        GetEventInt(event, "teamid"),
        GetEventInt(event, "score"));
    LogLine(buffer);
}



public Action:Event_teamplay_broadcast_audio(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];
    decl String:buff_sound[64];
    GetEventString(event, "sound", buff_sound, sizeof(buff_sound));
    Format(buffer, sizeof(buffer), "6,%d,%s",
        GetEventInt(event, "team"),
        buff_sound);
    LogLine(buffer);
}



public Action:Event_player_team(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];
    decl String:buff_name[64];
    GetEventString(event, "name", buff_name, sizeof(buff_name));
    Format(buffer, sizeof(buffer), "7,%d,%d,%d,%d,%d,%d,%s",
        GetEventInt(event, "userid"),
        GetEventInt(event, "team"),
        GetEventInt(event, "oldteam"),
        GetEventBool(event, "disconnect"),
        GetEventBool(event, "autoteam"),
        GetEventBool(event, "silent"),
        buff_name);
    LogLine(buffer);
}



public Action:Event_player_class(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];
    decl String:buff_class[64];
    GetEventString(event, "class", buff_class, sizeof(buff_class));
    Format(buffer, sizeof(buffer), "8,%d,%s",
        GetEventInt(event, "userid"),
        buff_class);
    LogLine(buffer);
}



public Action:Event_player_chat(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];
    decl String:buff_text[64];
    GetEventString(event, "text", buff_text, sizeof(buff_text));
    Format(buffer, sizeof(buffer), "9,%d,%d,%s",
        GetEventBool(event, "teamonly"),
        GetEventInt(event, "userid"),
        buff_text);
    LogLine(buffer);
}



public Action:Event_player_score(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "10,%d,%d,%d,%d",
        GetEventInt(event, "userid"),
        GetEventInt(event, "kills"),
        GetEventInt(event, "deaths"),
        GetEventInt(event, "score"));
    LogLine(buffer);
}



public Action:Event_player_spawn(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "11,%d",
        GetEventInt(event, "userid"));
    LogLine(buffer);
}



public Action:Event_player_shoot(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "12,%d,%d,%d",
        GetEventInt(event, "userid"),
        GetEventInt(event, "weapon"),
        GetEventInt(event, "mode"));
    LogLine(buffer);
}



public Action:Event_player_use(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "13,%d,%d",
        GetEventInt(event, "userid"),
        GetEventInt(event, "entity"));
    LogLine(buffer);
}



public Action:Event_player_changename(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];
    decl String:buff_oldname[64];
    GetEventString(event, "oldname", buff_oldname, sizeof(buff_oldname));    decl String:buff_newname[64];
    GetEventString(event, "newname", buff_newname, sizeof(buff_newname));
    Format(buffer, sizeof(buffer), "14,%d,%s,%s",
        GetEventInt(event, "userid"),
        buff_oldname,
        buff_newname);
    LogLine(buffer);
}



public Action:Event_player_hintmessage(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];
    decl String:buff_hintmessage[64];
    GetEventString(event, "hintmessage", buff_hintmessage, sizeof(buff_hintmessage));
    Format(buffer, sizeof(buffer), "15,%s",
        buff_hintmessage);
    LogLine(buffer);
}


public Action:Event_game_newmap(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];
    decl String:buff_mapname[64];
    GetEventString(event, "mapname", buff_mapname, sizeof(buff_mapname));
    Format(buffer, sizeof(buffer), "17,%s",
        buff_mapname);
    LogLine(buffer);
}



public Action:Event_game_start(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];
    decl String:buff_objective[64];
    GetEventString(event, "objective", buff_objective, sizeof(buff_objective));
    Format(buffer, sizeof(buffer), "18,%d,%d,%d,%s",
        GetEventInt(event, "roundslimit"),
        GetEventInt(event, "timelimit"),
        GetEventInt(event, "fraglimit"),
        buff_objective);
    LogLine(buffer);
}



public Action:Event_game_end(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "19,%d",
        GetEventInt(event, "winner"));
    LogLine(buffer);
}



public Action:Event_game_message(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];
    decl String:buff_text[64];
    GetEventString(event, "text", buff_text, sizeof(buff_text));
    Format(buffer, sizeof(buffer), "20,%d,%s",
        GetEventInt(event, "target"),
        buff_text);
    LogLine(buffer);
}



public Action:Event_break_breakable(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "21,%d,%d,%d",
        GetEventInt(event, "entindex"),
        GetEventInt(event, "userid"),
        GetEventInt(event, "material"));
    LogLine(buffer);
}



public Action:Event_break_prop(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "22,%d,%d",
        GetEventInt(event, "entindex"),
        GetEventInt(event, "userid"));
    LogLine(buffer);
}



public Action:Event_entity_killed(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "23,%d,%d,%d,%d",
        GetEventInt(event, "entindex_killed"),
        GetEventInt(event, "entindex_attacker"),
        GetEventInt(event, "entindex_inflictor"),
        GetEventInt(event, "damagebits"));
    LogLine(buffer);
}



public Action:Event_bonus_updated(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "24,%d,%d,%d,%d",
        GetEventInt(event, "numadvanced"),
        GetEventInt(event, "numbronze"),
        GetEventInt(event, "numsilver"),
        GetEventInt(event, "numgold"));
    LogLine(buffer);
}



public Action:Event_achievement_increment(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "25,%d,%d,%d",
        GetEventInt(event, "achievement_id"),
        GetEventInt(event, "cur_val"),
        GetEventInt(event, "max_val"));
    LogLine(buffer);
}



public Action:Event_physgun_pickup(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "26,%d",
        GetEventInt(event, "entindex"));
    LogLine(buffer);
}



public Action:Event_flare_ignite_npc(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "27,%d",
        GetEventInt(event, "entindex"));
    LogLine(buffer);
}



public Action:Event_vote_cast(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "28,%d,%d,%d",
        GetEventInt(event, "vote_option"),
        GetEventInt(event, "team"),
        GetEventInt(event, "entityid"));
    LogLine(buffer);
}



public Action:Event_player_info(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];
    decl String:buff_name[64];
    GetEventString(event, "name", buff_name, sizeof(buff_name));    decl String:buff_networkid[64];
    GetEventString(event, "networkid", buff_networkid, sizeof(buff_networkid));
    Format(buffer, sizeof(buffer), "29,%s,%d,%d,%s,%d",
        buff_name,
        GetEventInt(event, "index"),
        GetEventInt(event, "userid"),
        buff_networkid,
        GetEventBool(event, "bot"));
    LogLine(buffer);
}



public Action:Event_player_death(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];
    decl String:buff_weapon[64];
    GetEventString(event, "weapon", buff_weapon, sizeof(buff_weapon));
    Format(buffer, sizeof(buffer), "30,%d,%d,%d,%s,%d,%d,%d,%d",
        GetEventInt(event, "userid"),
        GetEventInt(event, "attacker"),
        GetEventInt(event, "assister"),
        buff_weapon,
        GetEventBool(event, "headshot"),
        GetEventInt(event, "dominated"),
        GetEventInt(event, "revenge"),
        GetEventInt(event, "penetrated"));
    LogLine(buffer);
}



public Action:Event_player_hurt(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];
    decl String:buff_weapon[64];
    GetEventString(event, "weapon", buff_weapon, sizeof(buff_weapon));
    Format(buffer, sizeof(buffer), "31,%d,%d,%d,%d,%s,%d,%d,%d",
        GetEventInt(event, "userid"),
        GetEventInt(event, "attacker"),
        GetEventInt(event, "health"),
        GetEventInt(event, "armor"),
        buff_weapon,
        GetEventInt(event, "dmg_health"),
        GetEventInt(event, "dmg_armor"),
        GetEventInt(event, "hitgroup"));
    LogLine(buffer);
}



public Action:Event_item_purchase(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];
    decl String:buff_weapon[64];
    GetEventString(event, "weapon", buff_weapon, sizeof(buff_weapon));
    Format(buffer, sizeof(buffer), "32,%d,%d,%s",
        GetEventInt(event, "userid"),
        GetEventInt(event, "team"),
        buff_weapon);
    LogLine(buffer);
}



public Action:Event_bomb_beginplant(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "33,%d,%d",
        GetEventInt(event, "userid"),
        GetEventInt(event, "site"));
    LogLine(buffer);
}



public Action:Event_bomb_abortplant(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "34,%d,%d",
        GetEventInt(event, "userid"),
        GetEventInt(event, "site"));
    LogLine(buffer);
}



public Action:Event_bomb_planted(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "35,%d,%d",
        GetEventInt(event, "userid"),
        GetEventInt(event, "site"));
    LogLine(buffer);
}



public Action:Event_bomb_defused(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "36,%d,%d",
        GetEventInt(event, "userid"),
        GetEventInt(event, "site"));
    LogLine(buffer);
}



public Action:Event_bomb_exploded(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "37,%d,%d",
        GetEventInt(event, "userid"),
        GetEventInt(event, "site"));
    LogLine(buffer);
}



public Action:Event_bomb_dropped(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "38,%d,%d",
        GetEventInt(event, "userid"),
        GetEventInt(event, "entindex"));
    LogLine(buffer);
}



public Action:Event_bomb_pickup(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "39,%d",
        GetEventInt(event, "userid"));
    LogLine(buffer);
}



public Action:Event_defuser_dropped(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "40,%d",
        GetEventInt(event, "entityid"));
    LogLine(buffer);
}



public Action:Event_defuser_pickup(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "41,%d,%d",
        GetEventInt(event, "entityid"),
        GetEventInt(event, "userid"));
    LogLine(buffer);
}



public Action:Event_announce_phase_end(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "42,"
);
    LogLine(buffer);
}



public Action:Event_cs_intermission(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "43,"
);
    LogLine(buffer);
}



public Action:Event_bomb_begindefuse(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "44,%d,%d",
        GetEventInt(event, "userid"),
        GetEventBool(event, "haskit"));
    LogLine(buffer);
}



public Action:Event_bomb_abortdefuse(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "45,%d",
        GetEventInt(event, "userid"));
    LogLine(buffer);
}



public Action:Event_hostage_follows(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "46,%d,%d",
        GetEventInt(event, "userid"),
        GetEventInt(event, "hostage"));
    LogLine(buffer);
}



public Action:Event_hostage_hurt(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "47,%d,%d",
        GetEventInt(event, "userid"),
        GetEventInt(event, "hostage"));
    LogLine(buffer);
}



public Action:Event_hostage_killed(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "48,%d,%d",
        GetEventInt(event, "userid"),
        GetEventInt(event, "hostage"));
    LogLine(buffer);
}



public Action:Event_hostage_rescued(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "49,%d,%d,%d",
        GetEventInt(event, "userid"),
        GetEventInt(event, "hostage"),
        GetEventInt(event, "site"));
    LogLine(buffer);
}



public Action:Event_hostage_stops_following(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "50,%d,%d",
        GetEventInt(event, "userid"),
        GetEventInt(event, "hostage"));
    LogLine(buffer);
}



public Action:Event_hostage_rescued_all(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "51,"
);
    LogLine(buffer);
}



public Action:Event_hostage_call_for_help(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "52,%d",
        GetEventInt(event, "hostage"));
    LogLine(buffer);
}



public Action:Event_vip_escaped(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "53,%d",
        GetEventInt(event, "userid"));
    LogLine(buffer);
}



public Action:Event_vip_killed(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "54,%d,%d",
        GetEventInt(event, "userid"),
        GetEventInt(event, "attacker"));
    LogLine(buffer);
}



public Action:Event_player_radio(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "55,%d,%d",
        GetEventInt(event, "userid"),
        GetEventInt(event, "slot"));
    LogLine(buffer);
}



public Action:Event_bomb_beep(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "56,%d",
        GetEventInt(event, "entindex"));
    LogLine(buffer);
}



public Action:Event_weapon_fire(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];
    decl String:buff_weapon[64];
    GetEventString(event, "weapon", buff_weapon, sizeof(buff_weapon));
    Format(buffer, sizeof(buffer), "57,%d,%s,%d",
        GetEventInt(event, "userid"),
        buff_weapon,
        GetEventBool(event, "silenced"));
    LogLine(buffer);
}



public Action:Event_weapon_fire_on_empty(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];
    decl String:buff_weapon[64];
    GetEventString(event, "weapon", buff_weapon, sizeof(buff_weapon));
    Format(buffer, sizeof(buffer), "58,%d,%s",
        GetEventInt(event, "userid"),
        buff_weapon);
    LogLine(buffer);
}



public Action:Event_weapon_outofammo(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "59,%d",
        GetEventInt(event, "userid"));
    LogLine(buffer);
}



public Action:Event_weapon_reload(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "60,%d",
        GetEventInt(event, "userid"));
    LogLine(buffer);
}



public Action:Event_weapon_zoom(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "61,%d",
        GetEventInt(event, "userid"));
    LogLine(buffer);
}



public Action:Event_silencer_detach(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "62,%d",
        GetEventInt(event, "userid"));
    LogLine(buffer);
}



public Action:Event_inspect_weapon(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "63,%d",
        GetEventInt(event, "userid"));
    LogLine(buffer);
}



public Action:Event_weapon_zoom_rifle(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "64,%d",
        GetEventInt(event, "userid"));
    LogLine(buffer);
}



public Action:Event_player_spawned(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "65,%d,%d",
        GetEventInt(event, "userid"),
        GetEventBool(event, "inrestart"));
    LogLine(buffer);
}



public Action:Event_item_pickup(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];
    decl String:buff_item[64];
    GetEventString(event, "item", buff_item, sizeof(buff_item));
    Format(buffer, sizeof(buffer), "66,%d,%s",
        GetEventInt(event, "userid"),
        buff_item);
    LogLine(buffer);
}



public Action:Event_ammo_pickup(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];
    decl String:buff_item[64];
    GetEventString(event, "item", buff_item, sizeof(buff_item));
    Format(buffer, sizeof(buffer), "67,%d,%s,%d",
        GetEventInt(event, "userid"),
        buff_item,
        GetEventInt(event, "index"));
    LogLine(buffer);
}



public Action:Event_item_equip(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];
    decl String:buff_item[64];
    GetEventString(event, "item", buff_item, sizeof(buff_item));
    Format(buffer, sizeof(buffer), "68,%d,%s,%d,%d,%d,%d,%d,%d",
        GetEventInt(event, "userid"),
        buff_item,
        GetEventBool(event, "canzoom"),
        GetEventBool(event, "hassilencer"),
        GetEventBool(event, "issilenced"),
        GetEventBool(event, "hastracers"),
        GetEventInt(event, "weptype"),
        GetEventBool(event, "ispainted"));
    LogLine(buffer);
}



public Action:Event_enter_buyzone(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "69,%d,%d",
        GetEventInt(event, "userid"),
        GetEventBool(event, "canbuy"));
    LogLine(buffer);
}



public Action:Event_exit_buyzone(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "70,%d,%d",
        GetEventInt(event, "userid"),
        GetEventBool(event, "canbuy"));
    LogLine(buffer);
}



public Action:Event_buytime_ended(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "71,"
);
    LogLine(buffer);
}



public Action:Event_enter_bombzone(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "72,%d,%d,%d",
        GetEventInt(event, "userid"),
        GetEventBool(event, "hasbomb"),
        GetEventBool(event, "isplanted"));
    LogLine(buffer);
}



public Action:Event_exit_bombzone(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "73,%d,%d,%d",
        GetEventInt(event, "userid"),
        GetEventBool(event, "hasbomb"),
        GetEventBool(event, "isplanted"));
    LogLine(buffer);
}



public Action:Event_enter_rescue_zone(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "74,%d",
        GetEventInt(event, "userid"));
    LogLine(buffer);
}



public Action:Event_exit_rescue_zone(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "75,%d",
        GetEventInt(event, "userid"));
    LogLine(buffer);
}



public Action:Event_silencer_off(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "76,%d",
        GetEventInt(event, "userid"));
    LogLine(buffer);
}



public Action:Event_silencer_on(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "77,%d",
        GetEventInt(event, "userid"));
    LogLine(buffer);
}



public Action:Event_buymenu_open(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "78,%d",
        GetEventInt(event, "userid"));
    LogLine(buffer);
}



public Action:Event_buymenu_close(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "79,%d",
        GetEventInt(event, "userid"));
    LogLine(buffer);
}



public Action:Event_round_prestart(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "80,"
);
    LogLine(buffer);
}



public Action:Event_round_poststart(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "81,"
);
    LogLine(buffer);
}



public Action:Event_round_start(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];
    decl String:buff_objective[64];
    GetEventString(event, "objective", buff_objective, sizeof(buff_objective));
    Format(buffer, sizeof(buffer), "82,%d,%d,%s",
        GetEventInt(event, "timelimit"),
        GetEventInt(event, "fraglimit"),
        buff_objective);
    LogLine(buffer);
}



public Action:Event_round_end(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];
    decl String:buff_message[64];
    GetEventString(event, "message", buff_message, sizeof(buff_message));
    Format(buffer, sizeof(buffer), "83,%d,%d,%s",
        GetEventInt(event, "winner"),
        GetEventInt(event, "reason"),
        buff_message);
    LogLine(buffer);
}



public Action:Event_grenade_bounce(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "84,%d",
        GetEventInt(event, "userid"));
    LogLine(buffer);
}



public Action:Event_hegrenade_detonate(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "85,%d,%d,%f,%f,%f",
        GetEventInt(event, "userid"),
        GetEventInt(event, "entityid"),
        GetEventFloat(event, "x"),
        GetEventFloat(event, "y"),
        GetEventFloat(event, "z"));
    LogLine(buffer);
}



public Action:Event_flashbang_detonate(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "86,%d,%d,%f,%f,%f",
        GetEventInt(event, "userid"),
        GetEventInt(event, "entityid"),
        GetEventFloat(event, "x"),
        GetEventFloat(event, "y"),
        GetEventFloat(event, "z"));
    LogLine(buffer);
}



public Action:Event_smokegrenade_detonate(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "87,%d,%d,%f,%f,%f",
        GetEventInt(event, "userid"),
        GetEventInt(event, "entityid"),
        GetEventFloat(event, "x"),
        GetEventFloat(event, "y"),
        GetEventFloat(event, "z"));
    LogLine(buffer);
}



public Action:Event_smokegrenade_expired(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "88,%d,%d,%f,%f,%f",
        GetEventInt(event, "userid"),
        GetEventInt(event, "entityid"),
        GetEventFloat(event, "x"),
        GetEventFloat(event, "y"),
        GetEventFloat(event, "z"));
    LogLine(buffer);
}



public Action:Event_molotov_detonate(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "89,%d,%f,%f,%f",
        GetEventInt(event, "userid"),
        GetEventFloat(event, "x"),
        GetEventFloat(event, "y"),
        GetEventFloat(event, "z"));
    LogLine(buffer);
}



public Action:Event_decoy_detonate(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "90,%d,%d,%f,%f,%f",
        GetEventInt(event, "userid"),
        GetEventInt(event, "entityid"),
        GetEventFloat(event, "x"),
        GetEventFloat(event, "y"),
        GetEventFloat(event, "z"));
    LogLine(buffer);
}



public Action:Event_decoy_started(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "91,%d,%d,%f,%f,%f",
        GetEventInt(event, "userid"),
        GetEventInt(event, "entityid"),
        GetEventFloat(event, "x"),
        GetEventFloat(event, "y"),
        GetEventFloat(event, "z"));
    LogLine(buffer);
}



public Action:Event_inferno_startburn(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "92,%d,%f,%f,%f",
        GetEventInt(event, "entityid"),
        GetEventFloat(event, "x"),
        GetEventFloat(event, "y"),
        GetEventFloat(event, "z"));
    LogLine(buffer);
}



public Action:Event_inferno_expire(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "93,%d,%f,%f,%f",
        GetEventInt(event, "entityid"),
        GetEventFloat(event, "x"),
        GetEventFloat(event, "y"),
        GetEventFloat(event, "z"));
    LogLine(buffer);
}



public Action:Event_inferno_extinguish(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "94,%d,%f,%f,%f",
        GetEventInt(event, "entityid"),
        GetEventFloat(event, "x"),
        GetEventFloat(event, "y"),
        GetEventFloat(event, "z"));
    LogLine(buffer);
}



public Action:Event_decoy_firing(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "95,%d,%d,%f,%f,%f",
        GetEventInt(event, "userid"),
        GetEventInt(event, "entityid"),
        GetEventFloat(event, "x"),
        GetEventFloat(event, "y"),
        GetEventFloat(event, "z"));
    LogLine(buffer);
}



public Action:Event_bullet_impact(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "96,%d,%f,%f,%f",
        GetEventInt(event, "userid"),
        GetEventFloat(event, "x"),
        GetEventFloat(event, "y"),
        GetEventFloat(event, "z"));
    LogLine(buffer);
}



public Action:Event_player_footstep(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "97,%d",
        GetEventInt(event, "userid"));
    LogLine(buffer);
}



public Action:Event_player_jump(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "98,%d",
        GetEventInt(event, "userid"));
    LogLine(buffer);
}



public Action:Event_player_blind(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "99,%d",
        GetEventInt(event, "userid"));
    LogLine(buffer);
}



public Action:Event_player_falldamage(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "100,%d,%f",
        GetEventInt(event, "userid"),
        GetEventFloat(event, "damage"));
    LogLine(buffer);
}



public Action:Event_door_moving(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "101,%d,%d",
        GetEventInt(event, "entindex"),
        GetEventInt(event, "userid"));
    LogLine(buffer);
}



public Action:Event_round_freeze_end(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "102,"
);
    LogLine(buffer);
}



public Action:Event_mb_input_lock_success(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "103,"
);
    LogLine(buffer);
}



public Action:Event_mb_input_lock_cancel(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "104,"
);
    LogLine(buffer);
}



public Action:Event_nav_blocked(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "105,%d,%d",
        GetEventInt(event, "area"),
        GetEventBool(event, "blocked"));
    LogLine(buffer);
}



public Action:Event_nav_generate(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "106,"
);
    LogLine(buffer);
}



public Action:Event_player_stats_updated(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "107,%d",
        GetEventBool(event, "forceupload"));
    LogLine(buffer);
}



public Action:Event_achievement_info_loaded(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "108,"
);
    LogLine(buffer);
}



public Action:Event_spec_target_updated(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "109,%d",
        GetEventInt(event, "userid"));
    LogLine(buffer);
}



public Action:Event_hltv_changed_mode(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "110,%d,%d,%d",
        GetEventInt(event, "oldmode"),
        GetEventInt(event, "newmode"),
        GetEventInt(event, "obs_target"));
    LogLine(buffer);
}



public Action:Event_cs_game_disconnected(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "111,"
);
    LogLine(buffer);
}



public Action:Event_cs_win_panel_round(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];
    decl String:buff_funfact_token[64];
    GetEventString(event, "funfact_token", buff_funfact_token, sizeof(buff_funfact_token));
    Format(buffer, sizeof(buffer), "112,%d,%d,%d,%d,%s,%d,%d,%d,%d",
        GetEventBool(event, "show_timer_defend"),
        GetEventBool(event, "show_timer_attack"),
        GetEventInt(event, "timer_time"),
        GetEventInt(event, "final_event"),
        buff_funfact_token,
        GetEventInt(event, "funfact_player"),
        GetEventInt(event, "funfact_data1"),
        GetEventInt(event, "funfact_data2"),
        GetEventInt(event, "funfact_data3"));
    LogLine(buffer);
}



public Action:Event_cs_win_panel_match(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "113,"
);
    LogLine(buffer);
}



public Action:Event_cs_match_end_restart(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "114,"
);
    LogLine(buffer);
}



public Action:Event_cs_pre_restart(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "115,"
);
    LogLine(buffer);
}



public Action:Event_show_freezepanel(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "116,%d,%d,%d,%d,%d,%d",
        GetEventInt(event, "victim"),
        GetEventInt(event, "killer"),
        GetEventInt(event, "hits_taken"),
        GetEventInt(event, "damage_taken"),
        GetEventInt(event, "hits_given"),
        GetEventInt(event, "damage_given"));
    LogLine(buffer);
}



public Action:Event_hide_freezepanel(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "117,"
);
    LogLine(buffer);
}



public Action:Event_freezecam_started(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "118,"
);
    LogLine(buffer);
}



public Action:Event_player_avenged_teammate(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "119,%d,%d",
        GetEventInt(event, "avenger_id"),
        GetEventInt(event, "avenged_player_id"));
    LogLine(buffer);
}



public Action:Event_achievement_earned(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "120,%d,%d",
        GetEventInt(event, "player"),
        GetEventInt(event, "achievement"));
    LogLine(buffer);
}



public Action:Event_achievement_earned_local(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "121,%d,%d",
        GetEventInt(event, "achievement"),
        GetEventInt(event, "splitscreenplayer"));
    LogLine(buffer);
}



public Action:Event_item_found(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "122,%d,%d,%d,%d,%d",
        GetEventInt(event, "player"),
        GetEventInt(event, "quality"),
        GetEventInt(event, "method"),
        GetEventInt(event, "itemdef"),
        GetEventInt(event, "itemid"));
    LogLine(buffer);
}



public Action:Event_match_end_conditions(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "123,%d,%d,%d,%d",
        GetEventInt(event, "frags"),
        GetEventInt(event, "max_rounds"),
        GetEventInt(event, "win_rounds"),
        GetEventInt(event, "time"));
    LogLine(buffer);
}



public Action:Event_round_mvp(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "124,%d,%d",
        GetEventInt(event, "userid"),
        GetEventInt(event, "reason"));
    LogLine(buffer);
}



public Action:Event_player_decal(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "125,%d",
        GetEventInt(event, "userid"));
    LogLine(buffer);
}



public Action:Event_teamplay_round_start(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "126,%d",
        GetEventBool(event, "full_reset"));
    LogLine(buffer);
}



public Action:Event_client_disconnect(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "127,"
);
    LogLine(buffer);
}



public Action:Event_switch_team(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "128,%d,%d,%d,%d,%d",
        GetEventInt(event, "numPlayers"),
        GetEventInt(event, "numSpectators"),
        GetEventInt(event, "avg_rank"),
        GetEventInt(event, "numTSlotsFree"),
        GetEventInt(event, "numCTSlotsFree"));
    LogLine(buffer);
}



public Action:Event_write_profile_data(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "129,"
);
    LogLine(buffer);
}



public Action:Event_update_matchmaking_stats(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "130,"
);
    LogLine(buffer);
}



public Action:Event_player_reset_vote(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "131,%d,%d",
        GetEventInt(event, "userid"),
        GetEventInt(event, "vote"));
    LogLine(buffer);
}



public Action:Event_enable_restart_voting(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "132,%d",
        GetEventBool(event, "enable"));
    LogLine(buffer);
}



public Action:Event_sfuievent(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];
    decl String:buff_action[64];
    GetEventString(event, "action", buff_action, sizeof(buff_action));    decl String:buff_data[64];
    GetEventString(event, "data", buff_data, sizeof(buff_data));
    Format(buffer, sizeof(buffer), "133,%s,%s,%d",
        buff_action,
        buff_data,
        GetEventInt(event, "slot"));
    LogLine(buffer);
}



public Action:Event_start_vote(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "134,%d,%d,%d",
        GetEventInt(event, "userid"),
        GetEventInt(event, "type"),
        GetEventInt(event, "vote_parameter"));
    LogLine(buffer);
}



public Action:Event_player_given_c4(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "135,%d",
        GetEventInt(event, "userid"));
    LogLine(buffer);
}



public Action:Event_tr_player_flashbanged(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "136,%d",
        GetEventInt(event, "userid"));
    LogLine(buffer);
}



public Action:Event_tr_mark_complete(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "138,%d",
        GetEventInt(event, "complete"));
    LogLine(buffer);
}



public Action:Event_tr_mark_best_time(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "139,%d",
        GetEventInt(event, "time"));
    LogLine(buffer);
}



public Action:Event_tr_exit_hint_trigger(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "140,"
);
    LogLine(buffer);
}



public Action:Event_bot_takeover(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "141,%d,%d,%d",
        GetEventInt(event, "userid"),
        GetEventInt(event, "botid"),
        GetEventInt(event, "index"));
    LogLine(buffer);
}



public Action:Event_tr_show_finish_msgbox(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "142,%d",
        GetEventInt(event, "userid"));
    LogLine(buffer);
}



public Action:Event_tr_show_exit_msgbox(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "143,%d",
        GetEventInt(event, "userid"));
    LogLine(buffer);
}



public Action:Event_reset_player_controls(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "144,"
);
    LogLine(buffer);
}



public Action:Event_jointeam_failed(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "145,%d,%d",
        GetEventInt(event, "userid"),
        GetEventInt(event, "reason"));
    LogLine(buffer);
}



public Action:Event_teamchange_pending(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "146,%d,%d",
        GetEventInt(event, "userid"),
        GetEventInt(event, "toteam"));
    LogLine(buffer);
}



public Action:Event_material_default_complete(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "147,"
);
    LogLine(buffer);
}



public Action:Event_cs_prev_next_spectator(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "148,%d",
        GetEventBool(event, "next"));
    LogLine(buffer);
}



public Action:Event_cs_handle_ime_event(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];
    decl String:buff_eventtype[64];
    GetEventString(event, "eventtype", buff_eventtype, sizeof(buff_eventtype));    decl String:buff_eventdata[64];
    GetEventString(event, "eventdata", buff_eventdata, sizeof(buff_eventdata));
    Format(buffer, sizeof(buffer), "149,%s,%s",
        buff_eventtype,
        buff_eventdata);
    LogLine(buffer);
}



public Action:Event_nextlevel_changed(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];
    decl String:buff_nextlevel[64];
    GetEventString(event, "nextlevel", buff_nextlevel, sizeof(buff_nextlevel));
    Format(buffer, sizeof(buffer), "150,%s",
        buff_nextlevel);
    LogLine(buffer);
}



public Action:Event_seasoncoin_levelup(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];

    Format(buffer, sizeof(buffer), "151,%d,%d,%d",
        GetEventInt(event, "player"),
        GetEventInt(event, "category"),
        GetEventInt(event, "rank"));
    LogLine(buffer);
}


