import json, sqlite3, os, time, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BASE=Path(__file__).resolve().parent
DB=BASE/'relief.db'


def db():
    c=sqlite3.connect(DB)
    c.row_factory=sqlite3.Row
    return c

def init():
    c=db(); cur=c.cursor()
    cur.executescript('''
    CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, role TEXT);
    CREATE TABLE IF NOT EXISTS incidents(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, hazard TEXT, location TEXT, severity INTEGER, people INTEGER, status TEXT, created_at TEXT);
    CREATE TABLE IF NOT EXISTS resources(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, quantity INTEGER, unit TEXT, location TEXT);
    CREATE TABLE IF NOT EXISTS allocations(id INTEGER PRIMARY KEY AUTOINCREMENT, incident_id INTEGER, resource_id INTEGER, quantity INTEGER, status TEXT, created_at TEXT);
    CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT, action TEXT, actor TEXT, detail TEXT, created_at TEXT);
    ''')
    cur.execute("INSERT OR IGNORE INTO users(username,password,role) VALUES('admin','admin123','Admin')")
    if cur.execute('SELECT COUNT(*) FROM incidents').fetchone()[0]==0:
        now=time.strftime('%Y-%m-%d %H:%M:%S')
        cur.executemany('INSERT INTO incidents(title,hazard,location,severity,people,status,created_at) VALUES(?,?,?,?,?,?,?)',[
          ('Flash Flood','Flood','Vijayawada',5,420,'Open',now),('Earthquake Tremor','Earthquake','Sikkim',3,85,'Open',now),('Heavy Rainfall','Rainfall','Tirupati',4,210,'Assessed',now)])
    if cur.execute('SELECT COUNT(*) FROM resources').fetchone()[0]==0:
        cur.executemany('INSERT INTO resources(name,quantity,unit,location) VALUES(?,?,?,?)',[
          ('Drinking Water',1200,'litres','Central Depot'),('Food Kits',650,'kits','Central Depot'),('First Aid Kits',180,'kits','Medical Store'),('Blankets',500,'units','Central Depot')])
    c.commit(); c.close()

init()

def q(sql,args=()):
    c=db(); rows=c.execute(sql,args).fetchall(); c.close(); return [dict(r) for r in rows]
def one(sql,args=()):
    c=db(); r=c.execute(sql,args).fetchone(); c.close(); return dict(r) if r else None

def write_audit(action,actor,detail):
    c=db(); c.execute('INSERT INTO audit(action,actor,detail,created_at) VALUES(?,?,?,?)',(action,actor,detail,time.strftime('%Y-%m-%d %H:%M:%S'))); c.commit(); c.close()

