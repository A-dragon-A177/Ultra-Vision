"""Vision web dashboard — runs on port 8080, localhost only.

Access at: http://localhost:8080
Shows: agents, procedures, run history, facts, trigger a procedure.
Speak page: http://localhost:8080/speak  (animated Vision face + TTS)
"""
import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response, StreamingResponse

ROOT = Path(os.environ.get("VISION_HOME", Path(__file__).resolve().parent.parent))
DB_PATH = ROOT / "data" / "vision.db"

app = FastAPI(title="Vision Dashboard", docs_url=None, redoc_url=None)

_CSS = """
body{font-family:system-ui,sans-serif;max-width:900px;margin:0 auto;padding:1rem 2rem;background:#0f0f0f;color:#e8e8e8}
h1{color:#7dd3fc;margin-bottom:.5rem}h2{color:#a5b4fc;border-bottom:1px solid #333;padding-bottom:.3rem}
a{color:#7dd3fc;text-decoration:none}.card{background:#1a1a1a;border:1px solid #333;border-radius:8px;padding:1rem;margin:.5rem 0}
.tag{background:#1e3a5f;color:#7dd3fc;padding:2px 8px;border-radius:4px;font-size:.8rem;margin-right:4px}
.tag.green{background:#14532d;color:#86efac}.tag.red{background:#450a0a;color:#fca5a5}
.tag.yellow{background:#451a03;color:#fcd34d}form{display:inline}
button{background:#1e3a5f;color:#7dd3fc;border:1px solid #3b82f6;padding:6px 14px;border-radius:4px;cursor:pointer}
button:hover{background:#1d4ed8}pre{background:#111;padding:.8rem;border-radius:4px;overflow-x:auto;font-size:.85rem}
table{width:100%;border-collapse:collapse}td,th{padding:.4rem .8rem;border-bottom:1px solid #333;text-align:left}
th{color:#a5b4fc;font-weight:600}.muted{color:#888;font-size:.85rem}
"""

def _db():
    if not DB_PATH.exists():
        return None
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def _load_agents():
    agents = {}
    for f in sorted((ROOT / "agents").glob("*.md")):
        lines = f.read_text(encoding="utf-8").splitlines()
        meta = {}
        if lines and lines[0] == "---":
            for line in lines[1:]:
                if line == "---":
                    break
                if ":" in line:
                    k, _, v = line.partition(":")
                    meta[k.strip()] = v.strip()
        agents[f.stem] = meta
    return agents


def _load_procs():
    procs = {}
    for f in sorted((ROOT / "procedures").glob("*.md")):
        lines = f.read_text(encoding="utf-8").splitlines()
        meta = {}
        if lines and lines[0] == "---":
            for line in lines[1:]:
                if line == "---":
                    break
                if ":" in line:
                    k, _, v = line.partition(":")
                    meta[k.strip()] = v.strip()
        procs[f.stem] = meta
    return procs


@app.get("/favicon.ico")
async def favicon():
    return Response(status_code=204)


@app.get("/", response_class=HTMLResponse)
async def home():
    agents = _load_agents()
    procs = _load_procs()
    c = _db()
    runs_html, facts_html = "", ""

    if c:
        runs = c.execute(
            "SELECT id, procedure, step, status, ts FROM runs ORDER BY id DESC LIMIT 20"
        ).fetchall()
        status_colors = {"done": "green", "running": "yellow", "paused": "yellow",
                         "asking": "yellow", "stopped": "red"}
        runs_rows = "".join(
            f"<tr><td>{r['id']}</td><td>{r['procedure']}</td>"
            f"<td>{r['step']}</td>"
            f"<td><span class='tag {status_colors.get(r['status'], '')}'>{r['status']}</span></td>"
            f"<td class='muted'>{datetime.fromtimestamp(r['ts']).strftime('%d %b %H:%M')}</td></tr>"
            for r in runs
        )
        runs_html = f"<table><tr><th>#</th><th>Procedure</th><th>Step</th><th>Status</th><th>Time</th></tr>{runs_rows}</table>"

        facts = c.execute("SELECT id, text FROM facts ORDER BY id").fetchall()
        facts_html = "".join(
            f"<div class='card'>{f['id']}. {f['text']} "
            f"<form action='/forget/{f['id']}' method='post'>"
            f"<button style='padding:2px 8px;font-size:.8rem;background:#450a0a;border-color:#7f1d1d'>Forget</button>"
            f"</form></div>"
            for f in facts
        ) or "<p class='muted'>Nothing saved yet.</p>"
        c.close()

    agents_html = "".join(
        f"<div class='card'><b>{name.title()}</b> <span class='tag'>{meta.get('title','')}</span>"
        + ("<span class='tag green'>Groq</span>" if meta.get("quality") == "true" else "")
        + ("<span class='tag'>web search</span>" if meta.get("web_search") == "true" else "")
        + f"<br><span class='muted'>{meta.get('handles','')}</span></div>"
        for name, meta in agents.items()
    )

    proc_options = "".join(f"<option value='{name}'>{name} — {meta.get('description','')}</option>"
                           for name, meta in procs.items())

    return HTMLResponse(f"""<!doctype html><html><head><meta charset=utf-8>
<title>Vision Dashboard</title><style>{_CSS}</style></head><body>
<h1>Vision Dashboard</h1>
<p class='muted'>Your AI team command centre · <a href='/facts'>Facts</a> · <a href='/runs'>All runs</a></p>

<h2>Run a procedure</h2>
<form action='/run' method='post'>
  <select name='name' style='background:#1a1a1a;color:#e8e8e8;border:1px solid #333;padding:6px 10px;border-radius:4px'>{proc_options}</select>
  <input name='request' placeholder='Extra details (optional)' style='background:#1a1a1a;color:#e8e8e8;border:1px solid #333;padding:6px 10px;border-radius:4px;width:260px'>
  <button type='submit'>Run</button>
</form>

<h2>Recent runs</h2>{runs_html or "<p class='muted'>No runs yet.</p>"}

<h2>Team</h2>{agents_html}

<h2>Facts the team knows</h2>{facts_html}
</body></html>""")


