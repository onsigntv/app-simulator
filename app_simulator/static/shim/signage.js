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
          resource = new Request(resource, {
            url: "/.proxy_request?url=" + encodeURIComponent(resource.url),
          });
        } else {
          resource = "/.proxy_request?url=" + encodeURIComponent(resource);
        }
        return origFetch(resource, options);
      };
    }
  }

  var toastTimer = null;
  var toastArea = null;
  var toastMsgs = [];
  var toast = null;
  function addNotification(msg) {
    if (toastTimer) clearTimeout(toastTimer);

    toastTimer = setTimeout(function () {
      function fadeToast(op) {
        if (toastTimer) {
          /* Check if a new attr has been set while the toast is fading
          away, if so, the fading must stop. */
          toastArea.style.opacity = "0.7";
        } else if (op >= 0) {
          toastArea.style.opacity = parseFloat(op / 100);
          setTimeout(function () {
            fadeToast(op - 1);
          }, 10);
        } else {
          toastArea.remove();
          toastArea = null;
        }
      }

      toastTimer = null;
      fadeToast(70);
    }, 5000);

    var textSpan = document.createElement("span");
    textSpan.style = "display: flex;flex-direction: column;max-width: 100%;margin: 3px auto";
    textSpan.innerText = msg;
    console.log(msg);

    toastMsgs.push(textSpan);
    if (toastMsgs.length > 10) {
      toastMsgs[0].remove();
      toastMsgs.splice(0, 1);
    }

    if (!toastArea) {
      toastArea = document.createElement("div");
      toastArea.style =
        "position: fixed;left: 0;right: 0;display: flex;justify-content: center;align-items: center;z-index: 1000000;opacity:0.7;";

      toast = document.createElement("div");
      toast.style =
        "position: fixed;bottom: 10%;background-color: black;color: white;border-radius: 30px;padding: 8px 20px;text-align: center;font-family: monospace; box-shadow: 0 5px 9px 0 rgba(0, 0, 0, 0.2), 0 7px 21px 0 rgba(0, 0, 0, 0.19);";

      toastArea.appendChild(toast);
      document.body.appendChild(toastArea);
    }

    toast.appendChild(textSpan);
  }

  if (window.__appFormData["_toast_attr_change"]) {
    document.addEventListener("appattrchanged", function (e) {
      addNotification(`Attribute "${e.detail.name}" = ${JSON.stringify(e.detail.value)}`);
    });
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
      dispatch("sizechanged", {
        detail: { width: window.innerWidth, height: window.innerHeight },
      });
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
  var showEventTriggeredAt = 0;
  window.signageVisible = new Promise(function (resolve) {
    document.addEventListener("show", function () {
      showEventTriggeredAt = Date.now();
      resolve();
    });
  });

  var playbackInfo = {};
  try {
    playbackInfo = JSON.parse(window.__appFormData["_playback_info"]) || {};
  } catch (e) {
    /* noop */
  }

  var serialPortCallbacks = {};
  function serialPortDispatch(alias, data) {
    var data = { detail: { name: alias, value: data } };
    if (serialPortCallbacks[alias]) {
      serialPortCallbacks[alias].forEach(function (func) {
        func(data);
      });
    }
  }

  if (window.__appFormData._simulate_playback_changes) {
    function setBgColour() {
      if (document.body.style.backgroundColor === "red") {
        document.body.style.backgroundColor = "blue";
      } else {
        document.body.style.backgroundColor = "red";
      }

      signage.playbackLoops().then((value) => {
        dispatch("playbackloopschanged", { detail: { value } }, internalTarget);
        addNotification("playbackloopschanged event fired");
      });
    }

    window.signageVisible.then(() => {
      setInterval(setBgColour, 10_000);
      setBgColour();
    });
  }

  var internalTarget = document.createElement("div");
  var brightness = 100;
  var volume = 100;
  var playIdCount = 0;
  var signage = {
    addEventListener: function () {
      if (arguments[0] === "serialportdata") {
        var alias = arguments[1];
        var func = arguments[2];
        if (!serialPortCallbacks[alias]) serialPortCallbacks[alias] = [];
        serialPortCallbacks[alias].push(func);
      } else {
        internalTarget.addEventListener.apply(internalTarget, arguments);
      }
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
            resolve({
              src: "ip",
              lat: pos.coords.latitude,
              lng: pos.coords.longitude,
            });
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
      console.log("LOG ENTRY", {
        level: level,
        domain: domain,
        message: message,
      });
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
    playbackLoops: function () {
      return new Promise((resolve) => {
        var pbLoops = JSON.parse(JSON.stringify(window.__playbackLoops));

        if (window.__appFormData._simulate_playback_changes && showEventTriggeredAt) {
          var red = document.body.style.backgroundColor === "red";
          var name = red ? "Red Image" : "Blue Image";
          var id = red ? "32UXZyPl" : "jaUpoPKV";

          var loop = {
            name: "PRIMARY",
            start: showEventTriggeredAt,
            rect: [0, 0, window.innerWidth, window.innerHeight],
            content: {
              id: id,
              kind: "IMAGE",
              name: name,
              attrs: {},
              reason: "LOOP",
              start: showEventTriggeredAt + playIdCount * 10_000,
              playId: "#c10" + playIdCount++,
            },
          };

          pbLoops.loops.push(loop);
        }

        pbLoops.ts = Date.now();
        pbLoops.loops[0].content.start = showEventTriggeredAt;
        resolve(pbLoops);
      });
    },
    playbackLoopsDiff: function (prevPlaybackLoops, currentPlaybackLoops) {
      var started = [];
      var stopped = [];
      var oldLoops = {};
      var newLoops = {};

      function mapContents(loop, path, paths) {
        if (!loop.content) return;

        path += "/" + loop.name + "/" + loop.content.id;
        paths[path] = {
          name: loop.name,
          rect: loop.rect,
          content: loop.content,
        };

        if (loop.content.tracks) {
          for (var i = 0; i < loop.content.tracks.length; i++) {
            mapContents(loop.content.tracks[i], path, paths);
          }
        }
      }

      if (prevPlaybackLoops) {
        for (var i = 0; i < prevPlaybackLoops.loops.length; i++) {
          var loop = prevPlaybackLoops.loops[i];
          mapContents(loop, "", oldLoops);
        }
      }

      for (i = 0; i < currentPlaybackLoops.loops.length; i++) {
        loop = currentPlaybackLoops.loops[i];
        mapContents(loop, "", newLoops);
      }

      Object.keys(oldLoops).forEach((path) => {
        if (!newLoops[path]) {
          loop = oldLoops[path];
          loop.content.duration = (currentPlaybackLoops.ts - loop.content.start) / 1000;
          stopped.push(loop);
        }
      });

      Object.keys(newLoops).forEach((path) => {
        if (!oldLoops[path]) started.push(newLoops[path]);
      });

      return {
        stopped: stopped,
        started: started,
      };
    },
    removeEventListener: function () {
      internalTarget.removeEventListener.apply(internalTarget, arguments);
    },
    sendEvent: function (level, code, message, extra) {
      console.log("SENT EVENT", {
        level: level,
        code: code,
        message: message,
        extra: extra,
      });
    },
    serialPortWrite: function (alias, data) {
      return new Promise((resolve, reject) => {
        if (window.__serialPorts[alias]) {
          var mode = window.__serialPorts[alias];
          try {
            if (mode === "character") {
              for (var i = 0; i < data.length; i++) {
                serialPortDispatch(alias, data[i]);
              }
            } else if (mode === "line") {
              data.split(/\r?\n/).forEach(function (line) {
                serialPortDispatch(alias, line);
              });
            } else if (mode === "binary") {
              var encoder = new TextEncoder();
              serialPortDispatch(alias, encoder.encode(data).buffer);
            }
            resolve();
          } catch (ex) {
            reject(`Error writing data to serial port: "${ex}"`);
          }
        } else {
          reject(`Serial port not connected: "${alias}"`);
        }
      });
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
        } else if (name in playbackInfo.player.attrs && value !== playbackInfo.player.attrs[name]) {
          playbackInfo.player.attrs[name] = value;
          dispatch("attrchanged", { detail: { name: name, value: value } }, internalTarget);
        }
      } catch (ex) {
        console.log("Error setting player attribute: ", ex);
      }
    },
    setPlayerAttributes: function (values) {
      for (var [name, value] of Object.entries(values)) {
        signage.setPlayerAttribute(name, value);
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

  if (window.__appAttrs) {
    let assertAttrExists = function (name) {
      if (!(name in window.__appAttrs)) {
        throw new Error("App attribute does not exist: " + name);
      }
    };

    let checkAttrType = function (name, value) {
      var attrType = window.__appAttrs[name]["type"];

      if (typeof value === attrType || value === null) {
        return true;
      }

      if (value instanceof Array) {
        var elementType;
        if (attrType === "numberarray") {
          elementType = "number";
        } else if (attrType === "stringarray") {
          elementType = "string";
        } else {
          return false;
        }

        for (var i = 0; i < value.length; i++) {
          if (typeof value[i] !== elementType) {
            return false;
          }
        }

        return true;
      }

      return false;
    };

    window.isAppAttributeConnected = function (name) {
      assertAttrExists(name);
      return window.__appAttrs[name]["playerName"] in playbackInfo.player.attrs;
    };

    window.getAppAttribute = function (name, defaultValue = null) {
      assertAttrExists(name);

      if (window.__appAttrs[name]["mode"] === "w") {
        throw new Error("Can't access writeonly app attribute: " + name);
      }

      var attr = signage.getPlayerAttribute(window.__appAttrs[name]["playerName"]);

      return attr ? attr : window.__appAttrs[name]["default"] ? window.__appAttrs[name]["default"] : defaultValue;
    };

    window.setAppAttribute = function (name, value) {
      assertAttrExists(name);

      if (!isAppAttributeConnected(name)) return;

      if (window.__appAttrs[name]["mode"] === "r") {
        throw new Error("Can't set readonly app attribute: " + name);
      }

      if (checkAttrType(name, value)) {
        signage.setPlayerAttribute(window.__appAttrs[name]["playerName"], value);
      } else {
        throw new Error("Incorrect value type for app attribute: " + name);
      }
    };

    window.setAppAttributes = function (values) {
      for (var [name, value] of Object.entries(values)) {
        window.setAppAttribute(name, value);
      }
    };

    signage.addEventListener("attrchanged", function (event) {
      var playerAttr = event.detail.name;
      var value = event.detail.value;

      var appAttr = Object.keys(window.__appAttrs).find((key) => window.__appAttrs[key]["playerName"] === playerAttr);
      if (appAttr && isAppAttributeConnected(appAttr)) {
        dispatch("appattrchanged", { detail: { name: appAttr, value: value } });
      }
    });
  }

  if (window.__appFormData["_toast_serial_port_data"] && window.__serialPorts) {
    var serialPorts = Object.keys(window.__serialPorts);
    serialPorts.forEach(function (alias) {
      signage.addEventListener("serialportdata", alias, function (e) {
        addNotification(`Data read from serial port "${e.detail.name}": "${e.detail.value}"`);
      });
    });
  }

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
