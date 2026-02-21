import "./styles.css";

/** CONFIG (matches your PyQt) */
const API_BASE = "http://localhost:9444/api/v1";
const API_KEY  = "vc_aceea537c874533b85bdb56d3e7835db40a1cc32eff8024b";

const C = {
  cyan:"#00e5ff", green:"#00ff6a", orange:"#ff8c00", red:"#ff4444", gold:"#fbbf24",
  dim:"#4a6a7a", text2:"#7baac4", border:"#1e3a4a"
};

type ThreatLevel = "NORMAL" | "ELEVATED" | "HIGH" | "CRITICAL" | "UNKNOWN";
type StatusResponse = {
  uptime_seconds?: number;
  threats?: { threat_level?: ThreatLevel; active_alerts?: number };
  organs?: { active?: number; total?: number };
  mesh?: { router_active?: boolean };
  api?: { websocket_clients?: number };
};
type Organ = { name?: string; tier?: "P0"|"P1"|"P2"; description?: string; unit?: string; active?: any; status?: string; };
type AlertItem = { severity?: string; message?: string; description?: string; timestamp?: string; };

function h<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  props: Record<string, any> = {},
  ...children: (HTMLElement|string|null|undefined)[]
){
  const el = document.createElement(tag);
  for (const [k,v] of Object.entries(props)){
    if (v == null) continue;
    if (k === "class") el.className = v;
    else if (k === "style") Object.assign(el.style, v);
    else if (k.startsWith("on") && typeof v === "function") (el as any)[k.toLowerCase()] = v;
    else el.setAttribute(k, String(v));
  }
  for (const c of children) el.append(c instanceof HTMLElement ? c : document.createTextNode(c ?? ""));
  return el;
}

async function apiGet<T>(path: string): Promise<T> {
  const r = await fetch(`${API_BASE}/${path}`, { headers: API_KEY ? { "X-VeilCore-Key": API_KEY } : {} });
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json();
}

/** ========= Splash (fast deterministic) ========= */
function Splash(onDone: () => void){
  const root = h("div", { style:{ position:"fixed", inset:"0", background:"#0a0e17", display:"grid", placeItems:"center" }});
  const box  = h("div", { style:{ textAlign:"center" } },
    h("div",{ style:{ fontSize:"72px", color:C.cyan, marginBottom:"12px" }}, "👁"),
    h("div",{ style:{ fontSize:"44px", color:C.cyan, fontWeight:"1000", letterSpacing:"12px" }}, "V E I L O S"),
    h("div",{ style:{ color:C.text2, marginTop:"10px" }}, "Hospital Cybersecurity Defense Platform"),
    h("div",{ style:{ color:C.dim, marginTop:"16px", fontSize:"12px" }}, "82 organs · 17 subsystems · 5 compliance frameworks"),
  );
  root.append(box);

  setTimeout(()=>{
    root.style.transition = "opacity 600ms ease";
    root.style.opacity = "0";
    setTimeout(onDone, 650);
  }, 1200);

  return root;
}

/** ========= Window Manager ========= */
type WinSpec = {
  id: string;
  title: string;
  size?: "normal"|"small";
  x?: number; y?: number;
  render: () => HTMLElement;
};

class WindowManager {
  private z = 10;
  private desktop: HTMLElement;
  private windows = new Map<string, HTMLElement>();

  constructor(desktop: HTMLElement){
    this.desktop = desktop;
    window.addEventListener("keydown", (e)=>{
      if (e.altKey && e.key === "Tab") {
        e.preventDefault();
        this.altTab();
      }
    });
  }

  open(spec: WinSpec){
    if (this.windows.has(spec.id)) {
      this.focus(spec.id);
      return;
    }

    const win = h("div", { class:`win ${spec.size === "small" ? "small" : ""}` });
    win.style.left = `${spec.x ?? 120}px`;
    win.style.top  = `${spec.y ?? 90}px`;
    win.style.zIndex = String(this.z++);

    const titlebar = h("div", { class:"titlebar" },
      h("div", { class:"wintitle" }, spec.title),
      h("div", { class:"wincontrols" },
        h("button", { class:"ctrl", onclick:()=>this.minimize(spec.id) }, "—"),
        h("button", { class:"ctrl", onclick:()=>this.close(spec.id) }, "✕"),
      )
    );
    const body = h("div", { class:"winbody" }, spec.render());

    win.append(titlebar, body);
    this.desktop.append(win);

    this.makeDraggable(win, titlebar);
    win.addEventListener("mousedown", ()=>this.focus(spec.id));

    this.windows.set(spec.id, win);
    this.focus(spec.id);
  }