@app.post("/run")
async def trigger_run(name: str = Form(...), request: str = Form("")):
    # Write a trigger file — main.py picks it up on next poll
    trigger = ROOT / "data" / "dashboard_trigger.json"
    trigger.write_text(json.dumps({"procedure": name, "request": request}), encoding="utf-8")
    return RedirectResponse("/?triggered=1", status_code=303)


@app.post("/forget/{fact_id}")
async def forget(fact_id: int):
    c = _db()
    if c:
        c.execute("DELETE FROM facts WHERE id = ?", (fact_id,))
        c.commit()
        c.close()
    return RedirectResponse("/", status_code=303)


_SPEAK_PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Vision · AI Command Center</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:100%;height:100%;overflow:hidden;background:#000814}
body{
  font-family:'Courier New',monospace;
  color:#00d4ff;
  user-select:none;
  position:relative;
}

/* ── full-screen avatar ── */
#av{
  position:fixed;inset:0;width:100%;height:100%;
  object-fit:contain;object-position:center bottom;
  z-index:0;
  transition:filter .4s ease, opacity .35s ease;
}
body.speaking #av{
  animation:glow .45s ease-in-out infinite alternate;
}
@keyframes glow{
  from{filter:brightness(1.05) drop-shadow(0 0 25px rgba(0,200,255,.5)) drop-shadow(0 0 60px rgba(0,120,255,.3))}
  to  {filter:brightness(1.35) drop-shadow(0 0 90px rgba(0,220,255,1)) drop-shadow(0 0 180px rgba(0,160,255,.65)) drop-shadow(0 0 260px rgba(0,80,255,.35))}
}

