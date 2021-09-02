(function() {
  var prevWidth = null, prevHeight = null, timer = null;
  function dispatch(name, width, height) {
    var customEvent = document.createEvent('HTMLEvents');
    customEvent.initEvent(name, true, false);
    if (width !== undefined) customEvent.clientWidth = width;
    if (height !== undefined) customEvent.clientHeight = height;
    document.dispatchEvent(customEvent);
  }
  function dispatchShow() {
    window.setTimeout(function() { dispatch('show'); }, 1000);
  }
  function conditionalDispatchMeasure() {
    var width = window.innerWidth, height = window.innerHeight;
    if (width !== prevWidth || height !== prevHeight) {
      dispatch('measurechange', width, height);
      prevWidth = width; prevHeight = height;
    }
  }
  function debounceDispatchMeasure() {
    if (timer) window.clearTimeout(timer);
    timer = window.setTimeout(conditionalDispatchMeasure, 500);
  }
  window.addEventListener('DOMContentLoaded', conditionalDispatchMeasure, false);
  window.addEventListener('load', conditionalDispatchMeasure, false);
  window.addEventListener('load', dispatchShow, false);
  window.addEventListener('resize', debounceDispatchMeasure, false);
})();