  focus(id: string){
    const w = this.windows.get(id);
    if (!w) return;
    w.style.zIndex = String(this.z++);
  }

  close(id: string){
    const w = this.windows.get(id);
    if (!w) return;
    w.remove();
    this.windows.delete(id);
    // tell taskbar to update via event
    document.dispatchEvent(new CustomEvent("wm:changed"));
  }

  minimize(id: string){
    const w = this.windows.get(id);
    if (!w) return;
    // cheap minimize: toggle display
    w.style.display = (w.style.display === "none") ? "block" : "none";
    document.dispatchEvent(new CustomEvent("wm:changed"));
  }

  listOpen(){
    return Array.from(this.windows.keys());
  }

  private altTab(){
    const ids = this.listOpen();
    if (ids.length <= 1) return;
    // rotate: bring next to front
    const first = ids[0];
    ids.push(ids.shift()!);
    this.focus(ids[0]);
    // reorder Map by re-inserting (so next alt-tab cycles)
    const newMap = new Map<string, HTMLElement>();
    for (const id of ids) newMap.set(id, this.windows.get(id)!);
    this.windows = newMap;
  }

  private makeDraggable(win: HTMLElement, handle: HTMLElement){
    let dragging = false;
    let ox = 0, oy = 0;

    handle.addEventListener("mousedown", (e: MouseEvent)=>{
      dragging = true;
      ox = e.clientX - win.offsetLeft;
      oy = e.clientY - win.offsetTop;
      this.focusByEl(win);
    });

    document.addEventListener("mouseup", ()=>dragging=false);
    document.addEventListener("mousemove", (e: MouseEvent)=>{
      if (!dragging) return;
      win.style.left = `${e.clientX - ox}px`;
      win.style.top  = `${e.clientY - oy}px`;
    });
  }

  private focusByEl(win: HTMLElement){
    win.style.zIndex = String(this.z++);
  }
}

/** ========= Apps ========= */
function DashboardApp(){
  const root = h("div");

  const hdr = h("div", { class:"hdr" },
    h("div",{ class:"big" }, "🔱 SECURITY COMMAND CENTER"),
    h("div",{ class:"conn", id:"conn" }, "● CONNECTING..."),
    h("div",{ class:"tlevel", id:"tlevel" }, "● --"),
  );

  const cards = h("div",{ class:"cards" });
  const cAlerts = metric("ACTIVE ALERTS","--", C.red);
  const cOrgans = metric("ORGANS ACTIVE","--", C.green);
  const cUptime = metric("UPTIME","--", C.cyan);
  const cMesh   = metric("MESH ROUTER","--", C.cyan);
  const cWs     = metric("WS CLIENTS","--", C.gold);
  cards.append(cAlerts.node,cOrgans.node,cUptime.node,cMesh.node,cWs.node);

  const mid = h("div",{ class:"grid2" });

  const organsPanel = panel("🧬 SECURITY ORGANS");
  const organsBody = organsPanel.body;

  const alertsPanel = panel("🚨 LIVE ALERT FEED", C.red);
  const alertsBody = alertsPanel.body;

  const right = h("div", {},
    alertsPanel.node,
    compliancePanel()
  );

  mid.append(organsPanel.node, right);

  root.append(hdr, cards, mid);

  async function refresh(){
    // status
    try {
      const st = await apiGet<StatusResponse>("status");
      const conn = hdr.querySelector("#conn") as HTMLElement;
      conn.textContent = "● CONNECTED";
      conn.style.color = C.green;

      const lv = st?.threats?.threat_level ?? "UNKNOWN";
      const lc: Record<string,string> = { NORMAL:C.green, ELEVATED:C.orange, HIGH:C.red, CRITICAL:C.red, UNKNOWN:C.dim };
      const tlevel = hdr.querySelector("#tlevel") as HTMLElement;
      tlevel.textContent = `● ${lv}`;
      tlevel.style.color = lc[lv] ?? C.dim;

      const ac = st?.threats?.active_alerts ?? 0;
      cAlerts.set(String(ac), ac > 0 ? C.red : C.green);

      const a = st?.organs?.active ?? 0;
      const total = st?.organs?.total ?? 82;
      cOrgans.set(`${a}/${total}`, a === total ? C.green : C.orange);

      const u = st?.uptime_seconds ?? 0;
      const hh = Math.floor(u/3600), mm = Math.floor((u%3600)/60);
      cUptime.set(`${hh}h ${mm}m`, C.cyan);

      const mr = !!st?.mesh?.router_active;
      cMesh.set(mr ? "ACTIVE" : "DOWN", mr ? C.green : C.red);

      cWs.set(String(st?.api?.websocket_clients ?? 0), C.gold);

    } catch {
      const conn = hdr.querySelector("#conn") as HTMLElement;
      conn.textContent = "● OFFLINE";
      conn.style.color = C.red;
    }

    // organs
    try {
      const data = await apiGet<{organs: Organ[]}>("organs");
      organsBody.replaceChildren(...renderOrgans(data.organs ?? []));
    } catch {
      organsBody.replaceChildren(h("div",{style:{color:C.dim, padding:"12px"}}, "No organs (API error)."));
    }

    // alerts
    try {
      const data = await apiGet<{alerts: AlertItem[]}>("alerts?limit=50");
      alertsBody.replaceChildren(...renderAlerts(data.alerts ?? []));
    } catch {
      alertsBody.replaceChildren(h("div",{style:{color:C.dim, padding:"12px"}}, "No alerts (API error)."));
    }
  }

  refresh();
  const timer = setInterval(refresh, 3000);

  // cleanup if window closes (optional)
  (root as any)._cleanup = () => clearInterval(timer);

  return root;
}

