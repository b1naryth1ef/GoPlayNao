// (function () {

// var original = document.title;
// var timeout;

// window.flashTitle = function (newMsg, howManyTimes) {
//     original = document.title;
//     function step() {
//         document.title = (document.title == original) ? newMsg : original;

//         if (--howManyTimes > 0) {
//             timeout = setTimeout(step, 1000);
//         };
//     };

//     howManyTimes = parseInt(howManyTimes);

//     if (isNaN(howManyTimes)) {
//         howManyTimes = 5;
//     };

//     cancelFlashTitle(timeout);
//     step();
// };

// window.cancelFlashTitle = function () {
//     clearTimeout(timeout);
//     document.title = original;
// };

// }());

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

