if (CTFd._internal.challenge) {
  var challenge = CTFd._internal.challenge;
} else {
  var challenge = window.challenge;
}

if (CTFd.lib.$) {
  $ = CTFd.lib.$;
}

if (!window.Moment) {
  Date.prototype.fromNow = function(){
    var date = this;
    var delta = Math.round((+new Date - date) / 1000);

    var minute = 60,
      hour = minute * 60,
      day = hour * 24,
      week = day * 7;

    var fuzzy;

    if (delta < 30) {
      fuzzy = 'just now';
    } else if (delta < minute) {
      fuzzy = delta + ' seconds ago.';
    } else if (delta < 2 * minute) {
      fuzzy = 'a minute ago'
    } else if (delta < hour) {
      fuzzy = Math.floor(delta / minute) + ' minutes ago';
    } else if (Math.floor(delta / hour) == 1) {
      fuzzy = '1 hour ago'
    } else if (delta < day) {
      fuzzy = Math.floor(delta / hour) + ' hours ago';
    } else if (delta < day * 2) {
      fuzzy = 'yesterday';
    }
    return fuzzy;
  }
  function Moment(d) {
    return new Date(d);
  }
}

function htmlEntities(string) {
  return $("<div/>")
    .text(string)
    .html();
}

challenge.data = undefined;

challenge.renderer = CTFd.lib.markdown();

challenge.preRender = function() {};

challenge.render = function(markdown) {
  return challenge.renderer.render(markdown);
};

challenge.postRender = function() {
  // Don't hijack the enter button
  $("#submission-input").unbind("keyup");

  var submission_template =
    '<div class="card bg-light mb-4">\
    <div class="card-body">\
        <blockquote class="blockquote mb-0">\
            <p>{0}</p>\
            <small class="text-muted">{1}</small>\
        </blockquote>\
    </div>\
  </div>';

  $(".nav-tabs a").click(function(e) {
    if ($(e.target).attr("href") === "#submissions") {
      // Populate Submissions
      var challenge_id = parseInt($("#challenge-id").val());
      var url = "/manual/submissions/" + challenge_id;

      CTFd.fetch(url, {
        method: "GET",
        credentials: "same-origin",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json"
        }
      })
        .then(function(response) {
          return response.json();
        })
        .then(function(response) {
          var correct = response["data"]["correct"];
          var pending = response["data"]["pending"];

          $("#challenge-submissions").empty();
          $("#challenge-submissions").append($("<br>"));
          $("#challenge-submissions").append($("<h3>Correct</h3>"));
          for (var index = 0; index < correct.length; index++) {
            var s = correct[index];
            var entry = $(
              submission_template.format(
                htmlEntities(s.provided),
                Moment(s.date).fromNow()
              )
            );
            $("#challenge-submissions").append(entry);
          }

          $("#challenge-submissions").append($("<br>"));
          $("#challenge-submissions").append($("<hr>"));
          $("#challenge-submissions").append($("<br>"));

          $("#challenge-submissions").append($("<h3>Pending</h3>"));
          for (var index = 0; index < pending.length; index++) {
            var s = pending[index];
            var entry = $(
              submission_template.format(
                htmlEntities(s.provided),
                Moment(s.date).fromNow()
              )
            );
            $("#challenge-submissions").append(entry);
          }
        });
    }
    $(this).tab("show");
  });
};

challenge.submit = function(cb, preview) {
  var challenge_id = parseInt($("#challenge-id").val());
  var submission = $("#submission-input").val();

  var body = {
    'challenge_id': challenge_id,
    'submission': submission,
  }
  var params = {}
  if (preview) {
    params['preview'] = true
  }

  var params = {
    challenge_id: challenge_id,
    submission: submission
  };

  return CTFd.api.post_challenge_attempt(params, body).then(function (response) {
    if (response.status === 429) {
      // User was ratelimited but process response
      return response
    }
    if (response.status === 403) {
      // User is not logged in or CTF is paused.
      return response
    }
    return response
  })
};