HTML='''<!doctype html><html><head><meta charset="utf-8"><title>Disaster Relief Management System</title><style>
*{box-sizing:border-box}body{margin:0;font-family:Inter,Arial,sans-serif;background:#f5f7fb;color:#182230}.top{height:70px;background:#173b57;color:#fff;display:flex;align-items:center;justify-content:space-between;padding:0 34px}.brand{font-size:21px;font-weight:800}.pill{background:#2f6f8f;padding:8px 14px;border-radius:20px;font-size:12px}.wrap{display:flex;min-height:calc(100vh - 70px)}.side{width:225px;background:#102d42;color:#dce8ef;padding:24px 14px}.side button{display:block;width:100%;padding:12px 14px;margin:5px 0;border:0;background:transparent;color:#dce8ef;text-align:left;border-radius:9px;cursor:pointer}.side button.active,.side button:hover{background:#1d4f6d;color:#fff}.main{flex:1;padding:30px;max-width:1250px}.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:18px}.card{background:#fff;border:1px solid #e4e9ef;border-radius:14px;padding:20px;box-shadow:0 4px 14px #173b570b}.kpi{font-size:30px;font-weight:800;margin-top:8px}.muted{color:#718096;font-size:13px}.row{display:flex;gap:12px;align-items:center;justify-content:space-between}.table{width:100%;border-collapse:collapse;margin-top:10px}.table th,.table td{padding:12px;border-bottom:1px solid #edf0f4;text-align:left;font-size:13px}.badge{padding:5px 9px;border-radius:999px;font-size:11px;font-weight:700;background:#e7f3ed;color:#1f7a52}.badge.warn{background:#fff3d9;color:#9b6a00}.badge.high{background:#ffe5e5;color:#b22b2b}.btn{border:0;border-radius:8px;padding:9px 13px;background:#1c7896;color:#fff;cursor:pointer}.btn.secondary{background:#e8eef3;color:#173b57}.btn.danger{background:#bd3d3d}.form{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}.input,select{width:100%;padding:10px;border:1px solid #d7dee6;border-radius:8px;background:#fff}.full{grid-column:1/-1}.hide{display:none}.login{max-width:420px;margin:100px auto}.hero{margin-bottom:22px}.hero h1{margin:0 0 6px}.actions{display:flex;gap:8px}.section{margin-top:22px}.toast{position:fixed;right:25px;bottom:25px;background:#173b57;color:#fff;padding:13px 17px;border-radius:9px;display:none}.small{font-size:12px}.progress{height:8px;background:#e8edf2;border-radius:8px;overflow:hidden}.progress span{display:block;height:100%;background:#1c7896}.two{display:grid;grid-template-columns:1.5fr 1fr;gap:18px}
</style></head><body><div id="app"></div><div id="toast" class="toast"></div><script>
let page='dashboard'; let incidents=[]; let resources=[];
const app=document.getElementById('app');
function toast(x){let t=document.getElementById('toast');t.textContent=x;t.style.display='block';setTimeout(()=>t.style.display='none',1800)}
async function api(path,opt={}){let r=await fetch(path,{headers:{'Content-Type':'application/json'},...opt});let d=await r.json();if(!r.ok)throw Error(d.error||'Request failed');return d}
function login(){app.innerHTML=`<div class="login card"><div style="font-size:34px">🛟</div><h1>Disaster Relief</h1><p class="muted">AI-Based Disaster Relief Management System</p><div class="section"><label>Username</label><input id="u" class="input" value="admin"><br><br><label>Password</label><input id="p" class="input" type="password" value="admin123"><br><br><button class="btn" style="width:100%" onclick="doLogin()">Sign in</button><p class="small muted">Demo credentials: admin / admin123</p></div></div>`}
async function doLogin(){try{await api('/api/login',{method:'POST',body:JSON.stringify({username:u.value,password:p.value})});localStorage.setItem('logged','1');render();}catch(e){toast(e.message)}}
function shell(content){app.innerHTML=`<div class="top"><div class="brand">🛟 Disaster Relief Management System</div><div class="pill">ADMIN · LIVE DEMO</div></div><div class="wrap"><aside class="side"><button class="${page==='dashboard'?'active':''}" onclick="go('dashboard')">▦ Dashboard</button><button class="${page==='incidents'?'active':''}" onclick="go('incidents')">⚠ Incidents</button><button class="${page==='resources'?'active':''}" onclick="go('resources')">▣ Resources</button><button class="${page==='allocation'?'active':''}" onclick="go('allocation')">⇄ Allocation</button><button class="${page==='audit'?'active':''}" onclick="go('audit')">◷ Audit Log</button><button onclick="localStorage.removeItem('logged');login()">↪ Logout</button></aside><main class="main">${content}</main></div>`}
async function go(p){page=p;render()}
async function render(){if(!localStorage.getItem('logged'))return login(); if(page==='dashboard')return dashboard(); if(page==='incidents')return incidentsPage(); if(page==='resources')return resourcesPage(); if(page==='allocation')return allocationPage(); if(page==='audit')return auditPage()}
async function dashboard(){let d=await api('/api/dashboard');shell(`<div class="hero"><h1>Operations Dashboard</h1><p class="muted">Current incidents, relief inventory and delivery readiness.</p></div><div class="grid"><div class="card"><div class="muted">Open incidents</div><div class="kpi">${d.open_incidents}</div></div><div class="card"><div class="muted">People affected</div><div class="kpi">${d.people}</div></div><div class="card"><div class="muted">Resources available</div><div class="kpi">${d.resources}</div></div><div class="card"><div class="muted">Allocations</div><div class="kpi">${d.allocations}</div></div></div><div class="section two"><div class="card"><div class="row"><h3>Priority incidents</h3><button class="btn secondary" onclick="go('incidents')">View all</button></div><table class="table"><tr><th>Incident</th><th>Location</th><th>Severity</th><th>Status</th></tr>${d.incidents.map(x=>`<tr><td>${x.title}</td><td>${x.location}</td><td><span class="badge ${x.severity>=4?'high':x.severity===3?'warn':''}">${x.severity}/5</span></td><td>${x.status}</td></tr>`).join('')}</table></div><div class="card"><h3>Relief readiness</h3><p class="muted">Inventory coverage</p>${d.resource_breakdown.map(x=>`<div style="margin:15px 0"><div class="row"><span>${x.name}</span><b>${x.quantity}</b></div><div class="progress"><span style="width:${Math.min(100,x.quantity/12)}%"></span></div></div>`).join('')}</div></div>`)}
async function incidentsPage(){incidents=await api('/api/incidents');shell(`<div class="hero row"><div><h1>Incident Management</h1><p class="muted">Register, classify and update disaster reports.</p></div><button class="btn" onclick="showIncidentForm()">+ Add Incident</button></div><div id="iform"></div><div class="card"><table class="table"><tr><th>Title</th><th>Hazard</th><th>Location</th><th>People</th><th>Severity</th><th>Status</th><th>Action</th></tr>${incidents.map(x=>`<tr><td>${x.title}</td><td>${x.hazard}</td><td>${x.location}</td><td>${x.people}</td><td><span class="badge ${x.severity>=4?'high':x.severity===3?'warn':''}">${x.severity}/5</span></td><td>${x.status}</td><td><button class="btn secondary" onclick="updateStatus(${x.id},'Assessed')">Assess</button></td></tr>`).join('')}</table></div>`)}
function showIncidentForm(){document.getElementById('iform').innerHTML=`<div class="card section"><h3>New incident</h3><div class="form"><input id="it" class="input" placeholder="Incident title"><select id="ih" class="input"><option>Flood</option><option>Earthquake</option><option>Rainfall</option><option>Fire</option></select><input id="il" class="input" placeholder="Location"><input id="ip" class="input" type="number" placeholder="People affected"><input id="is" class="input" type="number" min="1" max="5" value="3" placeholder="Severity"><div class="full actions"><button class="btn" onclick="addIncident()">Save incident</button><button class="btn secondary" onclick="incidentsPage()">Cancel</button></div></div></div>`}
async function addIncident(){await api('/api/incidents',{method:'POST',body:JSON.stringify({title:it.value,hazard:ih.value,location:il.value,people:+ip.value,severity:+is.value})});toast('Incident added');incidentsPage()}
async function updateStatus(id,status){await api('/api/incidents/'+id,{method:'PUT',body:JSON.stringify({status})});toast('Incident assessed');incidentsPage()}
async function resourcesPage(){resources=await api('/api/resources');shell(`<div class="hero"><h1>Relief Inventory</h1><p class="muted">Available resources by item and location.</p></div><div class="card"><table class="table"><tr><th>Resource</th><th>Quantity</th><th>Unit</th><th>Location</th><th>Availability</th></tr>${resources.map(x=>`<tr><td>${x.name}</td><td><b>${x.quantity}</b></td><td>${x.unit}</td><td>${x.location}</td><td><span class="badge">Available</span></td></tr>`).join('')}</table></div>`)}
async function allocationPage(){let d=await api('/api/allocation');shell(`<div class="hero"><h1>Allocation & Dispatch</h1><p class="muted">Prioritize a request, reserve stock and create an auditable dispatch.</p></div><div class="card"><h3>Create allocation</h3><div class="form"><select id="ai" class="input">${d.incidents.map(x=>`<option value="${x.id}">${x.title} — ${x.location}</option>`).join('')}</select><select id="ar" class="input">${d.resources.map(x=>`<option value="${x.id}">${x.name} (${x.quantity} ${x.unit})</option>`).join('')}</select><input id="aq" class="input" type="number" min="1" value="20" placeholder="Quantity"><div class="full"><button class="btn" onclick="allocate()">Approve & Dispatch</button></div></div></div><div class="card section"><h3>Recent dispatches</h3><table class="table"><tr><th>Incident</th><th>Resource</th><th>Quantity</th><th>Status</th><th>Time</th></tr>${d.allocations.map(x=>`<tr><td>${x.incident}</td><td>${x.resource}</td><td>${x.quantity}</td><td><span class="badge">${x.status}</span></td><td>${x.created_at}</td></tr>`).join('')}</table></div>`)}
async function allocate(){await api('/api/allocation',{method:'POST',body:JSON.stringify({incident_id:+ai.value,resource_id:+ar.value,quantity:+aq.value})});toast('Dispatch recorded and stock updated');allocationPage()}
async function auditPage(){let d=await api('/api/audit');shell(`<div class="hero"><h1>Audit Trail</h1><p class="muted">Traceable approvals, changes and dispatch actions.</p></div><div class="card"><table class="table"><tr><th>Time</th><th>Action</th><th>Actor</th><th>Detail</th></tr>${d.map(x=>`<tr><td>${x.created_at}</td><td>${x.action}</td><td>${x.actor}</td><td>${x.detail}</td></tr>`).join('')}</table></div>`)}
if(localStorage.getItem('logged'))render();else login();
</script></body></html>'''

