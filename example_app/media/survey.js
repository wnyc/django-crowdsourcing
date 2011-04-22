var googleMapCallbacks = [];
var yahooChartCallbacks = [];
var googleMapAPILoaded = false;
var yahooChartAPILoaded = false;
function loadMapsAndCharts() {
  /* We don't want to necessarily load the google map and yahoo chart APIs on
   * every page. Luckily, both APIs provide a mechanism for lazy loading.
   * The crowdsourcing maps and charts register the code they need to run in
   * googleMapCallbacks and yahooChartCallbacks. This gives loadMapsAndCharts
   * a chance to load the APIs before attempting to load any charts or maps. */
  if (googleMapCallbacks.length) {
    var onAPILoaded = function() {
      while (googleMapCallbacks.length) {
        googleMapCallbacks.pop()();
      }
      $(window).unload(GUnload);
    };
    if (!googleMapAPILoaded) {
      google.load("maps", "2", {callback: onAPILoaded});
      googleMapAPILoaded = true;
    } else {
      onAPILoaded();
    }
  }
  if (yahooChartCallbacks.length) {
    var onAPILoaded = function() {
      while (yahooChartCallbacks.length) {
        yahooChartCallbacks.pop()();
      }
    };
    if (!yahooChartAPILoaded) {
      var loader = new YAHOO.util.YUILoader({
        require: ["charts"],
        onSuccess: onAPILoaded,
        combine: true
      });
      loader.insert();
    } else {
      onAPILoaded();
    }
  }
}

var commentToggles = {};
function toggleComments(id) {
  var div = $("#" + id);
  if (commentToggles[id]) {
    div.hide("slow");
  } else {
    div.show("slow");
  }
  commentToggles[id] = !commentToggles[id];
  return false;
}

function loadSurvey(slug, elementId) {
  $(document).ready(function() {
    var url = "/crowdsourcing/" + slug + "/api/allowed_actions/";
    $.getJSON(url, function(data, status) {
      loadSurveyForm(slug,
                     elementId,
                     !data["enter"],
                     data["view"],
                     data["open"],
                     data["need_login"]);
    });
  });
}

function loadSurveyForm(slug, elementId, cantEnter, canView, open, needLogin) {
  var url = "/crowdsourcing/" + slug + "/api/questions/";

  $.getJSON(url, function(survey, status) {
    var isChoiceType = false;
    var types = {choice: 0, select: 0, numeric_select: 0, numeric_choice: 0};
    for (var type in types) {
      isChoiceType = isChoiceType || survey.questions[0].option_type == type;
    }
    var isPoll = survey.questions.length == 1 && isChoiceType;
    var wrapper = initializeWrapper(elementId, isPoll ? "poll" : "survey");
    var beforeWrapper = function(text, element) {
      if (text) {
        wrapper.before(element.html(text));
      }
    };
    beforeWrapper(survey.title, $("<h3/>"));
    var description = survey.description || survey.tease;
    if (description) {
      beforeWrapper(description, $("<p/>").addClass("subtitle"));
    }
    var form = $("<form/>").attr("method", "POST");
    form.attr("action", survey.submit_url);
    form.addClass(isPoll ? "vote" : "survey").appendTo(wrapper);
    tease = $('#' + elementId).parent().parent();
    if (tease.attr('class') == 'tease') {
      tease.children().eq(0).hide();
    }

    var div = $("<div/>").attr("id", "inner_" + slug).appendTo(form);
    if (cantEnter) {
      // I didn't use if (needLogin) or if (open) for backwards compatibility.
      if (needLogin == true) {
        div.text("You must login to enter this survey.");
      } else if (open == true) {
        div.text("You've already entered this survey.");
      } else {
        div.text("This survey isn't open yet.");
      }
    } else {
      if (isPoll) {
        var question = survey.questions[0];
        $("<h2/>").html(question.question).appendTo(div);
        appendChoiceButtons(survey, question, div);
      } else {
        $.get(survey.submit_url, queryParametersAsLookup(), function(results, textStatus) {
          var err = "Crowdsourcing encountered and error. Sorry about that!";
          form.html("success" == textStatus ? results : err);
        });
      }
    }
    form.ajaxForm({beforeSubmit: function() {
      form.find("input[type='submit']").attr("value", "Submitting...").attr("disabled", true);
      return true;
    }, success: function(responseText) {
      form.html(responseText);
    }});
    if (canView) {
      appendSeeResults(wrapper, survey);
    }
  });
}

