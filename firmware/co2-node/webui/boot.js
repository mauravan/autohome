(function () {
"use strict";
var CSS = [
  /* logo wordmark */
  "a#logo esp-logo{display:none!important}",
  "a#logo{display:inline-block!important;width:36px!important;height:36px!important;",
  "  background:url(data:image/png;base64,__LOGO_B64__) no-repeat left center/contain!important}",
  /* header layout: small logo/icons pinned, title + subtitle centered below */
  "header{position:relative!important;display:flex!important;flex-direction:column!important;",
  "  align-items:center!important;width:90%!important;margin:1em auto 0!important;",
  "  padding-inline:0.5em!important;padding-top:2.5em!important;padding-bottom:0.5em!important}",
  "a#logo{position:absolute!important;left:0.5em!important;top:0.5em!important}",
  "#beat{position:absolute!important;right:2em!important;top:0.5em!important;font-size:1.6rem!important}",
  "#scheme{position:absolute!important;right:0.5em!important;top:0.5em!important;font-size:1.6rem!important}",
  "h1{text-align:center!important;width:100%!important;margin-block:.25em!important}",
  "header div{text-align:center!important;width:100%!important}",
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
