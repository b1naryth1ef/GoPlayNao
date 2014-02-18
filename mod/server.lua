local Plugin = Plugin
local sessionid = ""
local match = nil
local globdata = {
    processedBans = 0
}

local STATE_NONE, STATE_SETUP, STATE_READY, STATE_PLAYING = 0, 1, 2, 3

Plugin.Version = "1"
Plugin.HasConfig = true
Plugin.ConfigName = "ns2pug.json"

Plugin.DefaultConfig = {
    APIURL = "http://pug.hydr0.com/api/%s?%s",
    ServerID = "",
    ServerHash = "",
}

-- Generic logger
function _log(prefix, msg, ...)
    Shared.Message(string.format("%s: %s", prefix, string.format(msg, ...)))
end

-- Log a debug message
function debug(msg, ...)
    _log("DEBUG", msg, ...)
end

-- Log a warn message
function warn(msg, ...)
    _log("WARN", msg, ...)
end

-- Get the length of a table
function tablelength(T)
    local count = 0
    for _ in pairs(T) do count = count + 1 end
    return count
end

-- Send an api request
function request(url, onSuccess, method, data)
    if method == "" then method = "GET" end

    -- If we have a sessionid, add it to the request data
    if sessionid ~= "" then
        data["sid"] = sessionid
    end

    -- YOLO QUERY STRING
    local qstring = ""
    for k, v in pairs(data) do
        qstring = qstring + string.format("&%s=%s", k, v)
    end

    -- Compile final url, debug, and send
    url = string.format(prefix, url, qstring)
    debug("Sending request: `%s`", url)
    Shared.SendHTTPRequest(url, method, onSuccess)
end

-- Sets up the plugin
function Plugin:Initialise()
    request("servers/register", self:API_GetSessionID, "POST", {
        sid = self.Config.ServerID,
        shash = self.Config.ServerHash
    })

    match = {}
    match.state = STATE_NONE
end

-- Check whether the game should start yet
function Plugin:CheckGameStart(gr)
    if match.state == STATE_PLAYING or match.state == STATE_READY then
        return false
    end

    if State == kGameState.PreGame or State == kGameState.NotStarted then
        if tablelength(match.data.players) == match.size then
            local com1, com2 = Plugin:GetCommanders(gr)

            -- If we do not have two commanders, don't start
            if not com1 or not com2 then
                return false
            end

            local com1id = self:GetSteamID(Server.GetOwner(com1))
            local com2id = self:GetSteamID(Server.GetOwner(com2))

            match.state = STATE_READY
            request("matches/start", self:API_MatchesStart, "POST", {
                id = match.id,
                com1 = com1id,
                com2 = com2id,
            })
        end
    end
end

-- Validate whether the player is allowed into this pug, and post a join message
function Plugin:ClientConnect(client)
    id = self:GetSteamID(client)
    if not id then return end

    if not match.players[id] then
        self:Kick(client, "player not in current match!")
        return
    end

    -- Delete the cooldown timer if its there
    local tname = string.format("dc_%s", id)
    self:DestroyTimer(tname)

    -- TODO: add function to get base table for player
    match.data.players[id] = {}

    -- Grab the player
    local player = Client:GetControllingPlayer()

    -- Tell the world the player joined if we're getting ready
    if match.state ~= STATE_PLAYING then
        Shine:Print("Player %s joined the server, %s/%s players connected",
            true,
            player:GetName(),
            tablelength(match.data.players),
            match.size)
    end

    -- Assign the player to a team based on match data
    local gr = GetGamerules()
    gr:JoinTeam(player, match.players[id])

    -- Check bans (async)
    self:CheckBan(client)
end

-- Remove the player from match data, this is temporary and should be fixed later
function Plugin:ClientDisconnect(client)
    id = self:GetSteamID(client)
    if not id then return end

    if match.state ~= STATE_PLAYING then
        match.data.players[id] = nil
    elseif match.state == STATE_PLAYING
        -- If a player is disconnected for 3 minutes, create a cooldown for them
        --  the backend will create a appropriet ban/etc.
        local tname = string.format("dc_%s", id)
        self:DestroyTimer(tname)
        self:CreateTimer(tname, 60 * 3, 1, function()
            request("players/cooldown", nil, "POST", {
                id = id,
                why = 1
            })
        end)
    end
