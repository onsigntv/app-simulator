document.addEventListener(
  "DOMContentLoaded",
  function () {
    var button = document.getElementById("pbInfoBtn");
    function togglePlaybackInfo() {
      var toggled = document.getElementById("_playback_info").toggleAttribute("hidden");
      if (toggled) {
        button.innerHTML = "Edit";
      } else {
        button.innerHTML = "Done";
      }
    }
    button.addEventListener("click", togglePlaybackInfo, false);
    togglePlaybackInfo();

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
