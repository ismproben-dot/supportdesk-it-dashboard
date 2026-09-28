"""OpsDesk Pro: dependency-free local portfolio API. Python 3.11+."""
import argparse, csv, hashlib, hmac, io, json, os, secrets, sqlite3, time
from datetime import datetime, timedelta, timezone
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

ROOT = Path(__file__).resolve().parent
DB = Path(os.environ.get('OPSDESK_DB', ROOT / 'data' / 'opsdesk.sqlite3'))
PRIORITIES = {'Critical': 4, 'High': 24, 'Medium': 72, 'Low': 168}
STATUSES = ('Open', 'In Progress', 'Resolved')

def now(): return datetime.now(timezone.utc).isoformat(timespec='seconds')
def connect():
    db = sqlite3.connect(DB, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    return db

def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 260000).hex()
    return salt + ':' + digest

def verify(password, encoded): return hmac.compare_digest(password_hash(password, encoded.split(':')[0]), encoded)

def initialize():
    DB.parent.mkdir(parents=True, exist_ok=True)
    with connect() as db: db.executescript((ROOT / 'schema.sql').read_text())

def create_user(name, email, password, role):
    if role not in ('admin','agent','requester') or len(password) < 12: raise ValueError('Use a valid role and a password of at least 12 characters.')
    with connect() as db: db.execute('INSERT INTO users(name,email,password,role) VALUES(?,?,?,?)', (name, email.lower(), password_hash(password), role))

class APIError(Exception):
    def __init__(self, status, message): self.status, self.message = status, message

def text(data, key, maximum=200):
    value = data.get(key)
    if not isinstance(value, str) or not value.strip() or len(value) > maximum: raise APIError(400, f'{key}: enter 1–{maximum} characters.')
    return value.strip()

def option(data, key, choices):
    value = data.get(key)
    if not isinstance(value, str) or value not in choices: raise APIError(400, f'Invalid {key}.')
    return value

