
function flashTitle(text) {
    var timer,
        original = document.title

    $(window).blur(function () {
        timer = setInterval(function() {
            var val = $('title').text() == original ? text : original;
            $('title').text(val);
        }, 1000)
    })

    $(window).focus(function() {
        clearInterval(timer)
        document.title = original;
    })
}
