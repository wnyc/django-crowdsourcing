var latestMap = null;
function setupMap(
    div_id,
    details_id,
    results_url,
    center_lat,
    center_lng,
    zoom) {
  var onAPILoaded = function() {
    if (GBrowserIsCompatible()) {
      $(function() {
        var params = queryParametersAsLookup();
        $.getJSON(results_url, params, function(data, status) {
          if (status != "success") {
            $("#" + div_id).html("The crowdsourcing API is experiencing "
              + "problems. It returned status " + status + ".");
            return;
          }
          if (!data.entries.length) {
            $("#" + div_id).html("There aren't any locations to show on "
              + "this map, but as soon as we get some we'll put a map here.");
            return;
          }
          var map = initializeMap(div_id, data, center_lat, center_lng, zoom);
          latestMap = map;
          var createClickClosure = function(url) {
            return function() {
              showSubmission(url, div_id, details_id); 
            };
          };
          for (entry_i in data.entries) {
            var entry = data.entries[entry_i];
            var icon = G_DEFAULT_ICON;
            if (entry.icon) {
              icon = new GIcon(G_DEFAULT_ICON, entry.icon);
            }
            var marker = new GMarker(new GLatLng(entry.lat, entry.lng), icon);
            map.addOverlay(marker);
            createClickClosure(marker, entry.url);
            GEvent.addListener(marker, "click", createClickClosure(entry.url));
          }
        });
      });
    } else {
      $("#" + div_id).html("Sorry! Your browser doesn't support Google Maps.");
    }
  }
  googleMapCallbacks.push(onAPILoaded);
}

function showSubmission(url, div_id, details_id) {
  var img = '<img class="loading" src="/media/img/loading.gif" ' +
      'alt="loading" />';
  var details = $("#" + details_id);
  details.html(img);
  var offset = $("#" + div_id).offset;
  details.fadeIn();
  $.get(url, function(results) {
    var get_close = function(css) {
      var div = $("<div />").addClass(css);
      $("<a />").text("Close").click(function(event) {
        event.preventDefault();
        details.hide();
      }).attr("href", "#").appendTo(div);
      return div;
    }
    details.empty();
    details.append(get_close("top_close"));
    $(results).appendTo(details);
    details.append(get_close("bottom_close"));
    initEnlargeable(details);
  });
}

function initializeMap(div_id, data, center_lat, center_lng, zoom) {
  var map = new GMap2(document.getElementById(div_id));
  if (null != center_lat && null != center_lng) {
    var center = new GLatLng(center_lat, center_lng);
  } else {
    var corners = minMaxLatLong(data.entries);
    var center = new GLatLng((corners[0] + corners[2]) / 2,
                             (corners[1] + corners[3]) / 2);
  }
  var use_zoom = 13;
  if (null != zoom) {
    use_zoom = zoom;
  }
  map.setCenter(center, use_zoom);
  map.setUIToDefault();
  if (null == zoom) {
    setZoom(map, data.entries)
  }
  return map;
}

function setZoom(map, entries) {
  var corners = minMaxLatLong(entries);
  var lower = new GLatLng(corners[0], corners[1]);
  var upper = new GLatLng(corners[2], corners[3]);
  bounds = new GLatLngBounds(lower, upper);
  map.setZoom(map.getBoundsZoomLevel(bounds));
}

function minMaxLatLong(entries) {
  var max_lat = max_long = -91.0;
  var min_lat = min_long = 91.0;
  for (entry_i in entries) {
    var entry = entries[entry_i];
    min_lat = entry.lat < min_lat ? entry.lat : min_lat;
    min_long = entry.lng < min_long ? entry.lng : min_long;
    max_lat = entry.lat > max_lat ? entry.lat : max_lat;
    max_long = entry.lng > max_long ? entry.lng : max_long;
  }
  return [min_lat, min_long, max_lat, max_long];
}

function setupMapEmbed() {
  $(".map_embed_link").each(function() {
    var wrapper = $(this).parents(".google_map_wrapper");
    var click = function(event) {
      event.preventDefault();
      wrapper.find("fieldset").toggle();
    };
    $(this).click(click);
    wrapper.find(".close-map-button").click(click);
    wrapper.find("textarea").click(function() {
      this.select();
    });
  });
}

$(setupMapEmbed);
