document.addEventListener(
  "DOMContentLoaded",
  function () {
    function setupTextArea(elementId, btnId) {
      var toggleButton = document.getElementById(btnId);

      function toggleTextArea() {
        var toggled = document.getElementById(elementId).toggleAttribute("hidden");
        if (toggled) {
          toggleButton.innerHTML = "Edit";
        } else {
          toggleButton.innerHTML = "Done";
        }
      }

      toggleButton.addEventListener("click", toggleTextArea, false);
      toggleTextArea();
    }

    setupTextArea("_playback_info", "pbInfoBtn");

    function toggleAttrConnection(checkbox) {
      var textArea = document.getElementById("_playback_info");
      var pbInfo = JSON.parse(textArea.value);

      if (checkbox.checked) {
        pbInfo.player.attrs[checkbox.dataset.label] = null;
      } else {
        delete pbInfo.player.attrs[checkbox.dataset.label];
      }

      var defaultValueInput = document.getElementById(checkbox.dataset.attr);
      if (defaultValueInput) {
        defaultValueInput.hidden = !checkbox.checked;
        if (!checkbox.checked) defaultValueInput.value = null;
      }

      textArea.value = JSON.stringify(pbInfo, null, 2);
    }

    Array.from(document.getElementsByClassName("connect-attr")).forEach(function (checkbox) {
      checkbox.addEventListener("click", function () {
        toggleAttrConnection(this);
      });

      toggleAttrConnection(checkbox);
    });

    var count = 1;
    var serialPortForm = document.getElementById("serial-port-form");
    var serialPortInputs = [];
    document.getElementById("add-serial").addEventListener("click", function () {
      var newForm = serialPortForm.cloneNode(true);
      newForm.toggleAttribute("hidden");
      newForm.id = serialPortForm.id + count.toString();
      count++;

      serialPortInputs.push({
        alias: newForm.children[0].children[0],
        mode: newForm.children[2].children[0],
      });
      document.getElementById("serial-ports-table").appendChild(newForm);
      document.querySelector(".serial-toast").classList.remove("d-none");
    });

    var isValidDataFeedURL = function(url) {
      var regex = /^https?:\/\/[^/]+\/share\/[a-zA-Z0-9]{32}\/?$/;
      return regex.test(url);
    };

    document.querySelectorAll(".js-datafeed-input").forEach(function(element) {
      var targetId = element.dataset.targetId;

      var updateValue = function() {
        var value = parseInt(element.value, 10);
        if (!isNaN(value) && value > 0) {
          var config = {
            entry_count: value,
          }
          document.getElementById(targetId).value = JSON.stringify(config);
        }

        if (isValidDataFeedURL(element.value.trim())) {
          document.querySelector(`.js-open-config-datafeed[data-target-id=${targetId}`).removeAttribute("disabled");
        } else {
          document.querySelector(`.js-open-config-datafeed[data-target-id=${targetId}`).setAttribute("disabled", "disabled");
        }
      }

      updateValue();
      element.addEventListener("input", updateValue);
    });

    document.querySelectorAll(".js-save-config-datafeed").forEach(function(btn) {
      var targetId = btn.dataset.targetId;
      btn.addEventListener("click", function() {
        btn.blur();
        var modalBody = document.querySelector(`#modal${targetId} .modal-body`);
        var url = document.getElementById("url" + targetId).value;
        var selects = modalBody.querySelectorAll("select");

        if (url && selects.length > 0) {
          var config = {
            url: url
          };
          selects.forEach(function(select) {
            if (select.value) {
              config[select.name] = select.value;
            }
          });
          document.getElementById(targetId).value = JSON.stringify(config);
        } else {
          document.getElementById(targetId).value = "";
        }
      });
    });

    document.querySelectorAll(".js-open-config-datafeed").forEach(function(btn) {
      btn.addEventListener("click", function(event) {
        var targetId = btn.dataset.targetId;
        var currentConfig = null;
        
        try {
          currentConfig = JSON.parse(document.getElementById(targetId).value);
        } catch(err) {}

        var url = document.getElementById("url" + targetId).value;

        if (currentConfig && currentConfig.url != url) {
          currentConfig = null;
        }

        if (currentConfig) return;

        var fields =  JSON.parse(btn.dataset.fields);
        loadOptionsFromDataFeed(url, fields, targetId);
      });
    });

    var loadOptionsFromDataFeed = function(url, fields, targetId) {
      var modalBody = document.querySelector(`#modal${targetId} .modal-body`);
      modalBody.innerText = "Fetching..."

      if (!url) {
        showError(modalBody, "Invalid Data Feed URL.");
        return;
      }

      var parsedUrl = url.split("?")[0] + "?json=1";

      fetch(parsedUrl)
        .then(function(response) {
          return response.json();
        })
        .then(function(data) {
          if (!data.columns || !Array.isArray(data.columns)) {
            return showError(modalBody, "Invalid Data Feed URL.");
          }
          renderFieldSelectors(fields, data.columns, modalBody);
        })
        .catch(function(error) {
          showError(modalBody, "Invalid Data Feed URL.");
        });
    };

    var renderFieldSelectors = function(fields, columns, container) {
      container.innerHTML = "";
      var formElement = document.createElement("form");
      var selectedColumns = {};
      var selectedFields = {};
      fields.forEach(function(field) {
        var formGroup = document.createElement("div");
        formGroup.className = "form-group";

        var label = document.createElement("label");
        label.textContent = field.label;

        var select = document.createElement("select");
        select.className = `form-control field-type-${field.type}`;
        select.name = field.name;

        var helpText;
        if (field.help_text) {
          helpText = document.createElement("p");
          helpText.style.fontSize = "12px";
          helpText.style.opacity = 0.6;
          helpText.style.margin = "5px 0 0 0";
          helpText.innerText = field.help_text;
        }

        var availableTypes = [field.type];
        if (field.type === "text") {
          availableTypes.push("url", "number", "integer", "time", "date", "datetime");
        } else if (field.type === "media") {
          availableTypes.push("image", "video");
        }

        if (!field.required) {
          var option = document.createElement("option");
          option.value = "";
          option.textContent = "No column";
          select.appendChild(option);
          label.textContent += " (optional)"
        }

        columns.forEach(function(column) {
          if (availableTypes.includes(column.kind)) {
            var option = document.createElement("option");
            option.value = column.guid;
            option.textContent = column.name;
            select.appendChild(option);

            if (!selectedColumns[column.guid] && !selectedFields[field.name]) {
              select.value = option.value;
              selectedColumns[column.guid] = true;
              selectedFields[field.name] = true;
            }
          }
        });

        formGroup.appendChild(label);
        formGroup.appendChild(select)
        if (helpText) {
          formGroup.appendChild(helpText);
        }
        formElement.appendChild(formGroup);
      });
      container.appendChild(formElement);
    };

    var showError = function(container, message) {
      container.innerHTML = `<div class="alert alert-danger">${message}</div>`;
    };

    document.addEventListener("submit", function (event) {
      var serialPortsData = {};
      for (var i = 0; i < serialPortInputs.length; i++) {
        var alias = serialPortInputs[i].alias.value;
        if (alias) {
          serialPortsData[serialPortInputs[i].alias.value] = serialPortInputs[i].mode.value;
        }
      }
      document.getElementById("_serial_port_config").value = JSON.stringify(serialPortsData);
    });
  },
  false
);