function loadSurveyResults(surveySlug, reportSlug, elementId) {
  var url = "/crowdsourcing/" + surveySlug + "/api/report/";
  if (reportSlug) {
    url += reportSlug + "/";
  }
  $.get(url, queryParametersAsLookup(), function(results, textStatus) {
    var wrapper = $("#" + elementId);
    if ("success" == textStatus) {
      wrapper.html(results);
      initEnlargeable(wrapper);
    } else {
      wrapper.html("The reports appear to be broken. Sorry about that! " +
                   "<input type='hidden' value='" + textStatus + "' />");
    }
  });
}

function setNameAndId(element, survey, question) {
  element.attr("id", questionId(survey, question));
  element.attr("name", questionName(survey, question));
}

function appendChoiceButtons(survey, question, wrapper) {
  var answerInput = $("<input type='hidden' />").appendTo(wrapper);
  answerInput.attr("name", questionName(survey, question));
  var ul = $("<ul class='voteList clearfix' />").appendTo(wrapper);
  for (var i = 0; i < question.options.length; i++) {
    var answer = question.options[i];
    var li = $("<li/>").appendTo(ul);
    var css = {cursor: "pointer"};
    var a = $("<a/>").attr("href", "#").css(css).html(answer);
    a.appendTo(li).click(function(evt) {
      evt.preventDefault();
      var a = $(this); // Necessary. Review closures if you don't understand.
      // crowdsourcing.forms.BaseOptionAnswer.__init__ duplicates this.
      var value = a.text().replace(/&amp;/g, "&").replace(/"/g, "'").trim();
      answerInput.attr("value", value);
      a.parents("form").submit();
    }).mouseover(function() {
      $(this).addClass('surveyRoll');
      $(this).parent().addClass('surveyRoll');
    }).mouseout(function() {
      $(this).removeClass('surveyRoll');
      $(this).parent().removeClass('surveyRoll');
    });
  }
}

function questionName(survey, question) {
  return survey.id + "_" + question["cms_id"] + "-answer";
}

function questionId(survey, question) {
  return "id_" + questionName(survey, question);
}

function appendSeeResults(appendTo, survey) {
  var a = $("<a/>").text("See Results");
  a.attr("href", survey.report_url);
  $("<p/>").addClass("results").appendTo(appendTo).append(a);
}

function initializeWrapper(elementId, wrapperClass) {
  var wrapper = $("#" + elementId);
  wrapper.empty().addClass("clearfix").addClass("survey_wrapper");
  wrapper.wrap('<div class="' + wrapperClass + '" />');
  return wrapper;
}

function initEnlargeable(parent) {
  parent.find("input:hidden.enlargeable").each(function() {
    if ($(this).attr("data-initted") == "true") {
      return;
    } else {
      $(this).attr("data-initted", "true");
    }
    var url = $(this).attr("value");
    var id = $(this).attr("id").match(/(img_\d+)_full_url/)[1];
    var img = $("#" + id);
    var div = $("<div/>").addClass("enlarge_div");
    var height = img.outerHeight();
    var width = img.outerWidth();
    if (height && width) {
      var css = {height: img.outerHeight(), width: img.outerWidth()};
      div.css(css);
    }
    var makeA = function() {
      return $("<a/>").attr("href", "#").appendTo(div).click(function(e) {
        e.preventDefault();
        enlargeImage(id, url);
      });
    }
    var a_outer = makeA();
    var a_inner = makeA().addClass("enlarge_link").text("Enlarge");
    img.replaceWith(div);
    a_outer.append(img)
  });
}

$(function() {
  initEnlargeable($("body"));
});

/* Almost identical to parametersFromQuery in main.js, but used by
 * the crowdsourcing sample app, so we need 2 copies. */
function queryParametersAsLookup() {
  query = window.location.search.replace("?", "");
  var hashParts = query.split("&");
  var variables = {};
  // Twitter's widget.js breaks this: for (var i in hashParts)
  for (var i = 0; i < hashParts.length; i++) {
    var subParts = hashParts[i].split("=");
    if (subParts.length > 1 && subParts[1].length) {
      variables[unescape(subParts[0])] = unescape(subParts[1]);
    }
  }
  return variables;
}
