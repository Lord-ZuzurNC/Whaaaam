// Runs synchronously in <head>, before first paint.
//
// The markup ships data-theme="mocha" and ThemeManager corrected it at
// DOMContentLoaded, so a Latte user got a dark first paint that then faded to
// light on every single load. This sets the attribute early instead.
//
// It is a separate file rather than an inline script because the page's CSP is
// `script-src 'self'`, which blocks inline script and would need a nonce.
// ThemeManager in app.js still owns persistence, the switcher and image swaps;
// this only decides the very first paint.
(function () {
  var VALID = ["latte", "frappe", "macchiato", "mocha"];
  var theme = null;
  try {
    var fromUrl = new URLSearchParams(window.location.search).get("theme");
    if (VALID.indexOf(fromUrl) !== -1) theme = fromUrl;
    if (!theme) {
      var saved = localStorage.getItem("theme");
      if (VALID.indexOf(saved) !== -1) theme = saved;
    }
  } catch (e) {
    // Private mode or blocked storage: fall through to the default.
  }
  document.documentElement.setAttribute("data-theme", theme || "mocha");
})();
