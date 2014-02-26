- Wrapper registers with backend
- Wrapper polls for match
- Wrapper starts server w/ arguments
    - Match ID
    - Clients (String "steamid,steamid,steamid,steamid")

PACKETS:
0 - "Welcome" passes serverid,  serverhash, and matchid (should be 0 on new, 0< on reentrant)