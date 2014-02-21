var LobbyState = {
    LOBBY_STATE_CREATE: 1,
    LOBBY_STATE_IDLE: 2,
    LOBBY_STATE_SEARCH: 3,
    LOBBY_STATE_PLAY: 4,
    LOBBY_STATE_UNUSED: 5
}

var pug = {
    lobbyid: null,
    lobbypoll: 0,
    lobby: null,
    config: {},
    pollLobbyInterval: null,

    pushurl: function(url) {
        if (history) {
            history.pushState({}, '', url)
        }
    },

    msg: function(content, type, location, dismiss, cls) {
        var cls = cls ? cls : "";
        var dismiss = dismiss ? '<i class="icon-remove close" data-dismiss="alert"></i> ' : '';
        var alert = '<div style="text-align: center;" class="alert alert-'+type+' fade in '+cls+'">'+dismiss+content+'</div>';
        $(location).prepend(alert);
    },

    hidemsg: function(cls) {
        $("."+cls).remove();
    },

    vglobal: function() {
        var search_base = _.template('<li class="search-result"><a href="/user/<%= u.username %>"><div class="col-left">'+
                        '<span class="label label-info"><i class="icon-star"></i></span>'+
                        '</div><div class="col-right with-margin">'+
                        '<span class="message"><strong><%= u.username %></strong></span>'+
                        '<span class="time">32 Pugs Played</span></div></a> </li>')
        var search = function() {
            $(".search-result").remove()
            $.ajax("/api/users/search", {
                type: "POST",
                data: {
                    query: $("#search-input").val()
                },
                success: function (data) {
                    $(".sidebar-search-results").slideDown(200);
                    if (data.success) {
                        for (eid in data.results) {
                            $("#search-results").append(search_base({u: data.results[eid]}))
                        }
                    }
                }
            })
        }

        $('#search-submit').click(function(e) {
            e.preventDefault()
            search()
        })
        $('#search-input').keypress(function(e) {
            if(e.which == 13) {
                e.preventDefault();
                search()
            }
        });

        $(".sidebar-search-results .close").click(function () {
            $(".sidebar-search-results").slideUp(200)
        });
    },

    lobby: function (id) {
        pug.vglobal();
        pug.runGetStats();
        if (id) {
            pug.lobbyJoin(id);
        } else {
            $("#lobby").hide();
            $("#btn-create-lobby").click(pug.lobbyCreate);
        }
    },

    lobbyCreate: function(e) {
        // This should never happen unless people are firing manual events
        if (pug.lobbyid) {
            console.log("Wat. Da. Faq?");
            alert("Something went wrong! (Refresh the page?)");
            return
        }

        // Fade out the lobby creation wizard, and add in the loader
        $("#lobby-create-wizard").hide();
        $("#lobby-create-loader").fadeIn();

        // Function that handles error state
        var error = function (data) {
            var msg = data.msg ? data.msg : "Something went wrong!"
            // We hide the loader and reshow the wizard, in case its a user-correctabble
            //  error.
            $("#lobby-create-loader").hide();
            $("#lobby-create-wizard").show();
            pug.msg(msg, "danger", "#lobby-maker-main", false, "lobby-maker-err");
        }

        // Hide old errors
        pug.hidemsg("lobby-maker-err");

        // Make the request
        $.ajax("/api/lobby/create", {
            type: "POST",
            data: pug.config,
            success: function(data) {
                // Well dix, looks like we failed...
                if (!data.success) {
                    error(data);
                }
                // Hide loader
                $("#lobby-create-loader").hide();
                // Save lobby id, render
                pug.lobbyid = data.id;

                pug.pushurl(window.location+"/"+data.id)
                pug.lobbyRender(data);
            },
            error: error
        })
    },

    lobbyPollStart: function(first) {
        clearInterval(pug.pollLobbyInterval);
        pug.pollLobbyInterval = setInterval(pug.pollLobby, 1000 * 2.5);
        pug.pollLobby(first)
    },

    lobbyJoin: function(id) {
        if (!pug.lobbyid) {
            pug.lobbyid = id;
        }
        pug.lobbyPollStart(true);

        $.ajax("/api/lobby/info", {
            data: {
                id: pug.lobbyid
            },
            success: function (data) {
                if  (data.success) {
                    pug.lobby = data.lobby
                    pug.lobbyRender()
                }
            }
        });
        
    },

    lobbyMemberTemplate: _.template('<tr id="member-<%= m.id %>"><td><%= m.username %>'+
        '<% if (leader) { %><span class="label label-danger lobby-kick">X</span><% } %></td></tr>'),

    lobbyAddMember: function(m) {
        var isLeader = (USER.id == pug.lobby.owner)
        $("#lobby-member-list").append(pug.lobbyMemberTemplate({m: m, leader: isLeader}));
    },

    lobbyRmvMember: function(id) {
        $("#member-"+id).remove();
    },

    lobbyRender: function() {
        $("#lobby-maker").hide();
        $("#lobby").show();
        $("#lobby-chat-list").slimScroll({
            height: '350px',
            start: 'bottom',
        });

        if (pug.lobby.owner != USER.id) {
            $(".not-owner").show()
        } else {
            $(".owner").show()
        }

        $.each(pug.lobby.members, function(_, v) {
           pug.lobbyAddMember(v)
        })

        $("#lobby-queue-start").click(function () {
            $.ajax("/api/lobby/action", {
                type: "POST",
                data: {
                    id: pug.lobbyid,
                    action: "start"
                },
                success: pug.lobbyPollStart
            })
        });
        $("#lobby-queue-stop").click(function () {
            $.ajax("/api/lobby/action", {
                type: "POST",
                data: {
                    id: pug.lobbyid,
                    action: "stop"
                },
                success: pug.lobbyPollStart
            })
        });

        $("#lobby-leave").click(function () {
            $.ajax("/api/lobby/action", {
                type: "POST",
                data: {
                    id: pug.lobbyid,
                    action: "leave"
                },
                success: function (data) {
                    if (data.success) {
                        window.location = '/'
                    }
                }
            })
        })

        // The following handles sending chat messages
        var send_lobby_chat = function () {
            var msg = $("#lobby-chat-text").val();
            $.ajax("/api/lobby/chat", {
                type: "POST",
                data: {
                    id: pug.lobbyid,
                    msg: msg
                },
                success: function(data) {
                    if (data.success) {
                        $("#lobby-chat-text").val("");
                        pug.lobbyAddChat(USER.name, msg, true)
                    } else {
                        console.log(data.msg)
                    }
                }
            })
        }
        // Bind send button
        $("#lobby-chat-send").click(send_lobby_chat)
        // Bind the enter key
        $('#lobby-chat-text').keypress(function(e) {
            if(e.which == 13) {
                send_lobby_chat();
            }
        });
        pug.lobbyHandleState(pug.lobby.state)

        $("#lobby-invite-btn").click(function () {
            $("#invite-modal").modal('show')
        })
    },

    lobbyHandleState: function(state) {
        switch (state) {
            case LobbyState.LOBBY_STATE_CREATE:
            case LobbyState.LOBBY_STATE_IDLE:
            case LobbyState.LOBBY_STATE_UNUSED:
                $("#lobby-info-main-queued").hide();
                $("#lobby-info-main-waiting").show();
                break;
            case LobbyState.LOBBY_STATE_SEARCH:
                $("#lobby-info-main-queued").show();
                $("#lobby-info-main-waiting").hide();
                break;
        }
    },

    lobbyAddChat: function(from, msg, adjust) {
        $("#lobby-chat-list").append('<li class="list-group-item basic-alert"><b>'+from+':</b> '+msg+'</li>')
        if (adjust) { $("#lobby-chat-list").animate({ scrollTop: $('#lobby-chat-list')[0].scrollHeight}, 700);}
    },

    lobbyAddAction: function(text, color, adjust) {
        var extra = color ? ' class="text-'+color+'" ' : ''
        $("#lobby-chat-list").append('<li class="list-group-item basic-alert"><i'+extra+'>'+text+'</i></li>')
        if (adjust) { $("#lobby-chat-list").animate({ scrollTop: $('#lobby-chat-list')[0].scrollHeight}, 700);}
    },

    pollLobby: function(first) {
        first = (first == true)
        $.ajax("/api/lobby/poll", {
            data: {
                id: pug.lobbyid,
                last: pug.lobbypoll
            },
            success: function(data) {
                if (data.success) {
                    pug.lobbypoll += data.size

                    for (mi in data.data) {
                        m = data.data[mi]
                        if (m.type === "chat" && (m.id != USER.id || first)) {
                            pug.lobbyAddChat(m.from, m.msg)
                        } else if ((m.type === "join" || m.type === "quit") && !first){
                            pug.lobbyAddAction(m.msg, "success", !first);
                            if (m.type == "join") { pug.lobbyAddMember(m.member); }
                            if (m.type == "quit") { pug.lobbyRmvMember(m.member.id); }
                        } else if (m.type == "state") {
                            if (!first) { pug.lobbyHandleState(m.state); }
                            pug.lobbyAddAction(m.msg, "warning", !first);
                        } else if (m.type == "msg") {
                            pug.lobbyAddAction(m.msg, "danger", !first);
                        } else if (m.type == "timeout") {
                            pug.lobbyRmvMember(m.member.id);
                            pug.lobbyAddAction(m.msg, "danger", !first);
                        }
                    }

                    if (first) { $("#lobby-chat-list").animate({ scrollTop: $('#lobby-chat-list')[0].scrollHeight}, 700);}
                }
            }
        })
    },

    // Loads inital stats and queues for refresh
    runGetStats: function() {
        pug.getStats();
        setInterval(pug.getStats, 1000 * 15);
    },

    // Loads stats from the backend and dynamically loads them into values
    getStats: function () {
        $.ajax("/api/stats", {
            success: function (data) {
                $(".apistats").each(function (_, i) {
                    var id = $(i).attr("id").split(".")
                    var base = data;
                    for (get in id) {
                        base = base[id[get]]
                    }
                    $(i).text(base)
                })
            }
        })
    },

    friends: function() {
        pug.vglobal();
        $(".friends-unfriend").click(function (e) {
            console.log($($(this).parent()).attr("id"))
            console.log($(this))
            $.ajax("/api/users/unfriend", {
                type: "POST",
                data: {
                    id: $(this).attr("id")
                },
                success: function (data) {
                    if (data.success) {
                        // FIXME
                        $($(this).parent()).remove()
                        pug.msg("Removed friend!", "success", "#friends-main", true)
                    }
                }
            });
        });

        $(".friends-deny").click(function (e) {
            $.ajax("/api/invites/deny", {
                type: "POST",
                data: {
                    id: $(this).attr("id")
                },
                success: function (data) {
                    if (dat.success) {
                        // FIXME
                        $($(this).parent()).remove()
                        pug.msg("Denied Friend Invite!", "warning", "#friends-main", true)
                    }
                }
            })
        });

        $(".friends-accept").click(function (e) {
            $.ajax("/api/invites/accept", {
                type: "POST",
                data: {
                    id: $(this).attr("id")
                },
                success: function (data) {
                    if (dat.success) {
                        // FIXME
                        $($(this).parent()).remove()
                        pug.msg("Accepted Friend Invite!", "success", "#friends-main", true)
                    }
                }
            })
        });
    }
}

$(document).ready(function () {

});