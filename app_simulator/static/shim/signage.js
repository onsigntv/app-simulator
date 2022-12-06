(function () {
  var source = null;
  function createSource() {
    if (source) source.close();
    source = new EventSource("/.change_notification");
    source.onmessage = function () {
      var formEl = document.createElement("form");
      formEl.method = "POST";
      formEl.enctype = "multipart/form-data";
      for (var [key, val] of Object.entries(window.__appFormData)) {
        var i = document.createElement("input");
        i.hidden = true;
        i.name = key;
        i.value = val;
        formEl.appendChild(i);
      }
      document.body.appendChild(formEl);
      formEl.requestSubmit();
    };
    source.onerror = function () {
      window.setTimeout(createSource, 1000);
    };
  }
  createSource();

  if (window.__appFormData["_proxy_requests"]) {
    var origOpen = window.XMLHttpRequest.prototype.open;
    window.XMLHttpRequest.prototype.open = function () {
      arguments[1] = "/.proxy_request?url=" + encodeURIComponent(arguments[1]);
      return origOpen.apply(this, arguments);
    };
    var origFetch = window.fetch;
    if (origFetch) {
      window.fetch = function (resource, options) {
        if (Object.getPrototypeOf(resource) === Request.prototype) {
          resource = new Request(resource, { url: "/.proxy_request?url=" + encodeURIComponent(resource.url) });
        } else {
          resource = "/.proxy_request?url=" + encodeURIComponent(resource);
        }
        return origFetch(resource, options);
      };
    }
  }

  var prevWidth = null;
  var prevHeight = null;
  var resizeTimer = null;

  function dispatch(name, props, target) {
    var customEvent = document.createEvent("HTMLEvents");
    customEvent.initEvent(name, true, false);
    if (typeof props === "object") {
      for (var key in props) {
        customEvent[key] = props[key];
      }
    }
    if (!target) target = document;
    target.dispatchEvent(customEvent);
  }

  function dispatchSize() {
    if (window.innerWidth !== prevWidth || window.innerHeight !== prevHeight) {
      dispatch("sizechanged", { detail: { width: window.innerWidth, height: window.innerHeight } });
      prevWidth = window.innerWidth;
      prevHeight = window.innerHeight;
    }
  }

  window.addEventListener("DOMContentLoaded", dispatchSize);
  window.addEventListener("load", dispatchSize);
  window.addEventListener("resize", function () {
    if (resizeTimer) window.clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(dispatchSize, 250);
  });

  window.signageLoaded = new Promise(function (resolve) {
    document.addEventListener("signageloaded", function () {
      resolve();
    });
  });
  window.signageVisible = new Promise(function (resolve) {
    document.addEventListener("show", function () {
      resolve();
    });
  });

  var playbackInfo = {};
  try {
    playbackInfo = JSON.parse(window.__appFormData["_playback_info"]) || {};
  } catch (e) {
    /* noop */
  }

  var internalTarget = document.createElement("div");
  var brightness = 100;
  var volume = 100;
  var signage = {
    addEventListener: function () {
      internalTarget.addEventListener.apply(internalTarget, arguments);
    },
    getBrightness: function () {
      return brightness;
    },
    getCurrentPosition: function () {
      return JSON.stringify({
        coords: {
          accuracy: null,
          altitude: null,
          altitudeAccuracy: null,
          heading: null,
          latitude: 43.01256284360166,
          longitude: -89.44531987692744,
          speed: null,
        },
        timestamp: Date.now(),
      });
    },
    getGeoLocation: function () {
      return new Promise((resolve, reject) => {
        if (navigator.geolocation) {
          navigator.geolocation.getCurrentPosition((pos) => {
            resolve({ src: "ip", lat: pos.coords.latitude, lng: pos.coords.longitude });
          });
        } else {
          reject("Could not get geo location");
        }
      });
    },
    getPlayerAttribute: function (name) {
      var attr;
      try {
        if (name === "__tags__") {
          attr = playbackInfo.player.tags;
        } else {
          attr = playbackInfo.player.attrs[name];
        }
      } catch (e) {}

      return attr === undefined ? null : attr;
    },
    getVolume: function () {
      return volume;
    },
    height: function () {
      return window.innerHeight;
    },
    isVisible: function () {
      return true;
    },
    ledOff: function () {},
    ledOn: function (red, green, blue) {},
    log: function (level, domain, message) {
      console.log("LOG ENTRY", { level: level, domain: domain, message: message });
    },
    playAudio: function (uri) {
      var audio = new Audio(uri);
      audio.play().catch(function (error) {
        console.log("Error playing audio: ", error);
      });
    },
    playbackInfo: function () {
      return JSON.stringify(playbackInfo);
    },
    removeEventListener: function () {
      internalTarget.removeEventListener.apply(internalTarget, arguments);
    },
    sendEvent: function (level, code, message, extra) {
      console.log("SENT EVENT", { level: level, code: code, message: message, extra: extra });
    },
    setBrightness: function (percent) {
      var value = parseInt(percent, 10);
      if (!isNaN(value)) {
        brightness = Math.min(Math.max(value, 0), 100);
      }
      window.setTimeout(function () {
        dispatch("propchanged", { detail: { name: "brightness", value: brightness } }, internalTarget);
      }, 100);
    },
    setPlayerAttribute: function (name, value) {
      try {
        if (name === "__tags__") {
          playbackInfo.player.tags = value;
        } else {
          playbackInfo.player.attrs[name] = value;
        }
      } catch (ex) {
        console.log("Error setting player attribute: ", ex);
      }
    },
    setVolume: function (percent) {
      var value = parseInt(percent);
      if (!isNaN(value)) {
        volume = Math.min(Math.max(value, 0), 100);
      }
      window.setTimeout(function () {
        dispatch("propchanged", { detail: { name: "volume", value: volume } }, internalTarget);
      }, 100);
    },
    stopCurrentCampaign: function () {
      window.alert("App would be stopped right now.");
    },
    stopThisItem: function (delay, stopParentCampaign, isPartialPlayback) {
      window.setTimeout(signage.stopCurrentCampaign, delay);
    },
    triggerInteractivity: function (value, params) {
      window.alert("Would trigger interactivity " + value + " with Local API.");
    },
    width: function () {
      return window.innerWidth;
    },
  };

  document.addEventListener("DOMContentLoaded", function () {
    document.title = "\uD83D\uDED1 Preloading... | " + document.title;
  });
  window.addEventListener("load", function () {
    window.setTimeout(function () {
      window.signage = signage;
      dispatch("signageloaded");
      window.setTimeout(
        function () {
          document.title = "\uD83D\uDFE2 Visible | " + document.title.substring(document.title.indexOf("|") + 2);
          dispatch("show");
        },
        window.__appFormData._delay_show ? 3000 : 10
      );
    }, 10);
  });
})();
