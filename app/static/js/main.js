var pug = {
    lobbyid: null,
    lobbypoll: 0,
    config: {},

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

    lobby: function (id) {
        this.runGetStats();
        if (id) {
            this.joinLobby(id);
        } else {
            $("#lobby").hide();
            $("#btn-create-lobby").click(this.createLobby);
        }
    },

    createLobby: function(e) {
        // This should never happen unless people are firing manual events
        if (pug.id) {
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
                pug.renderLobby();
            },
            error: error
        })
    },

    lobbyPollStart: function() {
        clearTimeout(this.pollLobby);
        setTimeout(this.pollLobby, 1000 * 5);
        this.pollLobby()
    },

    joinLobby: function(id) {
        if (!pug.lobbyid) {
            pug.lobbyid = id
            // TODO: join lobby
        }
        pug.lobbyPollStart()
        pug.renderLobby();
        
    },

    renderLobby: function() {
        $("#lobby-maker").hide();
        $("#lobby").show();
        $("#lobby-chat-list").slimScroll({
            height: '350px'
        });
        $("#lobby-chat-send").click()
        var send_lobby_chat = function () {
            $.ajax("/api/lobby/chat", {
                data: {
                    id: pug.lobbyid,
                    msg: $("#lobby-chat-text").val()
                },
                success: function(data) {
                    if (data.success) {
                        $("#lobby-chat-text").val("");
                        // FIXME
                        pug.lobbyPollStart()
                    } else {
                        console.log(data.msg)
                    }
                }
            })
        }
        $("#lobby-chat-send").click(send_lobby_chat)
        $('#lobby-chat-text').keypress(function(e) {
            if(e.which == 13) {
                send_lobby_chat();
            }
        });
    },

    lobbyAddChat: function(from, msg) {
        $("#lobby-chat-list").append('<li class="list-group-item basic-alert"><b>'+from+':</b> '+msg+'</li>')
    },

    pollLobby: function() {
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
                        if (m.type === "chat") {
                            pug.lobbyAddChat(m.from, m.msg)
                        }
                    }
                }
            }
        })
    },

    // Loads inital stats and queues for refresh
    runGetStats: function() {
        pug.getStats();
        setTimeout(pug.getStats, 1000 * 5);
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
    }
}

$(document).ready(function () {

});