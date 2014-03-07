- Match is created, server is set
- Push match information to wrapper (over redis), includes map, players
- Wrapper starts new server passing in allowed players


## Match
{
    "id": 1,
    "players": "1234,4321,5678,8765",
    "map": "de_dust2"
}