def optional_id(data, key):
    value = data.get(key)
    if value in (None, ''): return None
    if type(value) is not int or value < 1: raise APIError(400, f'Invalid {key}.')
    return value

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_): pass  # no credentials or request bodies in logs
    def send(self, status, data, content_type='application/json', cookie=None):
        raw = json.dumps(data).encode() if content_type == 'application/json' else data.encode() if isinstance(data,str) else data
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'")
        if cookie: self.send_header('Set-Cookie',cookie)
        self.end_headers(); self.wfile.write(raw)
    def body(self):
        if self.headers.get('Content-Type','').split(';')[0] != 'application/json': raise APIError(415,'JSON required.')
        try: length = int(self.headers.get('Content-Length','0'))
        except ValueError: raise APIError(400,'Invalid content length.')
        if not 0 < length <= 32768: raise APIError(413,'Request too large or empty.')
        try: data = json.loads(self.rfile.read(length))
        except (ValueError, UnicodeError): raise APIError(400,'Invalid JSON.')
        if not isinstance(data,dict): raise APIError(400,'JSON object required.')
        return data
    def auth(self, db):
        cookie = SimpleCookie()
        try: cookie.load(self.headers.get('Cookie',''))
        except Exception: raise APIError(401,'Please sign in.')
        token = cookie.get('session')
        row = db.execute('SELECT u.id,u.name,u.email,u.role,s.csrf FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=? AND s.expires>?', (token.value if token else '',time.time())).fetchone()
        if not row: raise APIError(401,'Please sign in.')
        if self.command != 'GET' and not hmac.compare_digest(self.headers.get('X-CSRF-Token',''),row['csrf']): raise APIError(403,'Invalid request token.')
        return dict(row)
    def staff(self,user):
        if user['role'] not in ('admin','agent'): raise APIError(403,'Agent access required.')
    def ticket(self,db,user,tid):
        row=db.execute('SELECT * FROM tickets WHERE id=?',(tid,)).fetchone()
        if not row or (user['role']=='requester' and row['requester_id']!=user['id']): raise APIError(404,'Ticket not found.')
        return dict(row)
    def do_GET(self): self.handle_request()
    def do_POST(self): self.handle_request()
    def do_PATCH(self): self.handle_request()
    def handle_request(self):
        try:
            with connect() as db: self.route(db)
        except APIError as e: self.send(e.status,{'error':e.message})
        except sqlite3.IntegrityError: self.send(409,{'error':'Duplicate value or invalid related record.'})
        except Exception:
            self.send(500,{'error':'An internal error occurred.'})
    def route(self, db):
        path=urlsplit(self.path).path; method=self.command
        if not path.startswith('/api/'):
            files={'/':('index.html','text/html; charset=utf-8'),'/app.js':('app.js','text/javascript'),'/style.css':('style.css','text/css')}
            if method!='GET' or path not in files: raise APIError(404,'Not found.')
            name,mime=files[path]; return self.send(200,(ROOT/'static'/name).read_bytes(),mime)
        if path=='/api/login' and method=='POST':
            data=self.body(); email=text(data,'email').lower(); password=text(data,'password',256)
            user=db.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone()
            encoded=user['password'] if user else password_hash('dummy-password')
            if not verify(password,encoded) or not user: raise APIError(401,'Invalid email or password.')
            token=secrets.token_urlsafe(32); csrf=secrets.token_urlsafe(32)
            db.execute('DELETE FROM sessions WHERE expires<?',(time.time(),))
            db.execute('INSERT INTO sessions VALUES(?,?,?,?)',(token,user['id'],csrf,time.time()+28800))
            return self.send(200,{'ok':True},cookie=f'session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800')
        user=self.auth(db)
        if path=='/api/me' and method=='GET': return self.send(200,user)
        if path=='/api/logout' and method=='POST':
            db.execute('DELETE FROM sessions WHERE csrf=?',(user['csrf'],)); return self.send(200,{'ok':True},cookie='session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0')
        if path=='/api/users' and method=='GET':
            self.staff(user); return self.send(200,[dict(r) for r in db.execute("SELECT id,name,role FROM users WHERE role IN ('admin','agent')")])
        if path=='/api/assets':
            if method=='GET':
                self.staff(user); return self.send(200,[dict(r) for r in db.execute('SELECT * FROM assets ORDER BY id DESC')])
            if method=='POST':
                self.staff(user); d=self.body(); db.execute('INSERT INTO assets(tag,name,department,state) VALUES(?,?,?,?)',(text(d,'tag',40),text(d,'name'),text(d,'department',100),option(d,'state',('Active','Maintenance','Retired')))); return self.send(201,{'ok':True})
        scope=' WHERE t.requester_id=?' if user['role']=='requester' else ''
        params=[user['id']] if scope else []
        if path in ('/api/tickets','/api/report.csv') and method=='GET':
            q=parse_qs(urlsplit(self.path).query); clauses=[]
            if q.get('status',[''])[0]: clauses.append('t.status=?'); params.append(q['status'][0])
            if q.get('q',[''])[0]: clauses.append('(t.title LIKE ? OR CAST(t.id AS TEXT)=?)'); params.extend(['%'+q['q'][0]+'%',q['q'][0]])
            where=scope
            if clauses: where+=(' AND ' if where else ' WHERE ')+' AND '.join(clauses)
            rows=[dict(r) for r in db.execute('SELECT t.*,u.name requester,a.name assignee FROM tickets t JOIN users u ON u.id=t.requester_id LEFT JOIN users a ON a.id=t.assignee_id'+where+' ORDER BY t.id DESC',params)]
            if path.endswith('.csv'):
                out=io.StringIO(); writer=csv.writer(out); writer.writerow(['ID','Title','Priority','Status','Requester','Assignee','Due UTC'])
                def safe(v):
                    v=str(v or '')
                    return "'"+v if v[:1] in ('=','+','-','@','\t','\r','\n') else v
                writer.writerows([[safe(r[k]) for k in ('id','title','priority','status','requester','assignee','due_at')] for r in rows]); return self.send(200,out.getvalue(),'text/csv; charset=utf-8')
            return self.send(200,rows)
        if path=='/api/tickets' and method=='POST':
            d=self.body(); title=text(d,'title'); description=text(d,'description',5000); priority=option(d,'priority',PRIORITIES); stamp=now()
            due=(datetime.now(timezone.utc)+timedelta(hours=PRIORITIES[priority])).isoformat(timespec='seconds')
            cur=db.execute('INSERT INTO tickets(title,description,priority,requester_id,created_at,updated_at,due_at) VALUES(?,?,?,?,?,?,?)',(title,description,priority,user['id'],stamp,stamp,due)); tid=cur.lastrowid
            db.execute('INSERT INTO audit(ticket_id,user_id,action,created_at) VALUES(?,?,?,?)',(tid,user['id'],'Created ticket',stamp)); return self.send(201,{'id':tid})
        if path=='/api/analytics' and method=='GET':
            rows=[dict(r) for r in db.execute('SELECT t.* FROM tickets t'+scope,params)]
            opened=[r for r in rows if r['status']!='Resolved']; resolved=[r for r in rows if r['status']=='Resolved']
            hours=[(datetime.fromisoformat(r['resolved_at'])-datetime.fromisoformat(r['created_at'])).total_seconds()/3600 for r in resolved if r['resolved_at']]
            trend=[{'day':(datetime.now(timezone.utc)-timedelta(days=n)).date().isoformat()} for n in reversed(range(7))]
            for day in trend: day['count']=sum(r['created_at'][:10]==day['day'] for r in rows)
            return self.send(200,{'total':len(rows),'open':len(opened),'resolved':len(resolved),'overdue':sum(r['due_at']<now() for r in opened),'resolution_hours':round(sum(hours)/len(hours),1) if hours else None,'priorities':{p:sum(r['priority']==p for r in opened) for p in PRIORITIES},'trend':trend})
        parts=path.strip('/').split('/')
        if len(parts)>=3 and parts[:2]==['api','tickets'] and parts[2].isdigit():
            tid=int(parts[2]); ticket=self.ticket(db,user,tid)
            if len(parts)==3 and method=='GET':
                ticket['comments']=[dict(r) for r in db.execute('SELECT c.*,u.name author FROM comments c JOIN users u ON u.id=c.user_id WHERE ticket_id=? ORDER BY c.id',(tid,))]
                ticket['history']=[dict(r) for r in db.execute('SELECT a.*,u.name author FROM audit a JOIN users u ON u.id=a.user_id WHERE ticket_id=? ORDER BY a.id DESC',(tid,))]
                return self.send(200,ticket)
            if len(parts)==4 and parts[3]=='comments' and method=='POST':
                d=self.body(); db.execute('INSERT INTO comments(ticket_id,user_id,body,created_at) VALUES(?,?,?,?)',(tid,user['id'],text(d,'body',3000),now())); return self.send(201,{'ok':True})
            if len(parts)==3 and method=='PATCH':
                self.staff(user); d=self.body(); status=option(d,'status',STATUSES); assignee=optional_id(d,'assignee_id'); asset=optional_id(d,'asset_id')
                if type(d.get('version')) is not int: raise APIError(400,'Version required.')
                if assignee and not db.execute("SELECT id FROM users WHERE id=? AND role IN ('admin','agent')",(assignee,)).fetchone(): raise APIError(400,'Invalid agent.')
                stamp=now(); resolved=(ticket['resolved_at'] or stamp) if status=='Resolved' else None
                cur=db.execute('UPDATE tickets SET status=?,assignee_id=?,asset_id=?,updated_at=?,resolved_at=?,version=version+1 WHERE id=? AND version=?',(status,assignee,asset,stamp,resolved,tid,d['version']))
                if cur.rowcount!=1: raise APIError(409,'Ticket changed. Reload before saving.')
                action=f"Status: {ticket['status']} → {status}; agent: {assignee or 'unassigned'}; asset: {asset or 'none'}"
                db.execute('INSERT INTO audit(ticket_id,user_id,action,created_at) VALUES(?,?,?,?)',(tid,user['id'],action,stamp)); return self.send(200,{'ok':True})
        raise APIError(404,'Endpoint not found.')

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--port',type=int,default=8000); parser.add_argument('--create-user',action='store_true'); args=parser.parse_args(); initialize()
    if args.create_user:
        import getpass
        create_user(input('Name: '),input('Email: '),getpass.getpass('Password (12+ characters): '),input('Role (admin/agent/requester): ')); print('User created.'); return
    print(f'OpsDesk Pro running at http://127.0.0.1:{args.port}')
    ThreadingHTTPServer(('127.0.0.1',args.port),Handler).serve_forever()
if __name__=='__main__': main()
