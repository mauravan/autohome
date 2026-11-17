#pragma once

namespace esphome::captive_portal {

constexpr char INDEX_HTML[] PROGMEM = R"html(<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Wi-Fi setup</title>
<style>
:root{--g:#1b4332;--m:#777;--bd:#e4e4e4}
*{box-sizing:border-box;margin:0}
body{font:16px/1.5 system-ui,-apple-system,sans-serif;color:#111;background:#fff;
     min-height:100vh;display:flex;justify-content:center;padding:32px 20px}
main{width:100%;max-width:420px}
img.logo{display:block;height:64px;margin:0 auto 24px}
h1{font-size:20px;font-weight:600;color:var(--g)}
p.sub{color:var(--m);font-size:14px;margin-top:4px}
p#dev{color:var(--m);font-size:13px;margin-top:2px}
h2{font-size:13px;font-weight:600;text-transform:uppercase;letter-spacing:.08em;
   color:var(--m);margin:26px 0 8px}
ul#aps{list-style:none;border:1px solid var(--bd);border-radius:10px;overflow:hidden}
ul#aps:empty{display:none}
ul#aps li{display:flex;justify-content:space-between;align-items:center;gap:12px;
   padding:12px 14px;cursor:pointer;border-bottom:1px solid var(--bd)}
ul#aps li:last-child{border-bottom:0}
ul#aps li:hover{background:#f5f8f5}
.ssid{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.bars{color:var(--g);font-size:12px;letter-spacing:2px;flex:none}
p#noaps{color:var(--m);font-size:14px}
label{display:block;font-size:13px;color:var(--m);margin:14px 0 4px}
input{width:100%;padding:10px 12px;font:inherit;border:1px solid var(--bd);
   border-radius:8px;outline:none}
input:focus{border-color:var(--g)}
button{width:100%;margin-top:20px;padding:12px;font:inherit;font-weight:600;
   color:#fff;background:var(--g);border:0;border-radius:8px;cursor:pointer}
button:disabled{opacity:.5}
p#status{margin-top:16px;font-size:14px;color:var(--g);text-align:center;min-height:21px}
</style>
</head>
<body>
<main>
<img class="logo" src="/logo.png" alt="">
<h1>Wi-Fi setup</h1>
<p class="sub">Pick your network, or type the name manually.</p>
<p id="dev"></p>
<h2>Networks</h2>
<ul id="aps"></ul>
<p id="noaps">Scanning…</p>
<h2>Manual</h2>
<label for="ssid">Network name</label>
<input id="ssid" maxlength="32" autocomplete="off">
<label for="psk">Password</label>
<input id="psk" type="password">
<button id="go">Connect</button>
<p id="status"></p>
</main>
<script>
const $=i=>document.getElementById(i);
let done=false;
const BARS=n=>n>-50?'\u2582\u2584\u2586\u2588':n>-60?'\u2582\u2584\u2586':n>-70?'\u2582\u2584':'\u2582';
function pick(s){if(done)return;$('ssid').value=s;$('psk').focus();}
async function poll(){
  if(done)return;
  try{
    const c=await(await fetch('/config.json',{cache:'no-store'})).json();
    if(c.name)$('dev').textContent=c.name;
    const ul=$('aps');ul.textContent='';
    const aps=(c.aps||[]).filter(a=>a.ssid);
    $('noaps').style.display=aps.length?'none':'block';
    if(!aps.length)$('noaps').textContent='Scanning… no networks yet';
    for(const a of aps){
      const li=document.createElement('li');
      const s=document.createElement('span');s.className='ssid';s.textContent=a.ssid;
      const b=document.createElement('span');b.className='bars';b.textContent=BARS(a.rssi);
      li.append(s,b);li.onclick=()=>pick(a.ssid);ul.append(li);
    }
  }catch(e){}
}
poll();setInterval(poll,5000);
$('go').onclick=async()=>{
  const ssid=$('ssid').value.trim(),psk=$('psk').value;
  if(!ssid){$('status').textContent='Enter a network name.';return;}
  done=true;$('go').disabled=true;$('status').textContent='Saving…';
  try{
    // GET, not POST: the portal handler only answers HTTP_GET (canHandle filter)
    await fetch('/wifisave?ssid='+encodeURIComponent(ssid)+'&psk='+encodeURIComponent(psk),{cache:'no-store'});
    $('status').textContent='Saved \u2014 the sensor is connecting to \u201c'+ssid+'\u201d. This page will go offline; reconnect to your network to finish setup.';
  }catch(e){
    done=false;$('go').disabled=false;
    $('status').textContent='Could not reach the device. Still on the setup network? Try again.';
  }
};
</script>
</body>
</html>
)html";

}  // namespace esphome::captive_portal