end

-- Gets a clients steamid
function Plugin:GetSteamID(client)
    -- Need valid clients
    if not Shine:IsValidClient(client) then return end

    local steamid = Client:GetUserId()
    if not steamid or steamid <= 0 then return end

    return steamid
end

-- Kicks a player with a message
function Plugin:Kick(client, msg)
    local player = client:GetControllingPlayer()
    Shine:Print("Client %s (%s) was kicked: %s", true, player:GetName(), self:GetID(client), msg)
    client.DisconnectReason = msg
    Server.DisconnectClient(client)
end

-- Handles a response to servers/register
function Plugin:API_GetSessionID(response)
    -- Check response
    if not response or response == "" then
        warn("Error getting session ID!")
        return
    end

    -- Decode data and get the sessionid
    local data = json.decode(response)
    if data and data.success then
        sessionid = data.sessionid
        debug("Server registered with master, has sessionid: %s", sessionid)
    else
        warn("Error decoding GetSessionID response: `%s`", response)
    end
end

-- Handles a response to match start, starting the game if we're g2g
function Plugin:API_MatchesStart(response)
    if not response or response == "" then
        warn("Error starting match!")
        return
    end

    local data = json.decode(response)
    if data and data.success then
        Shine:Print("STARTING MATCH #%s!", true, match.id)
        -- Just get rid of this shit
        self:DestroyTimer("rup_or_ban")

        local gr = GetGamerules()
        gr:ResetGame()
        gr:SetGameState(kGameState.Countdown)
        gr.countdownTime = kCountDownLength
        gr.lastCountdownPlayed = nil
        match.state = STATE_PLAYING
    end
end

function Plugin:API_BansGet(response)
    if not response or response == "" then
        warn("Error getting ban!")
        return
    end

    -- If the player is banned, kick them and ping the backend server
    local data = json.decode(response)
    if data and data.active then
        -- Get client and kick
        local cli = Shine.GetClientBySteamID(data.steamid)
        local msg = string.format("Player is banned for %s on all NS2PUG servers: %s",
            data.duration, 
            data.reason)
        self:Kick(cli, msg)

        -- Tell the backend someone tried to connect.
        request("bans/ping", nil, "POST", {
            banid: data.id
        })
    end
end

-- Check if a player is banned
function Plugin:CheckBan(cli)
    request("bans/get", self:API_BansGet, "GET", {
        steamid: self:GetSteamId(cli)
    })
end

-- Get both teams commanders
function Plugin:GetCommanders(gamerules)
    return gamerules.team1:GetCommander(), gamerules.team2:GetCommander()
end

-- TODO: this will get data from the backend ping call
function Plugin:SetupMatch()
    -- Players have 5 minutes to connect or they are cooldowned
    self:CreateTimer("rup_or_ban", 60 * 5, 1, function()
        if match.state == STATE_SETUP then
            for k, v in pairs(match.players) do
                local cli = Shine.GetClientBySteamID(k)
                if not cli then
                    request("bans/cooldown", nil, "POST", {
                        id = k,
                        why = 2
                    })
                end
            end
        end
    end)
end

function Plugin:WaitForMatch()
    self:DestroyTimer("match_wait")
    self:CreateTimer("match_wait", 15, 0, function ()
        request("servers/poll", function (resp) 
            if not resp or resp == "" then
                warn("Error polling!")
                return
            end

            local data = json.decode(resp)
            if data.match then
                self:BuildMatch(data.match)
            end

        end, "POST")
    end)

end

function Plugin:BuildMatch(data)
    match = {}
    match.id = data.id
    match.size = data.size
    match.players = data.players
    match.state = STATE_SETUP
    match.config = data.config
    match.data = {
        players: {}
    }
end

-- TEST/TEMP FUNCTIONS
function Plugin:BuildTestMatch()
    match = {}
    match.id = 1
    match.size = 12 -- 6v6
    -- steamid:teamid
    match.players = {38683497: 1}
    match.state = STATE_SETUP
    match.data = {
        players = {}
    }
end
