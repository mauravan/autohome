(function () {
"use strict";
var CSS = [
  /* logo wordmark */
  "a#logo esp-logo{display:none!important}",
  "a#logo{display:inline-block!important;width:36px!important;height:36px!important;",
  "  background:url(data:image/png;base64,__LOGO_B64__) no-repeat left center/contain!important}",
  /* header layout: single row logo | title | beat, subtitle centered below */
  "header{display:flex!important;flex-wrap:wrap!important;align-items:center!important;",
  "  justify-content:space-between!important;width:100%!important;padding:0.5em!important;",
  "  box-sizing:border-box!important}",
  "a#logo{order:1!important;width:36px!important;height:36px!important;flex-shrink:0!important}",
  "h1{order:2!important;text-align:center!important;flex:1!important;margin:0!important}",
  "#beat{order:3!important;font-size:1.6rem!important;flex-shrink:0!important}",
  "header div{order:4!important;flex-basis:100%!important;text-align:center!important;margin-top:0.25em!important}",
  /* all-button sorting groups render as full-width buttons */
  ".tab-container:not(:has(.entity-row:not(:has(> div:nth-child(3) > button.abutton)))){",
  "  border:none;display:flex;flex-direction:column;gap:8px;padding:8px;",
  "  & .entity-row{background:#2e7d32;color:#fff;border-radius:8px;",
  "    justify-content:center;font-weight:600;padding:4px 8px;cursor:pointer;",
  "    position:relative;overflow:hidden;min-height:44px}",
  "  & .entity-row:hover{filter:brightness(1.15)}",
  "  & .entity-row>div:nth-child(3){position:absolute;inset:0}",
  "  & .entity-row>div:nth-child(3) button.abutton{position:absolute;inset:0;",
  "    width:100%;height:100%;opacity:0}",
  "}"
].join("");
var orig = Element.prototype.attachShadow;
Element.prototype.attachShadow = function (init) {
  var root = orig.call(this, init);
  try {
    var st = document.createElement("style");
    st.textContent = CSS;
    root.appendChild(st);
  } catch (e) { /* never break the app */ }
  return root;
};
})();
