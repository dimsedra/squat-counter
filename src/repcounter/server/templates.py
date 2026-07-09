"""Inline HTML templates for the web dashboard.

Uses string concatenation instead of Jinja2 to avoid template-engine dependency.
All CSS is inlined to keep the server self-contained.
"""
from __future__ import annotations

from typing import Any

from fastapi.responses import HTMLResponse

_CSS = """\
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html{font-size:16px}
body{font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;background:#0d1117;color:#e6edf3;min-height:100vh}
a{color:#58a6ff;text-decoration:none}
a:hover{text-decoration:underline}
h1{font-size:1.6rem;font-weight:600}
h2{font-size:1.2rem}
code{font-family:'SF Mono','Fira Code',monospace;font-size:.85rem}
.container{max-width:1200px;margin:0 auto;padding:1.5rem}
header,.watch-header{display:flex;align-items:center;gap:2rem;margin-bottom:1.5rem}
nav{display:flex;gap:1rem}
nav a{font-size:.9rem;color:#8b949e}
nav a:hover{color:#e6edf3}
.subtitle{color:#8b949e;font-size:.95rem;margin:.25rem 0 1.5rem}
.card-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:1rem}
.card{display:block;background:#161b22;border:1px solid #30363d;border-radius:8px;padding:1.5rem;cursor:pointer;transition:border-color .2s,transform .1s}
.card:hover{border-color:#58a6ff;transform:translateY(-1px)}
.card-icon{font-size:2rem;margin-bottom:.5rem}
.card h2{margin-bottom:.25rem}
.card p{color:#8b949e;font-size:.85rem}
form{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:1.5rem}
form h3{margin-bottom:1rem}
label{display:block;font-size:.85rem;color:#8b949e;margin-bottom:.75rem}
input[type="text"],input[type="file"]{display:block;margin-top:.25rem;width:100%}
input[type="text"]{background:#0d1117;border:1px solid #30363d;border-radius:4px;padding:.5rem;color:#e6edf3;font-size:.9rem}
button,.btn{background:#238636;color:#fff;border:none;border-radius:6px;padding:.5rem 1.25rem;font-size:.9rem;cursor:pointer;display:inline-block}
button:hover{background:#2ea043}
.btn-danger{background:#da3633}
.btn-danger:hover{background:#f85149}
.btn-danger:disabled{background:#484f58;cursor:default}
.watch-layout{display:flex;gap:1rem;flex-wrap:wrap}
.video-panel{flex:2;min-width:480px}
.video-panel img{width:100%;border-radius:8px;border:1px solid #30363d;display:block}
.data-panel{flex:1;min-width:200px;background:#161b22;border:1px solid #30363d;border-radius:8px;padding:1rem;display:flex;flex-direction:column;gap:.75rem}
.metric{display:flex;justify-content:space-between;align-items:baseline}
.metric-label{font-size:.8rem;color:#8b949e;text-transform:uppercase;letter-spacing:.05em}
.metric-value{font-size:1.5rem;font-weight:700;font-variant-numeric:tabular-nums}
.rep-count{border-bottom:1px solid #30363d;padding-bottom:.5rem}
.rep-count .metric-value{font-size:2.5rem;color:#58a6ff}
.badge-row{display:flex;flex-wrap:wrap;gap:.35rem;min-height:1.6rem}
.badge{font-size:.7rem;font-weight:600;text-transform:uppercase;letter-spacing:.05em;padding:.2rem .5rem;border-radius:4px;background:#d29922;color:#0d1117}
.badge-danger{background:#da3633;color:#fff}
.badge-warning{background:#d29922;color:#0d1117}
.badge-ok{background:#238636;color:#fff}
.hidden{display:none}
.session-controls{margin-top:auto;display:flex;flex-direction:column;gap:.5rem}
.session-table{width:100%;border-collapse:collapse;font-size:.85rem}
.session-table th,.session-table td{padding:.5rem .75rem;text-align:left;border-bottom:1px solid #21262d}
.session-table th{color:#8b949e;font-weight:500}
.session-table tr:hover td{background:#161b22}
.download-links{display:flex;gap:.5rem}
.download-links a{font-size:.8rem}
.empty-state{color:#8b949e;margin-top:2rem;text-align:center}
"""

