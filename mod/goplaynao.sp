#pragma semicolon 1

#include <sourcemod>
#include <sdktools>
#include <sdkhooks>
#include <cURL>
#include <json>

#define VERSION "0.1"

public Plugin:myinfo = 
{
    name = "GoPlayNao",
    author = "B1naryTh1ef",
    description = "Matchmaking Plugin for CSGO",
    version = VERSION,
    url = "github.com/b1naryth1ef/goplaynao"
}

new CURL_Default_opt[][2] = {
    {_:CURLOPT_NOSIGNAL,1},
    {_:CURLOPT_NOPROGRESS,1},
    {_:CURLOPT_TIMEOUT,30},
    {_:CURLOPT_CONNECTTIMEOUT,60},
    {_:CURLOPT_VERBOSE,0}
};


#define CURL_DEFAULT_OPT(%1) curl_easy_setopt_int_array(%1, CURL_Default_opt, sizeof(CURL_Default_opt))

new Handle:check_loop = INVALID_HANDLE;


public OnPluginStart() {
    check_loop = CreateTimer(10.0, CheckForMatch, _, TIMER_REPEAT);
}

public Action:CheckForMatch(Handle:timer)
{
    new Handle:curl = curl_easy_init();
    curl_easy_setopt_string(curl, CURLOPT_URL, "http://pug.hydr0.com/api/servers/poll");
    curl_easy_setopt_int(curl, CURLOPT_SSL_VERIFYPEER, 0);
    curl_easy_setopt_int(curl, CURLOPT_SSL_VERIFYHOST, 2);
    curl_easy_setopt_string(curl, CURLOPT_POSTFIELDS, "server=???&hash=???");
    curl_easy_perform_thread(curl, OnComplete);
}

/*
- Poll backend for matches
- Setup matches with map
- Only allow players in match to join
- GOTV/Demo (low-prio)
- Track statistics in local file-buffer
*/