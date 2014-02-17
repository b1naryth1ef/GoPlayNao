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
        id = self.Config.ServerID,
        hash = self.Config.ServerHash
    })

    -- For testing
    self:BuildTestMatch()
end

-- Check whether the game should start yet
function Plugin:CheckGameStart(gr)
    if match.state == STATE_PLAYING or match.state == STATE_READY then
        return false
    end

    if State == kGameState.PreGame or State == kGameState.NotStarted then
        if tablelength(match.data.players) == match.size then
            local com1, com2 = Plugin:GetCommanders(gr)
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
        Plugin:Kick(client, "player not in current match!")
        return
    end

    -- TODO: add function to get base table for player
    match.data.players[id] = {}

    -- Tell the world the player joined if we're getting ready
    if match.state ~= STATE_PLAYING then
        player = Client:GetControllingPlayer()
        Shine:Print("Player %s joined the server, %s/%s players connected",
            true,
            player:GetName(),
            tablelength(match.data.players),
            match.size)
    end
    -- TODO: Assign player to team
end

-- Remove the player from match data, this is temporary and should be fixed later
function Plugin:ClientDisconnect(client)
    id = self:GetSteamID(client)
    if not id then return end

    if match.data.players[id] then
        match.data.players[id] = nil
    end

    -- TODO: start reconnect timer before cooldown
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
    if data and data.sessionid then
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

    -- If the player is banned, kick them
    -- TODO: send a request to the server, and track connects by banned players
    local data = json.decode(response)
    if data and data.active then
        local cli = Shine.GetClientBySteamID(data.id)
        local msg = string.format("You are banned from all NS2PUG servers: %s", data.reason)
        self:Kick(cli, msg)
    end
end

function Plugin:CheckBan(cli)
    request("bans/get", self:API_BansGet, "GET", {
        id: self:GetSteamId(cli)
    })
end

function Plugin:GetCommanders(gamerules)
    return gamerules.team1:GetCommander(), gamerules.team2:GetCommander()
end

-- TEST/TEMP FUNCTIONS
function Plugin:BuildTestMatch()
    match = {}
    match.id = 1
    match.size = 12 -- 6v6
    match.players = {"38683497": true}
    match.state = STATE_SETUP
    match.data = {
        players = {}
    }
end