class Handler(BaseHTTPRequestHandler):
    def send_json(self,data,status=200):
        b=json.dumps(data).encode(); self.send_response(status); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(b))); self.end_headers(); self.wfile.write(b)
    def body(self):
        n=int(self.headers.get('Content-Length','0')); return json.loads(self.rfile.read(n) or '{}')
    def do_GET(self):
        path=urllib.parse.urlparse(self.path).path
        if path=='/':
            b=HTML.encode(); self.send_response(200); self.send_header('Content-Type','text/html'); self.send_header('Content-Length',str(len(b))); self.end_headers(); self.wfile.write(b); return
        if path=='/api/dashboard':
            inc=q('SELECT * FROM incidents ORDER BY severity DESC, id DESC'); res=q('SELECT * FROM resources'); alloc=one('SELECT COUNT(*) c FROM allocations')['c']; self.send_json({'open_incidents':sum(x['status']!='Closed' for x in inc),'people':sum(x['people'] for x in inc),'resources':sum(x['quantity'] for x in res),'allocations':alloc,'incidents':inc[:5],'resource_breakdown':res}); return
        if path=='/api/incidents': self.send_json(q('SELECT * FROM incidents ORDER BY id DESC')); return
        if path=='/api/resources': self.send_json(q('SELECT * FROM resources ORDER BY id')); return
        if path=='/api/allocation':
            inc=q('SELECT id,title,location FROM incidents'); res=q('SELECT id,name,quantity,unit FROM resources'); a=q('SELECT a.*,i.title incident,r.name resource FROM allocations a JOIN incidents i ON i.id=a.incident_id JOIN resources r ON r.id=a.resource_id ORDER BY a.id DESC'); self.send_json({'incidents':inc,'resources':res,'allocations':a}); return
        if path=='/api/audit': self.send_json(q('SELECT * FROM audit ORDER BY id DESC LIMIT 30')); return
        self.send_json({'error':'Not found'},404)
    def do_POST(self):
        path=urllib.parse.urlparse(self.path).path; d=self.body()
        if path=='/api/login':
            ok=one('SELECT * FROM users WHERE username=? AND password=?',(d.get('username'),d.get('password')))
            if ok: write_audit('LOGIN',ok['username'],'Successful login'); self.send_json({'ok':True,'role':ok['role']});
            else: self.send_json({'error':'Invalid credentials'},401)
            return
        if path=='/api/incidents':
            c=db(); cur=c.execute('INSERT INTO incidents(title,hazard,location,severity,people,status,created_at) VALUES(?,?,?,?,?,?,?)',(d['title'],d['hazard'],d['location'],int(d['severity']),int(d['people']),'Open',time.strftime('%Y-%m-%d %H:%M:%S'))); c.commit(); new=cur.lastrowid; c.close(); write_audit('CREATE_INCIDENT','admin',f'Incident #{new} created'); self.send_json({'id':new}); return
        if path=='/api/allocation':
            qty=int(d['quantity']); rid=int(d['resource_id']); iid=int(d['incident_id']); r=one('SELECT * FROM resources WHERE id=?',(rid,))
            if not r or r['quantity']<qty: self.send_json({'error':'Insufficient stock'},400); return
            c=db(); c.execute('UPDATE resources SET quantity=quantity-? WHERE id=?',(qty,rid)); c.execute('INSERT INTO allocations(incident_id,resource_id,quantity,status,created_at) VALUES(?,?,?,?,?)',(iid,rid,qty,'Dispatched',time.strftime('%Y-%m-%d %H:%M:%S'))); c.commit(); c.close(); write_audit('DISPATCH','admin',f'{qty} {r["unit"]} of {r["name"]} dispatched for incident #{iid}'); self.send_json({'ok':True}); return
        self.send_json({'error':'Not found'},404)
    def do_PUT(self):
        path=urllib.parse.urlparse(self.path).path; d=self.body()
        if path.startswith('/api/incidents/'):
            iid=int(path.rsplit('/',1)[1]); c=db(); c.execute('UPDATE incidents SET status=? WHERE id=?',(d.get('status','Assessed'),iid)); c.commit(); c.close(); write_audit('UPDATE_INCIDENT','admin',f'Incident #{iid} status updated'); self.send_json({'ok':True}); return
        self.send_json({'error':'Not found'},404)
    def log_message(self,*args): pass

if __name__=='__main__':
    print('Disaster Relief demo running at http://127.0.0.1:8000')
    ThreadingHTTPServer(('0.0.0.0',8000),Handler).serve_forever()