_WS_JS = """\
const SID=\"{sid}";let ws=null,complete=false;
function cws(){
  if(complete)return;
  const p=location.protocol==='https:'?'wss:':'ws:';
  ws=new WebSocket(p+'//'+location.host+'/ws/'+SID);
  ws.onmessage=function(e){
    var d=JSON.parse(e.data);
    if(d.complete){
      complete=true;ws.close();
      document.getElementById('rc').textContent=d.rep_count;
      document.getElementById('bb').classList.remove('hidden');
      document.getElementById('btn-stop').style.display='none';
      done(d);
      return;
    }
    document.getElementById('rc').textContent=d.rep_count;
    document.getElementById('ag').textContent=d.angle!=null?d.angle.toFixed(1)+'\\u00b0':'\\u2014';
    document.getElementById('st').textContent=d.rep_state||'\\u2014';
    document.getElementById('fp').textContent=d.fps;
    document.getElementById('vi').textContent=d.visibility!=null?d.visibility.toFixed(2):'\\u2014';
    tb('bp',d.paused);tb('bpr',d.partial);tb('bl',d.lost_track);tb('bu',d.uncalibrated);
  };
  ws.onclose=function(){
    if(!complete&&document.getElementById('vs'))setTimeout(cws,2000);
  };
}
function done(d){
  document.getElementById('dl').href='/session/'+SID+'/download?format=csv';
  document.getElementById('dl').style.display='inline-block';
  document.getElementById('btn-stop').disabled=true;
  document.getElementById('btn-stop').textContent='\u2713 Saved';
}
function tb(id,show){
  var e=document.getElementById(id);
  if(show)e.classList.remove('hidden');else e.classList.add('hidden');
}
async function stopSess(){
  var r=await fetch('/session/'+SID+'/stop',{method:'POST'});
  var d=await r.json();
  if(ws)ws.close();
  if(d.dir)done(d);
  document.getElementById('btn-stop').disabled=true;
  document.getElementById('btn-stop').textContent='\u2713 Saved';
}
cws();
"""


def _page(title: str, body: str) -> HTMLResponse:
    return HTMLResponse(
        '<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width">'
        '<title>' + title + '</title><style>' + _CSS + '</style></head><body>'
        + body + '</body></html>'
    )


def render_index() -> HTMLResponse:
    return _page("Squat Rep Counter",
        '<main class="container">'
        '<h1>Squat Rep Counter</h1>'
        '<p class="subtitle">Real-time pose monitoring &amp; research data collection</p>'
        '<div class="card-grid">'
        '<a href="/watch?source=webcam" class="card">'
        '<div class="card-icon">&#x1F4F7;</div><h2>Live Webcam</h2>'
        '<p>Start real-time squat monitoring with your webcam</p></a>'
        '<div class="card" onclick="document.getElementById(\'uf\').style.display=\'block\'">'
        '<div class="card-icon">&#x1F4C1;</div><h2>Upload Video</h2>'
        '<p>Process a pre-recorded video and collect session data</p></div>'
        '<a href="/sessions" class="card">'
        '<div class="card-icon">&#x1F4CA;</div><h2>Past Sessions</h2>'
        '<p>View and download previously recorded session data</p></a></div>'
        '<form id="uf" action="/upload" method="post" enctype="multipart/form-data"'
        ' style="display:none;margin-top:2rem"><h3>Upload Video</h3>'
        '<label>Video file (.mp4, .avi, .mov)'
        '<input type="file" name="file" accept="video/*" required></label>'
        '<label>Condition label (e.g. lighting_normal_cam_left)'
        '<input type="text" name="label" placeholder="my_condition_label"></label>'
        '<button type="submit">Upload &amp; Process</button></form>'
        '<script>'
        'document.getElementById(\'uf\').addEventListener(\'submit\',async function(e){'
        'e.preventDefault();var fd=new FormData(e.target);'
        'var r=await fetch(\'/upload\',{method:\'POST\',body:fd});'
        'var d=await r.json();'
        'if(d.session_id)window.location.href=\'/watch?session=\'+d.session_id;'
        'else alert(\'Error: \'+(d.error||\'unknown\'));});'
        '</script></main>'
    )


