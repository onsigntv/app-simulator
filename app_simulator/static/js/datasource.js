window.__handleDataFeed = function (opts) {
  var modat = opts.modat;
  
  function logMessage(message) {
    var now = new Date();
    console.log(now.toISOString() + " - " + opts.label + ": " + message);
  }

  function createUpdateChain(currentRows) {
    return new Promise((resolve) => {
      document.addEventListener("updateDataFeeds", function handler() {
        if (opts.update_source) {
          var rows = currentRows === opts.update_source ? opts.source : opts.update_source;
          document.removeEventListener("updateDataFeeds", handler);
          resolve({
            fields: opts.fields,
            source: rows,
            update: createUpdateChain(rows),
          });
          logMessage("Updated Successfully");
        } else if (opts.config && opts.config.url) {
          logMessage("Fetching...");
          fetch(opts.config.url)
            .then((response) => response.json())
            .then((data) => {
              if (!data.modat || !data.columns || !Array.isArray(data.columns)) {
                logMessage("Update Failed");
                return;
              }
              if (modat && data.modat <= modat) {
                logMessage("No Changes");
              } else {
                modat = data.modat;
                document.removeEventListener("updateDataFeeds", handler);
                var rows = [];
                data.rows.forEach(row => {
                  var data = {};
                  Object.keys(opts.fields).forEach(field => {
                    if (row[opts.config[field]] !== undefined) {
                      data[field] = row[opts.config[field]];
                    }
                  });
                  rows.push(data);
                });
                resolve({
                  fields: opts.fields,
                  source: rows,
                  update: createUpdateChain(),
                });
                logMessage("Updated Successfully");
              }
            })
            .catch((error) => {
              logMessage("Update Failed");
              console.error(error);
            });
        }
      });
    });
  }

  return Promise.resolve({
    fields: opts.fields,
    source: opts.source,
    update: createUpdateChain(),
  });
};

(function () {
  document.addEventListener("DOMContentLoaded", function () {
    var style = document.createElement("style");
    style.innerHTML = `
      #--floating-datafeed-btn {
        position: fixed;
        top: 20px;
        right: 0;
        background-color: #333;
        color: white;
        padding: 5px 5px;
        cursor: pointer;
        z-index: 9999999;
        user-select: none;
        font-family: sans-serif;
        font-size: 14px;
        opacity: 0.3;
        color: #fff;
        border-radius: 6px 0 0 6px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 5px;
        transform: translateX(82%);
      }
      #--floating-datafeed-btn-header {
        display:flex;
        align-items: center;
        justify-content: center;
        gap: 5px;
      }
      #--floating-datafeed-btn:hover {
        opacity: 1;
        transform: translateX(0);
      }
      #--floating-datafeed-btn.active {
        opacity: 1;
        transform: translateX(0);
      }
      #--floating-datafeed-btn-icon svg {
        width: 20px;
        height: 20px;
        display: block;
      }
      #--floating-datafeed-btn-icon path {
        fill: #43bf96;
      }
      #--floating-datafeed-btn:active {
        background-color:rgb(53, 147, 116);
        transform: translateX(0);
        opacity: 1;
      }
      #--floating-datafeed-btn:hover #--floating-datafeed-btn-title {
        display: inline;
      }
    }
    `;
    document.head.appendChild(style);

    var floatingBtn = document.createElement("div");
    floatingBtn.id = "--floating-datafeed-btn";
    floatingBtn.innerHTML = `
      <div id="--floating-datafeed-btn-header">
        <span id="--floating-datafeed-btn-icon">
          <svg id="Layer_1" version="1.1" viewBox="0 0 448 512">
            <path d="M448,80v48c0,44.2-100.3,80-224,80S0,172.2,0,128v-48C0,35.8,100.3,0,224,0s224,35.8,224,80ZM393.2,214.7c20.8-7.4,39.9-16.9,54.8-28.6v101.9c0,44.2-100.3,80-224,80S0,332.2,0,288v-101.9c14.9,11.8,34,21.2,54.8,28.6,44.9,16,104.7,25.3,169.2,25.3s124.3-9.3,169.2-25.3ZM0,346.1c14.9,11.8,34,21.2,54.8,28.6,44.9,16,104.7,25.3,169.2,25.3s124.3-9.3,169.2-25.3c20.8-7.4,39.9-16.9,54.8-28.6v85.9c0,44.2-100.3,80-224,80S0,476.2,0,432v-85.9Z"/>
          </svg>
        </span>
        <span id="--floating-datafeed-btn-title">Update Data Feeds</span>
      </div>`;  

    document.body.appendChild(floatingBtn);

    var startedDrag = false;
    var isDragging = false;
    var offsetY = 0;
    var preventClick = false;

    floatingBtn.addEventListener("mousedown", (e) => {
      startedDrag = true;
      offsetY = e.clientY - floatingBtn.getBoundingClientRect().top;
      e.stopPropagation();
    });

    floatingBtn.addEventListener('contextmenu', (event) => {
        event.preventDefault();
    });

    floatingBtn.addEventListener("click", function() {
      if (preventClick) {
        preventClick = false;
        return;
      }
      var event = new Event("updateDataFeeds");
      document.dispatchEvent(event);
    });

    document.addEventListener("mousemove", (e) => {
      if (!startedDrag) return;
      isDragging = true;
      floatingBtn.style.top = `${e.clientY - offsetY}px`;
    });

    document.addEventListener("mouseup", () => {
      if (isDragging) {
        preventClick = true;
      }
      startedDrag = false;
      isDragging = false;
    });
  });
})();
