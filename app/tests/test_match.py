import sys

sys.path.append("../")

from database import *

lobbyid = int(sys.argv[1])
lobby = Lobby.get(Lobby.id == lobbyid)
lobby.state = LobbyState.LOBBY_STATE_PLAY
lobby.save()

m = Match()
m.lobbies = [lobbyid]
m.teama = [lobbyid]
m.teamb = []
m.config = {}
m.server = Server.get(Server.id == 1)
m.state = MatchState.MATCH_STATE_SETUP
m.mapp = Map.get(Map.name == "de_nuke")
m.save()
m.cleanup()
m.server.setup(m)