def render_watch(session_id: str, source: str) -> HTMLResponse:
    js = _WS_JS.replace('{sid}', session_id)
    return _page('Session ' + session_id[:8],
        '<main class="container">'
        '<header class="watch-header">'
        '<h1>Squat Rep Counter</h1>'
        '<nav><a href="/">Home</a><a href="/sessions">Sessions</a></nav></header>'
        '<div class="watch-layout">'
        '<div class="video-panel">'
        '<img id="vs" src="/video/' + session_id + '" alt="Stream"></div>'
        '<div class="data-panel" id="dp">'
        '<div class="metric rep-count">'
        '<span class="metric-label">Reps</span>'
        '<span class="metric-value" id="rc">0</span></div>'
        '<div class="metric">'
        '<span class="metric-label">Angle</span>'
        '<span class="metric-value" id="ag">&mdash;</span></div>'
        '<div class="metric">'
        '<span class="metric-label">State</span>'
        '<span class="metric-value" id="st">&mdash;</span></div>'
        '<div class="metric">'
        '<span class="metric-label">FPS</span>'
        '<span class="metric-value" id="fp">0</span></div>'
        '<div class="metric">'
        '<span class="metric-label">Visibility</span>'
        '<span class="metric-value" id="vi">&mdash;</span></div>'
        '<div class="badge-row">'
        '<span id="bp" class="badge hidden">PAUSED</span>'
        '<span id="bpr" class="badge hidden">PARTIAL</span>'
        '<span id="bl" class="badge badge-danger hidden">LOST TRACK</span>'
        '<span id="bu" class="badge badge-warning hidden">UNCALIBRATED</span>'
        '<span id="bb" class="badge badge-ok hidden">COMPLETE</span></div>'
        '<div class="session-controls">'
        '<button id="btn-stop" class="btn-danger" onclick="stopSess()">Stop &amp; Save</button>'
        '<a id="dl" href="#" style="display:none" class="btn">'
        '&#x1F4E5; Download CSV</a></div></div></div>'
        '<script>' + js + '</script></main>'
    )


def render_sessions(sessions: list[dict[str, Any]]) -> HTMLResponse:
    rows = ''
    for s in sessions:
        sid = s.get('id', '')
        rows += (
            '<tr><td><code>' + sid[:8] + '&hellip;</code></td>'
            '<td>' + (s.get('label', '') or '&mdash;') + '</td>'
            '<td>' + s.get('source', '') + '</td>'
            '<td>' + str(s.get('duration_sec', '')) + 's</td>'
            '<td>' + str(s.get('fps', '')) + '</td>'
            '<td><strong>' + str(s.get('total_reps', 0)) + '</strong></td>'
            '<td>' + str(s.get('full_reps', 0)) + '</td>'
            '<td>' + str(s.get('partial_reps', 0)) + '</td>'
            '<td>' + str(s.get('total_frames', 0)) + '</td>'
            '<td class="download-links">'
            '<a href="/session/' + sid + '/download?format=csv">CSV</a>'
            '<a href="/session/' + sid + '/download?format=json">JSON</a>'
            '</td></tr>'
        )
    empty = (
        '' if sessions
        else '<p class="empty-state">No sessions yet. <a href="/">Start monitoring</a></p>'
    )
    return _page('Sessions',
        '<main class="container"><header><h1>Sessions</h1>'
        '<nav><a href="/">Home</a></nav></header>'
        '<table class="session-table"><thead><tr>'
        '<th>ID</th><th>Label</th><th>Source</th><th>Duration</th><th>FPS</th>'
        '<th>Reps</th><th>Full</th><th>Partial</th><th>Frames</th><th>Download</th>'
        '</tr></thead><tbody>' + rows + '</tbody></table>'
        + empty + '</main>'
    )


__all__ = ['render_index', 'render_watch', 'render_sessions']