function TerminalApp(){
  return h("div", { class:"term" },
`VeilOS Terminal v1.0
═══════════════════════════════════════
Type 'help' for available commands.

veilcore@hospital:~$ systemctl status veilcore.target
● veilcore.target - VeilCore Security Platform
     Loaded: loaded
     Active: active

veilcore@hospital:~$ _`);
}

function metric(title: string, value: string, color: string){
  const node = h("div",{ class:"card" },
    h("div",{ class:"t" }, title),
    h("div",{ class:"v", style:{ color } }, value),
  );
  const v = node.querySelector(".v") as HTMLElement;
  return {
    node,
    set: (val: string, c?: string)=>{ v.textContent = val; if (c) v.style.color = c; }
  };
}

function panel(title: string, color: string = C.cyan){
  const node = h("div",{ class:"panel" },
    h("div",{ class:"ph", style:{ color } }, title),
    h("div",{ class:"pb" }),
  );
  return { node, body: node.querySelector(".pb") as HTMLElement };
}

function renderOrgans(organs: Organ[]){
  if (!organs.length) return [h("div",{style:{color:C.dim, padding:"12px"}}, "No organs returned.")];

  const order: Record<string, number> = { P0:0, P1:1, P2:2 };
  organs.sort((a,b)=>
    (order[a.tier ?? "P2"] ?? 9) - (order[b.tier ?? "P2"] ?? 9) ||
    String(a.name ?? "").localeCompare(String(b.name ?? ""))
  );

  const out: HTMLElement[] = [];
  let tier: string|null = null;
  const tl: Record<string,string> = { P0:"🔴 P0 — CRITICAL", P1:"🟠 P1 — IMPORTANT", P2:"🟢 P2 — STANDARD" };
  const tc: Record<string,string> = { P0:C.red, P1:C.orange, P2:C.green };

  for (const o of organs){
    const t = o.tier ?? "P2";
    if (t !== tier){
      tier = t;
      out.push(h("div",{style:{padding:"10px 0 6px", color:tc[t] ?? C.green, fontWeight:"1000"}}, tl[t] ?? t));
    }
    const active = (o.active === true) || (o.status === "running") || (o.active === "active");
    out.push(h("div",{ class:"row" },
      h("div",{style:{color:tc[t] ?? C.green}}, "●"),
      h("div",{style:{fontWeight:"1000"}}, o.name ?? "?"),
      h("div",{style:{color:C.dim}}, o.description ?? o.unit ?? ""),
      h("div",{style:{textAlign:"right", fontWeight:"1000", color: active ? C.green : C.red}}, active ? "● ACTIVE" : "● DEAD"),
    ));
  }
  return out;
}

function renderAlerts(alerts: AlertItem[]){
  if (!alerts.length) return [h("div",{style:{color:C.dim, padding:"12px"}}, "No alerts.")];
  const si: Record<string,string> = { critical:"🔴", high:"🟠", medium:"🟡", low:"🟢", info:"🔵" };

  return alerts.slice(-30).map(a=>{
    const sev = (a.severity ?? "info").toLowerCase();
    const msg = a.message ?? a.description ?? JSON.stringify(a);
    let ts = a.timestamp ?? "";
    if (ts) ts = ts.replace("Z","").slice(11,19);
    return h("div",{style:{padding:"8px 0", borderBottom:`1px solid ${C.border}`, color:C.text2, fontSize:"12px"}},
      `${ts ? "["+ts+"] " : ""}${si[sev] ?? "⚪"} ${msg}`
    );
  });
}

