/* @author Dave Aaron Smith dasmith2@gmail.com
 *
 * This script contains the tools for enlarging images on a page using a 
 * light box, or modal window if you will. This script requires enlarge.css. */

/* It's a challenge to share the useful www.wnyc.org code with crowdsourcing
 * while at the same time not bogging crowdsourcing down with too many
 * www.wnyc.org specific details. Of course I could just make multiple
 * copies of this function, but that's even more painful, and makes me more
 * likely to release broken code with the crowdsourcing sample app. Hence, here
 * in particular, forgive the www.wnyc.org bits that bleed in: isExternal,
 * strippedHtml, credits, and credits_url. */
function enlargeImage(img_id, url, credits, credits_url) {
  if (!credits) {
    credits = "";
  }
  if (!credits_url) {
    credits_url = "";
  }
  var img = $("#" + img_id);

  var background = $("<div/>").appendTo($("body")).attr("id", "enlarge_bg");
  background.css("opacity", 0.5).click(hideEnlarge);
  var enlarge = $("<div/>").attr("id", "enlarge").appendTo($("body")).hide();
  var close1 = $("<div/>").addClass("close").append($("<a/>").html("Close"));
  close1.click(hideEnlarge);
  enlarge.append(close1);
  var imgElement = $("<img/>").appendTo($("<div/>").addClass("image"));
  imgElement.appendTo(enlarge).click(hideEnlarge);
  var loading = $("<div/>").addClass("loading").html("Loading...");
  loading.appendTo(enlarge);
  var imgCaption = $("<div/>").addClass("caption").appendTo(enlarge);
  var imgCredits = $("<div/>").addClass("credit").appendTo(enlarge);

  var caption = img.attr("title");
  imgCaption.text(caption);
  imgCaption.hide(); /* Caption shown after image width determined */
  var strippedHtml = function(element, credits) {
    if ("undefined" != typeof element.strippedHtml) {
      element.strippedHtml(credits);
    } else {
      element.text(credits);
    }
    return element;
  };
  if (credits_url) {
    var a = $("<a/>").attr("href", credits_url);
    if ("undefined" != typeof isExternal && isExternal(credits_url)) {
      a.attr("target", "_blank");
    }
    imgCredits.append(strippedHtml(a, credits));
  } else {
    strippedHtml(imgCredits, credits);
  }
  if (credits) {
    imgCredits.show();
  } else {
    imgCredits.hide();
  }
  var top = $(window).scrollTop() + 10;
  enlarge.css({top: top});
  loading.width("").height("").show();
  imgElement.css({position: "absolute", top: 0, left: -9999});
  imgElement.attr("title", caption).attr("alt", img.attr("alt"));
  enlarge.show();
  setEnlargeLeft(enlarge.outerWidth(), 0);
  imgLoaded = false;
  // <embed /> tags float above the popup divs.
  $("embed").css("visibility", "hidden");
  /* If the image has to load, then just the next line is necessary. Now, in
   * Chrome the image does not need to load at all the second time, so the
   * load event doesn't fire. In IE8, I've observed the load event just not
   * firing. Hence, call imgLoad right away, and call it periodically until our
   * image is finally loaded. */
  imgElement.load(imgLoad).attr("src", url);
  repeatImgLoad();
}

function setEnlargeLeft(enlargeWidth, animateTime) {
  var left = ($(window).width() - enlargeWidth) / 2;
  $("#enlarge").animate({left: left}, animateTime);
}

function hideEnlarge() {
  $("#enlarge_bg").detach();
  $("#enlarge").detach();
  $("embed").css("visibility", "visible");
}

var imgLoaded = false;
function imgLoad() {
  var animateTime = 250;
  var imgElement = $("#enlarge img");
  var enlarge = $("#enlarge");
  var loading = $("#enlarge .loading");
  var imgCaption = $("#enlarge .caption");

  if (!imgLoaded && imgElement[0].complete) {
    imgLoaded = true;
    imgCaption.show();
    var enlargeWidth = imgElement.outerWidth() + edgeWidth(enlarge);
    setEnlargeLeft(enlargeWidth, animateTime);
    var attrs = {width: imgElement.width(), height: imgElement.height()};
    loading.animate(attrs, animateTime, "linear", function() {
      loading.hide();
      imgElement.css({position: "static"});
    });
  }
}

function edgeWidth(element) {
  var returnValue = 0;
  for (attribute in {"margin": "", "padding": ""}) {
    for (direction in {"right": "", "left": ""}) {
      var att = attribute + "-" + direction;
      var value = parseInt(element.css(att).replace("px", ""));
      returnValue += value ? value : 0;
    }
  }
  return returnValue;
}

function repeatImgLoad() {
  if (!imgLoaded) {
    imgLoad();
    window.setTimeout(repeatImgLoad, 100);
  }
}
