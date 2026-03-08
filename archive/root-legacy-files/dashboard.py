#!/usr/bin/env python3
import os,json,time,subprocess,threading
from http.server import HTTPServer,SimpleHTTPRequestHandler

LEDGER="/opt/veil_os/ledger.json"
RUN="/opt/veil_os/var/run"

def get_organs():
    with open(LEDGER) as f: return [e.get("organ") for e in json.load(f) if e.get("organ")]

def is_running(n):
    pf=f"{RUN}/{n}.pid"
    if os.path.exists(pf):
        try:
            with open(pf) as f: pid=int(f.read().strip())
            os.kill(pid,0);return True
        except:pass
    return False

def status(): return {n:is_running(n) for n in get_organs()}

HTML='''<!DOCTYPE html><html><head><title>VEIL OS</title><style>
*{margin:0;padding:0}body{background:#0a0a0f;color:#0f8;font-family:monospace;padding:20px}
.h{text-align:center;padding:30px;border-bottom:2px solid #0f83}.h h1{font-size:3em;text-shadow:0 0 20px #0f8}
.st{display:flex;justify-content:center;gap:50px;margin:30px}.s{text-align:center;padding:20px 40px;background:#0f81;border:1px solid #0f83;border-radius:10px}
.s .n{font-size:3em;font-weight:bold}.run .n{color:#0f8}.stp .n{color:#f44}.tot .n{color:#48f}
.g{display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:8px;max-width:1400px;margin:0 auto}
.o{padding:12px 8px;text-align:center;border-radius:6px;font-size:.8em;transition:.5s}
.o.off{background:#f441;color:#f66}.o.on{background:#0f82;color:#0f8;box-shadow:0 0 15px #0f84;animation:p 2s infinite}
@keyframes p{50%{box-shadow:0 0 25px #0f86}}
.gl{font-size:1.4em;display:block;margin-bottom:4px}
.c{text-align:center;margin:30px}
button{background:linear-gradient(135deg,#0f8,#0a5);color:#000;border:0;padding:15px 40px;font-size:1.2em;font-weight:bold;border-radius:8px;cursor:pointer;margin:0 10px}
button:hover{transform:scale(1.05);box-shadow:0 0 30px #0f85}button.x{background:linear-gradient(135deg,#f44,#a22)}
.p{max-width:600px;margin:20px auto;height:30px;background:#fff1;border-radius:15px;overflow:hidden}
.pb{height:100%;background:linear-gradient(90deg,#0f8,#0fc);transition:.5s;box-shadow:0 0 20px #0f8}
</style></head><body>
<div class="h"><h1>🔱 VEIL OS</h1><div style="color:#888;margin-top:10px">Living Hospital Cybersecurity</div></div>
<div class="st"><div class="s run"><div class="n" id="r">0</div><div>ONLINE</div></div>
<div class="s stp"><div class="n" id="s">0</div><div>OFFLINE</div></div>
<div class="s tot"><div class="n" id="t">0</div><div>TOTAL</div></div></div>
<div class="p"><div class="pb" id="pb" style="width:0%"></div></div>
<div class="c"><button onclick="go()">⚡ ACTIVATE ALL</button><button class="x" onclick="stp()">🛑 SHUTDOWN</button></div>
<div class="g" id="g"></div>
<script>
const G={epic:'🏥',imprivata:'🔐',guardian:'🛡️',backup:'💾',quarantine:'🔒',firewall:'🔥',vault:'🏦',sentinel:'🗼',cortex:'🧠',mfa:'🔑',audit:'📋',canary:'🐤',forensic:'🔬',watchdog:'🐕',rollback:'⏪',gateway:'🚪',portal:'🌀',console:'🖥️',scheduler:'📅',keystore:'🗝️',router:'🔀',monitor:'👁️',logger:'📝',metrics:'📊',journal:'📔',init:'🌅',bios:'⚡',engine:'⚙️',queue:'📬',relay:'📡',bridge:'🌉',fabric:'🕸️',signal:'📶',emitter:'📢',daemon:'👻',loader:'📦',socket:'🔌',cache:'💨',clock:'🕐',linker:'🔗',dlp:'🛡️',phi:'🏥',rbac:'👥',session:'🎫',hospital:'🏥',auth:'🔑',driver:'🔧',dock:'🚢',matrix:'🔢',veilctl:'⚔️',fingerprint:'👆'};
let O={},X=0;
async function f(){O=await(await fetch('/status')).json();d()}
function d(){const n=Object.keys(O).sort(),r=n.filter(x=>O[x]).length;
document.getElementById('r').textContent=r;document.getElementById('s').textContent=n.length-r;
document.getElementById('t').textContent=n.length;document.getElementById('pb').style.width=(r/n.length*100)+'%';
document.getElementById('g').innerHTML=n.map(x=>`<div class="o ${O[x]?'on':'off'}"><span class="gl">${G[x]||'⚙️'}</span>${x}</div>`).join('')}
async function go(){if(X)return;X=1;await fetch('/start-all',{method:'POST'});X=0}
async function stp(){await fetch('/stop-all',{method:'POST'})}
f();setInterval(f,1000);
</script></body></html>'''

class H(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path=='/':self.send_response(200);self.send_header('Content-Type','text/html');self.end_headers();self.wfile.write(HTML.encode())
        elif self.path=='/status':self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(json.dumps(status()).encode())
        else:self.send_error(404)
    def do_POST(self):
        if self.path=='/start-all':threading.Thread(target=self.go,daemon=True).start();self.send_response(200);self.end_headers();self.wfile.write(b'OK')
        elif self.path=='/stop-all':subprocess.run(['veil','stop-all']);self.send_response(200);self.end_headers();self.wfile.write(b'OK')
    def go(self):
        for n in sorted(get_organs()):
            if not is_running(n):subprocess.run(['veil','start',n]);time.sleep(0.3)
    def log_message(self,*a):pass

print("🔱 Veil OS Dashboard: http://localhost:8888")
HTTPServer(('',8888),H).serve_forever()