/* vignette: blends white bg edges into dark page */
.vig{
  position:fixed;inset:0;z-index:1;pointer-events:none;
  background:
    radial-gradient(ellipse 72% 90% at 50% 55%,
      transparent 55%,
      rgba(0,8,20,.55) 75%,
      rgba(0,8,20,.88) 90%,
      #000814 100%);
}

/* scanlines overlay */
.scan{
  position:fixed;inset:0;z-index:2;pointer-events:none;
  background:repeating-linear-gradient(0deg,
    transparent,transparent 2px,
    rgba(0,212,255,.012) 2px,rgba(0,212,255,.012) 4px);
}

/* ── HUD top bar ── */
.hud{
  position:fixed;top:0;left:0;right:200px;z-index:11;
  display:flex;justify-content:space-between;align-items:center;
  padding:10px 22px;
  background:linear-gradient(to bottom,rgba(0,8,20,.92),rgba(0,8,20,.0));
  font-size:11px;letter-spacing:2px;
}
.hud-l{display:flex;align-items:center;gap:10px}
.dot{width:8px;height:8px;border-radius:50%;background:#00d4ff;animation:blink 2s infinite}
@keyframes blink{0%,100%{opacity:1;box-shadow:0 0 8px #00d4ff}50%{opacity:.2;box-shadow:none}}
.hud-r{display:flex;gap:16px;font-size:10px;color:rgba(0,212,255,.5);align-items:center}
#agname{
  cursor:pointer;color:#00d4ff;font-size:11px;letter-spacing:3px;
  border:1px solid rgba(0,212,255,.3);padding:3px 10px;
  transition:all .2s;
}
#agname:hover{background:rgba(0,212,255,.12);border-color:rgba(0,212,255,.7)}

/* ── agent picker dropdown ── */
.agent-sel{
  position:fixed;top:44px;right:200px;z-index:20;
  background:rgba(0,8,20,.97);
  border:1px solid rgba(0,212,255,.3);
  display:flex;flex-direction:column;gap:2px;padding:6px;
  min-width:120px;
}
.agent-btn{
  background:none;border:none;color:rgba(0,212,255,.55);
  font-family:'Courier New',monospace;font-size:9px;letter-spacing:2.5px;
  cursor:pointer;text-align:left;padding:5px 10px;text-transform:uppercase;
  transition:all .15s;
}
.agent-btn:hover,.agent-btn.active{
  color:#00d4ff;background:rgba(0,212,255,.1);
  text-shadow:0 0 8px rgba(0,212,255,.6);
}

/* ── bottom panel ── */
.bot{
  position:fixed;bottom:0;left:0;right:200px;z-index:10;
  background:linear-gradient(to top,rgba(0,5,16,.97) 70%,transparent);
  padding:28px 24px 20px;
  display:flex;flex-direction:column;align-items:center;gap:10px;
}
.reply{
  font-size:14px;color:rgba(0,212,255,.88);text-align:center;
  min-height:28px;max-width:800px;line-height:1.65;
  font-style:italic;letter-spacing:.3px;
  text-shadow:0 0 12px rgba(0,212,255,.4);
}
.irow{display:flex;gap:8px;width:100%;max-width:660px}
.inp{
  flex:1;background:rgba(0,15,40,.85);
  border:1px solid rgba(0,212,255,.4);
  color:#00d4ff;padding:11px 15px;
  font-family:inherit;font-size:14px;outline:none;letter-spacing:.5px;
  backdrop-filter:blur(4px);
}
.inp::placeholder{color:rgba(0,212,255,.3)}
.inp:focus{border-color:#00d4ff;box-shadow:0 0 14px rgba(0,212,255,.25)}
.sbtn{
  background:rgba(0,212,255,.13);
  border:1px solid rgba(0,212,255,.6);
  color:#00d4ff;padding:11px 20px;
  font-family:inherit;font-size:12px;letter-spacing:2.5px;cursor:pointer;
  transition:all .2s;backdrop-filter:blur(4px);
}
.sbtn:hover{background:rgba(0,212,255,.3);box-shadow:0 0 18px rgba(0,212,255,.45)}
.sbtn:disabled{opacity:.3;cursor:not-allowed}
.stl{font-size:10px;letter-spacing:3px;color:rgba(0,212,255,.35)}

/* ── activity log panel ── */
.log-panel{
  position:fixed;right:0;top:44px;bottom:155px;z-index:10;
  width:200px;
  background:rgba(0,3,12,.88);
  border-left:1px solid rgba(0,212,255,.2);
  border-bottom:1px solid rgba(0,212,255,.15);
  backdrop-filter:blur(8px);
  display:flex;flex-direction:column;
  overflow:hidden;
}
.log-title{
  font-size:9px;letter-spacing:3px;color:rgba(0,212,255,.45);
  padding:7px 10px 5px;border-bottom:1px solid rgba(0,212,255,.12);
  flex-shrink:0;
}
.log-tabs{
  display:flex;flex-wrap:wrap;gap:3px;padding:5px 6px 4px;
  border-bottom:1px solid rgba(0,212,255,.1);flex-shrink:0;
}
.log-tab{
  font-size:7px;letter-spacing:1.5px;cursor:pointer;
  border:1px solid rgba(0,212,255,.18);color:rgba(0,212,255,.35);
  background:none;padding:2px 5px;
  font-family:'Courier New',monospace;text-transform:uppercase;
  transition:all .15s;
}
.log-tab.active,.log-tab:hover{
  color:#00d4ff;border-color:rgba(0,212,255,.55);
  background:rgba(0,212,255,.1);
}
.log-body{
  flex:1;overflow-y:auto;padding:5px;
  display:flex;flex-direction:column;gap:5px;
}
.log-body::-webkit-scrollbar{width:3px}
.log-body::-webkit-scrollbar-track{background:transparent}
.log-body::-webkit-scrollbar-thumb{background:rgba(0,212,255,.25)}
.log-entry{
  font-size:9px;line-height:1.5;
  border-left:2px solid rgba(0,212,255,.25);
  padding:3px 6px;
}
.log-entry .log-t{color:rgba(0,212,255,.22);font-size:8px;margin-bottom:1px}
.log-entry .log-q{color:rgba(0,212,255,.38);margin-bottom:2px}
.log-entry .log-a{color:rgba(0,212,255,.7)}
</style>
</head>
<body>

<img id="av" src="/agent-avatar/vision" alt="Vision" onerror="this.style.opacity='0'">
<div class="vig"></div>
<div class="scan"></div>

<div class="hud">
  <div class="hud-l">
    <div class="dot"></div>
    <span style="opacity:.6">AI COMMAND CENTER</span>
  </div>
  <div class="hud-r">
    <span id="st">STATUS: IDLE</span>
    <span id="ts">--:--:--</span>
    <span id="agname" onclick="toggleAgSel()" title="Switch agent">VISION</span>
  </div>
</div>

<div class="agent-sel" id="agsel" style="display:none"></div>

<div class="log-panel" id="logPanel">
  <div class="log-title">▸ AGENT ACTIVITY</div>
  <div class="log-tabs" id="logTabs"></div>
  <div class="log-body" id="logBody">
    <div class="log-entry"><div class="log-t">waiting…</div></div>
  </div>
</div>

<div class="bot">
  <p class="reply" id="sub">Initialising…</p>
  <div class="irow">
    <input class="inp" id="txt" type="text"
           placeholder="Speak to Vision… (English / Tamil)" autocomplete="off"/>
    <button class="sbtn" id="btn" onclick="go()">SEND</button>
  </div>
  <span class="stl" id="stl">AWAITING INPUT</span>
</div>

<script>
const btn=document.getElementById('btn'),txt=document.getElementById('txt'),
      sub=document.getElementById('sub'),stl=document.getElementById('stl'),
      sts=document.getElementById('st'),ts=document.getElementById('ts'),
      av=document.getElementById('av'),agname=document.getElementById('agname'),
      agsel=document.getElementById('agsel');

const AGENTS=['vision','jarvis','ultron','zola','jim','friday','edith','veronica','jocasta','herbie'];
let curAgent='vision';

// Build agent picker
AGENTS.forEach(a=>{
  const b=document.createElement('button');
  b.className='agent-btn'+(a==='vision'?' active':'');
  b.dataset.agent=a;
  b.textContent=a.toUpperCase();
  b.onclick=()=>{switchAgent(a);stl.textContent='SWITCHED TO '+a.toUpperCase()};
  agsel.appendChild(b);
});

function toggleAgSel(){
  agsel.style.display=agsel.style.display==='none'?'flex':'none';
}
document.addEventListener('click',e=>{
  if(!agsel.contains(e.target)&&e.target!==agname) agsel.style.display='none';
});

function switchAgent(name){
  if(!AGENTS.includes(name))return;
  curAgent=name;
  av.style.opacity='0';
  setTimeout(()=>{
    av.src='/agent-avatar/'+name+'?t='+Date.now();
    av.onload=()=>{av.style.opacity='1'};
    av.onerror=()=>{av.style.opacity='0'};
  },200);
  agname.textContent=name.toUpperCase();
  agsel.style.display='none';
  document.querySelectorAll('.agent-btn').forEach(b=>{
    b.classList.toggle('active',b.dataset.agent===name);
  });
  txt.placeholder='Speak to '+name.charAt(0).toUpperCase()+name.slice(1)+'… (English / Tamil)';
  if(typeof updateLogPanelAgent==='function') updateLogPanelAgent();
}

function detectSwitch(q){
  const low=q.toLowerCase().trim();
  for(const a of AGENTS){
    const triggers=[
      'call '+a,'switch to '+a,'connect to '+a,'talk to '+a,
      'bring '+a,'summon '+a,'get me '+a,'speak to '+a,
      'connect me to '+a,'let me talk to '+a,'pass me to '+a,
      'transfer to '+a,'back to '+a,'bring in '+a
    ];
    if(triggers.some(p=>low.includes(p))) return a;
  }
  return null;
}

setInterval(()=>{ts.textContent=new Date().toLocaleTimeString('en-IN',{hour12:false})},1000);

function isTamil(text){
  return /[஀-௿]/.test(text);
}

function stripMd(t){
  return t
    .replace(/\*\*(.+?)\*\*/gs,'$1')
    .replace(/\*(.+?)\*/gs,'$1')
    .replace(/#{1,6} /g,'')
    .replace(/`(.+?)`/gs,'$1')
    .replace(/\[(.+?)\]\(.+?\)/g,'$1')
    .replace(/^\s*[-*+•]\s/gm,'')
    .replace(/\n{2,}/g,' ')
    .trim();
}

async function speak(text, displayText){
  stl.textContent='SYNTHESISING…';
  sts.textContent='STATUS: THINKING';
  try{
    const r=await fetch('/api/tts',{method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({text:stripMd(text),agent:curAgent})});
    if(!r.ok) throw new Error('TTS '+r.status);
    const url=URL.createObjectURL(await r.blob());
    const audio=new Audio(url);
    audio.addEventListener('ended',()=>{
      document.body.classList.remove('speaking');
      sts.textContent='STATUS: IDLE';
      stl.textContent='AWAITING INPUT';
      URL.revokeObjectURL(url);
    });
    // Glow + subtitle appear exactly when audio starts — not before
    audio.addEventListener('play',()=>{
      document.body.classList.add('speaking');
      sts.textContent='STATUS: SPEAKING';
      stl.textContent='SPEAKING…';
      if(displayText!==undefined) sub.textContent=displayText;
    });
    await audio.play();
  }catch(e){
    document.body.classList.remove('speaking');
    sts.textContent='STATUS: ERROR';
    stl.textContent='TTS ERROR';
    if(displayText!==undefined) sub.textContent=displayText;
  }
}

async function go(){
  const q=txt.value.trim();
  if(!q)return;

  // ── agent-switch intercept ──────────────────────────────────────
  const sw=detectSwitch(q);
  if(sw && sw!==curAgent){
    switchAgent(sw);
    btn.disabled=true;txt.value='';
    sts.textContent='STATUS: CONNECTING';
    stl.textContent='ROUTING TO '+sw.toUpperCase()+'…';
    sub.textContent='⟳  Connecting to '+sw.charAt(0).toUpperCase()+sw.slice(1)+'…';
    await new Promise(r=>setTimeout(r,900));
    try{
      const r=await fetch('/api/ask',{method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({agent:sw,
          message:'Vision has connected us. Greet the user and introduce yourself in 1-2 sentences.'})});
      if(!r.ok) throw new Error('Ask '+r.status);
      const d=await r.json();
      const ans=d.reply||d.text||JSON.stringify(d);
      await speak(ans, ans);
    }catch(e){
      sub.textContent='Connection error: '+e.message;
      sts.textContent='STATUS: ERROR';stl.textContent='ERROR';
    }finally{
      btn.disabled=false;
      if(!document.body.classList.contains('speaking'))stl.textContent='AWAITING INPUT';
    }
    return;
  }

  // ── normal ask ─────────────────────────────────────────────────
  btn.disabled=true;txt.value='';
  sts.textContent='STATUS: THINKING';
  stl.textContent='PROCESSING…';sub.textContent='…';
  try{
    const r=await fetch('/api/ask',{method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({agent:curAgent,message:q,lang:isTamil(q)?'ta':'en'})});
    if(!r.ok) throw new Error('Ask '+r.status);
    const d=await r.json();
    const ans=d.reply||d.text||JSON.stringify(d);
    await speak(ans, ans);
  }catch(e){
    sub.textContent='Error: '+e.message;
    sts.textContent='STATUS: ERROR';stl.textContent='ERROR';
  }finally{
    btn.disabled=false;
    if(!document.body.classList.contains('speaking'))stl.textContent='AWAITING INPUT';
  }
}

txt.addEventListener('keydown',e=>{if(e.key==='Enter')go();});
setTimeout(()=>{txt.value='Introduce yourself in one sentence.';go();},800);

// ── live activity log panel ───────────────────────────────────────
const logPanel=document.getElementById('logPanel');
const logTabs=document.getElementById('logTabs');
const logBody=document.getElementById('logBody');
let logAgent=curAgent;

AGENTS.forEach(a=>{
  const b=document.createElement('button');
  b.className='log-tab'+(a==='vision'?' active':'');
  b.dataset.agent=a;
  b.textContent=a.toUpperCase().slice(0,3);
  b.onclick=()=>{
    logAgent=a;
    document.querySelectorAll('.log-tab').forEach(x=>x.classList.toggle('active',x.dataset.agent===a));
    fetchActivity();
  };
  logTabs.appendChild(b);
});

async function fetchActivity(){
  try{
    const r=await fetch('/api/agent-activity?agent='+logAgent);
    if(!r.ok)return;
    const d=await r.json();
    const entries=d.entries||[];
    if(!entries.length){
      logBody.innerHTML='<div class="log-entry"><div class="log-t">no activity yet</div></div>';
      return;
    }
    logBody.innerHTML=entries.slice().reverse().map(e=>`
      <div class="log-entry">
        <div class="log-t">${e.time}</div>
        <div class="log-q">▸ ${e.question.length>55?e.question.slice(0,55)+'…':e.question}</div>
        <div class="log-a">${e.answer.length>110?e.answer.slice(0,110)+'…':e.answer}</div>
      </div>`).join('');
  }catch{}
}

function updateLogPanelAgent(){
  logAgent=curAgent;
  document.querySelectorAll('.log-tab').forEach(x=>x.classList.toggle('active',x.dataset.agent===curAgent));
  fetchActivity();
}

fetchActivity();
setInterval(fetchActivity,3000);
</script>
</body>
</html>"""


_SPEAK_PAGE_SIMPLE = r"""<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Vision Speak (simple)</title>
<style>
:root{--accent:#60c8ff;--accent2:#a78bfa;--bg:#05080f;--surface:#0d1117;--text:#e0e8ff;--muted:#4a5568}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);font-family:'Segoe UI',system-ui,sans-serif;
  min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2rem;padding:2rem}

/* ── face ── */
.face-wrap{position:relative;width:280px;height:280px;cursor:default}

.face-img{width:100%;height:100%;object-fit:cover;border-radius:50%;
  border:2px solid rgba(96,200,255,.35);display:block;position:relative;z-index:2}

.ring{position:absolute;border-radius:50%;border:2px solid transparent;z-index:1}
.r1{inset:-14px;animation:spin1 5s linear infinite;border-top-color:rgba(96,200,255,.6)}
.r2{inset:-24px;animation:spin2 8s linear infinite;border-right-color:rgba(167,139,250,.4)}
.r3{inset:-36px;animation:spin1 12s linear infinite reverse;border-bottom-color:rgba(96,200,255,.2)}
@keyframes spin1{to{transform:rotate(360deg)}}
@keyframes spin2{to{transform:rotate(-360deg)}}

.glow{position:absolute;inset:-4px;border-radius:50%;z-index:0;
  box-shadow:0 0 0px 0px transparent;transition:box-shadow .3s}
.speaking .glow{animation:glow 0.6s ease-in-out infinite alternate}
@keyframes glow{
  from{box-shadow:0 0 20px 4px rgba(96,200,255,.25)}
  to{box-shadow:0 0 60px 20px rgba(96,200,255,.5)}}

/* mouth overlay — synced by Web Audio API */
.mouth{position:absolute;bottom:21%;left:50%;transform:translateX(-50%);
  width:52px;height:8px;background:rgba(0,0,0,.5);border-radius:50%;z-index:3;
  transition:height .04s,background .2s}
.speaking .mouth{background:rgba(0,0,0,.7)}

/* ── subtitle ── */
.subtitle{max-width:520px;text-align:center;min-height:4rem;
  font-size:1.1rem;line-height:1.65;color:var(--text);
  background:rgba(13,17,23,.8);padding:1rem 1.5rem;border-radius:14px;
  border:1px solid rgba(96,200,255,.15);transition:opacity .4s}

/* ── input row ── */
.input-row{display:flex;gap:.6rem;width:100%;max-width:520px}
.input-row input{flex:1;background:var(--surface);border:1px solid var(--muted);
  border-radius:9px;padding:.7rem 1rem;color:var(--text);font-size:1rem;outline:none;
  transition:border-color .2s}
.input-row input:focus{border-color:var(--accent)}
.input-row button{background:var(--accent);color:var(--bg);border:none;border-radius:9px;
  padding:.7rem 1.4rem;font-size:1rem;font-weight:700;cursor:pointer;transition:opacity .2s;white-space:nowrap}
.input-row button:hover{opacity:.85}
.input-row button:disabled{opacity:.35;cursor:not-allowed}

.status-bar{font-size:.8rem;color:var(--muted);letter-spacing:.03em}
.name-tag{font-size:.75rem;color:var(--accent);letter-spacing:.15em;text-transform:uppercase;font-weight:600}
</style>
</head>
<body>
<div class="name-tag">VISION</div>

<div class="face-wrap" id="fw">
  <div class="ring r1"></div><div class="ring r2"></div><div class="ring r3"></div>
  <div class="glow"></div>
  <img class="face-img" id="fi" src="/face-image" onerror="this.style.display='none'"
    onerror="this.src='data:image/svg+xml;utf8,<svg xmlns=\'http://www.w3.org/2000/svg\' width=\'280\' height=\'280\'><circle cx=\'140\' cy=\'140\' r=\'140\' fill=\'%230d1117\'/><circle cx=\'140\' cy=\'110\' r=\'50\' fill=\'%2360c8ff\' opacity=\'.2\'/><text x=\'140\' y=\'210\' text-anchor=\'middle\' fill=\'%2360c8ff\' font-size=\'80\' font-family=\'sans-serif\'>V</text></svg>'"
    alt="Vision">
  <div class="mouth" id="mouth"></div>
</div>

<div class="subtitle" id="sub">Vision is ready. Ask me anything.</div>

<div class="input-row">
  <input id="txt" type="text" placeholder="Ask Vision…" autocomplete="off">
  <button id="btn" onclick="askVision()">Ask</button>
</div>

<div class="status-bar" id="stat">Idle &nbsp;·&nbsp; <a href="/" style="color:var(--muted)">Dashboard</a></div>

<script>
const fw=document.getElementById('fw'),sub=document.getElementById('sub'),
      mouth=document.getElementById('mouth'),btn=document.getElementById('btn'),
      stat=document.getElementById('stat'),txt=document.getElementById('txt');

let ctx=null,analyser=null,animId=null;

function initAudio(){
  if(ctx)return;
  ctx=new AudioContext();
  analyser=ctx.createAnalyser();
  analyser.fftSize=512;
  analyser.smoothingTimeConstant=0.75;
}

function animateFace(){
  if(!analyser){return;}
  const d=new Uint8Array(analyser.frequencyBinCount);
  analyser.getByteFrequencyData(d);
  const slice=Array.from(d.slice(2,22));
  const avg=slice.reduce((a,b)=>a+b,0)/slice.length;
  const o=Math.min(avg/100,1);
  mouth.style.height=`${8+o*28}px`;
  animId=requestAnimationFrame(animateFace);
}

function stopAnim(){
  if(animId){cancelAnimationFrame(animId);animId=null;}
  mouth.style.height='8px';
  fw.classList.remove('speaking');
}

async function playAudio(text){
  stat.textContent='Generating speech…';
  const r=await fetch('/api/tts',{
    method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({text})
  });
  if(!r.ok){
    const e=await r.json().catch(()=>({detail:'TTS error'}));
    throw new Error(e.detail||'TTS failed');
  }
  const ab=await r.arrayBuffer();
  initAudio();
  ctx.resume();
  const buf=await ctx.decodeAudioData(ab);
  const src=ctx.createBufferSource();
  src.buffer=buf;
  src.connect(analyser);
  src.connect(ctx.destination);
  fw.classList.add('speaking');
  stat.textContent='Speaking…';
  animateFace();
  return new Promise(res=>{
    src.start();
    src.onended=()=>{stopAnim();res();};
  });
}

async function askVision(){
  const q=txt.value.trim();
  if(!q)return;
  btn.disabled=true;
  sub.style.opacity='.5';
  stat.textContent='Thinking…';
  try{
    // 1. Ask the LLM
    const r=await fetch('/api/ask',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({agent:'vision',message:q})
    });
    if(!r.ok)throw new Error('Ask API failed');
    const d=await r.json();
    const ans=d.reply||d.text||d.answer||JSON.stringify(d);
    sub.textContent=ans;
    sub.style.opacity='1';
    // 2. Speak it
    await playAudio(ans);
  }catch(e){
    sub.textContent='Error: '+e.message;
    sub.style.opacity='1';
    stat.textContent='Error';
  }finally{
    btn.disabled=false;
    stat.textContent='Idle';
  }
}

// Enter key
txt.addEventListener('keydown',e=>{if(e.key==='Enter')askVision();});

// Auto-greet on first open
setTimeout(()=>{
  txt.value='Introduce yourself in one sentence.';
  askVision();
},800);
</script>
</body>
</html>"""


_agent_log: dict = {}


@app.get("/speak", response_class=HTMLResponse)
async def speak_page():
    return HTMLResponse(_SPEAK_PAGE)


@app.get("/face-image")
async def face_image():
    for ext, mt in [("webp", "image/webp"), ("png", "image/png"), ("jpg", "image/jpeg")]:
        face = ROOT / "data" / f"face.{ext}"
        if face.exists():
            return Response(content=face.read_bytes(), media_type=mt)
    return Response(status_code=404)


@app.get("/agent-avatar/{name}")
async def agent_avatar(name: str):
    name = name.lower().strip()
    # prefer PNG (transparent) then webp then jpg
    for ext, mt in [("png", "image/png"), ("webp", "image/webp"), ("jpg", "image/jpeg")]:
        f = ROOT / "data" / "avatars" / f"{name}.{ext}"
        if f.exists():
            return Response(content=f.read_bytes(), media_type=mt)
    # fallback to face image
    for ext, mt in [("png", "image/png"), ("webp", "image/webp"), ("jpg", "image/jpeg")]:
        f = ROOT / "data" / f"face.{ext}"
        if f.exists():
            return Response(content=f.read_bytes(), media_type=mt)
    return Response(status_code=404)


@app.post("/api/tts")
async def api_tts(request: Request):
    body = await request.json()
    text = body.get("text", "").strip()
    agent = body.get("agent", "vision")
    if not text:
        return JSONResponse({"detail": "No text provided"}, status_code=400)
    try:
        from .tts import synthesize
        audio = await synthesize(text, agent=agent)
        return Response(content=audio, media_type="audio/mpeg")
    except RuntimeError as e:
        return JSONResponse({"detail": str(e)}, status_code=503)
    except Exception as e:
        return JSONResponse({"detail": f"TTS error: {e}"}, status_code=500)


@app.post("/api/ask")
async def api_ask(request: Request):
    import datetime as _dt
    body = await request.json()
    agent = body.get("agent", "vision")
    message = body.get("message", "").strip()
    lang = body.get("lang", "en")
    if not message:
        return JSONResponse({"detail": "No message provided"}, status_code=400)
    # Inject language instruction so LLM replies in the same language as the user
    if lang == "ta":
        llm_message = "[Respond only in Tamil (தமிழ்). Do not use English.] " + message
    else:
        llm_message = "[Respond only in English. Do not use Tamil.] " + message
    try:
        from .core import ask, load_agents, load_procedures, run_procedure, route
        agents = load_agents()
        procs = load_procedures()
        # Route to detect if this message triggers a procedure (e.g. "Friday, create a reel")
        kind, name, rest = await route(message, agents, procs)
        if kind == "procedure" and name in procs:
            parts = []
            async for ev in run_procedure(procs[name], agents, request=rest):
                if ev["type"] == "step":
                    parts.append(f"**Step {ev['n']}/{ev['total']} – {ev['title']}**\n{ev['output']}")
                elif ev["type"] == "pause":
                    parts.append("Waiting for your approval to continue.")
                    break
                elif ev["type"] == "ask":
                    parts.append(f"{ev['agent'].title()} needs your input: {ev['question']}")
                    break
                elif ev["type"] == "done":
                    parts.append("Procedure complete.")
            reply = "\n\n".join(parts) if parts else f"Starting procedure: {name}"
        else:
            # name is the routed agent; fall back to request body agent if routing gave chief
            if name not in agents:
                name = agent if agent in agents else "vision"
            # save_text=message saves the original (unprefixed) message in conversation history
            reply = await ask(name, llm_message, agents, save_text=message)
        return JSONResponse({"reply": reply})
    except Exception as e:
        return JSONResponse({"detail": str(e)}, status_code=500)


@app.get("/api/agent-activity")
async def api_agent_activity(agent: str = "vision"):
    """Read conversation history from SQLite — survives restarts."""
    try:
        from .core import db as _db
        agent = agent.lower()
        with _db() as c:
            rows = c.execute(
                "SELECT role, content, ts FROM messages WHERE agent = ? ORDER BY id DESC LIMIT 40",
                (agent,)
            ).fetchall()
        import datetime as _dt
        entries = []
        pairs = []
        # Pair user+assistant messages from most-recent first
        i = 0
        while i < len(rows):
            if rows[i]["role"] == "assistant" and i + 1 < len(rows) and rows[i + 1]["role"] == "user":
                pairs.append({
                    "time": _dt.datetime.fromtimestamp(rows[i]["ts"]).strftime("%H:%M:%S"),
                    "question": rows[i + 1]["content"],
                    "answer": rows[i]["content"],
                })
                i += 2
            else:
                i += 1
        # pairs are newest-first; return up to 15
        return JSONResponse({"agent": agent, "entries": list(reversed(pairs[:15]))})
    except Exception as e:
        return JSONResponse({"agent": agent, "entries": [], "error": str(e)})


def start_dashboard():
    import threading
    import uvicorn
    port = int(os.environ.get("DASHBOARD_PORT", "8080"))
    t = threading.Thread(
        target=uvicorn.run,
        kwargs={"app": "app.dashboard:app", "host": "0.0.0.0", "port": port, "log_level": "warning"},
        daemon=True,
    )
    t.start()
    return port