function compliancePanel(){
  const node = h("div",{ style:{ marginTop:"12px" }, class:"panel" });
  const head = h("div",{ class:"ph" }, "📊 COMPLIANCE COVERAGE");
  const body = h("div",{ class:"pb" });

  const rows = [
    ["HIPAA","ShieldLaw Engine","100.0%", C.green],
    ["HITRUST CSF v11","TrustForge Engine","100.0%", C.green],
    ["SOC 2 Type II","AuditIron Engine","98.6%", C.gold],
    ["FedRAMP NIST 800-53","IronFlag Engine","100.0%", C.green],
    ["OWASP ASVS 5.0","345 Controls · 17 Domains","100.0%", C.green],
  ];

  for (const [n,e,s,col] of rows){
    body.append(
      h("div",{style:{display:"grid", gridTemplateColumns:"180px 1fr 90px", gap:"10px", padding:"8px 0", borderBottom:`1px solid ${C.border}`}},
        h("div",{style:{fontWeight:"1000"}}, n),
        h("div",{style:{color:C.dim}}, e),
        h("div",{style:{textAlign:"right", fontWeight:"1000", color:col}}, s),
      )
    );
  }

  node.append(head, body);
  return node;
}

/** ========= Desktop Shell ========= */
function Desktop(){
  const root = h("div",{ class:"desktop" });
  const desktopArea = h("div",{ style:{ position:"absolute", inset:"0 0 44px 0" }});
  const wm = new WindowManager(desktopArea);

  // Start menu
  const startMenu = h("div",{ class:"startmenu" },
    h("div",{ class:"title" }, "🔱 VEILOS APPLICATIONS"),
    h("div",{ class:"sep" }),
    appItem("📊", "Security Dashboard", "Real-time threat monitoring", C.cyan, ()=>wm.open({ id:"dashboard", title:"Security Dashboard", render:DashboardApp })),
    appItem("⌨", "Terminal", "VeilOS command line", C.green, ()=>wm.open({ id:"terminal", title:"Terminal", size:"small", render:TerminalApp, x:160, y:140 })),
    appItem("🚨", "Alert Center", "Threat & incident feed", C.red, ()=>wm.open({ id:"alerts", title:"Alert Center", render:DashboardApp, x:200, y:120 })),
    appItem("📋", "Compliance Hub", "HIPAA · HITRUST · SOC 2 · FedRAMP · ASVS", C.gold, ()=>wm.open({ id:"compliance", title:"Compliance Hub", render:DashboardApp, x:240, y:150 })),
    h("div",{ class:"footer" }, "82 organs · 17 subsystems · 5 frameworks")
  );

  function appItem(icon: string, name: string, desc: string, color: string, onOpen: ()=>void){
    return h("button",{ class:"appitem", onclick:()=>{ onOpen(); startMenu.classList.remove("open"); } },
      h("div",{ class:"approw" },
        h("div",{ class:"appicon", style:{ color } }, icon),
        h("div",{},
          h("div",{ class:"appname" }, name),
          h("div",{ class:"appdesc" }, desc),
        )
      )
    );
  }

  // Taskbar
  const taskbar = h("div",{ class:"taskbar" });
  const startBtn = h("button",{ class:"btn startbtn", onclick:()=>startMenu.classList.toggle("open") }, "🔱 VeilOS");
  const dashBtn  = h("button",{ class:"btn", onclick:()=>wm.open({ id:"dashboard", title:"Security Dashboard", render:DashboardApp }) }, "📊 Dashboard");
  const termBtn  = h("button",{ class:"btn", onclick:()=>wm.open({ id:"terminal", title:"Terminal", size:"small", render:TerminalApp, x:160, y:140 }) }, "⌨ Terminal");

  const tray = h("div",{ class:"tray" },
    h("div",{ class:"status" }, "● NOMINAL"),
    h("div",{ class:"clock", id:"clock" }, "--")
  );

  setInterval(()=>{
    const d = new Date();
    const txt = d.toLocaleString(undefined, { weekday:"short", month:"short", day:"2-digit", hour:"2-digit", minute:"2-digit", second:"2-digit" });
    const c = tray.querySelector("#clock") as HTMLElement;
    if (c) c.textContent = txt;
  }, 1000);

  taskbar.append(startBtn, dashBtn, termBtn, tray);

  // close start menu on click outside
  root.addEventListener("mousedown",(e)=>{
    if (!startMenu.contains(e.target as Node) && e.target !== startBtn) startMenu.classList.remove("open");
  });

  // Boot: open dashboard by default
  wm.open({ id:"dashboard", title:"Security Dashboard", render:DashboardApp });

  root.append(desktopArea, taskbar, startMenu);
  return root;
}

/** ========= Boot ========= */
const mount = document.getElementById("app")!;
mount.replaceChildren(Splash(()=>mount.replaceChildren(Desktop())));
