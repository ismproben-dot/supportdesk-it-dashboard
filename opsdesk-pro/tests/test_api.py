import http.client, json, tempfile, threading, unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server

class Client:
    def __init__(self,port): self.port=port; self.cookie=''; self.csrf=''
    def request(self,path,method='GET',data=None,csrf=True):
        conn=http.client.HTTPConnection('127.0.0.1',self.port)
        headers={'Content-Type':'application/json','Cookie':self.cookie}
        if csrf: headers['X-CSRF-Token']=self.csrf
        conn.request(method,path,json.dumps(data) if data is not None else None,headers)
        r=conn.getresponse(); raw=r.read(); cookie=r.getheader('Set-Cookie')
        if cookie:self.cookie=cookie.split(';')[0]
        result=json.loads(raw) if 'application/json' in r.getheader('Content-Type','') else raw.decode()
        conn.close(); return r.status,result
    def login(self,email):
        status,_=self.request('/api/login','POST',{'email':email,'password':'Test-password-123!'})
        assert status==200
        _,me=self.request('/api/me'); self.csrf=me['csrf']; return me

class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();server.DB=Path(cls.temp.name)/'test.sqlite3';server.initialize()
        for name,role in [('admin','admin'),('agent','agent'),('alice','requester'),('bob','requester')]:server.create_user(name,name+'@example.test','Test-password-123!',role)
        cls.http=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler);cls.thread=threading.Thread(target=cls.http.serve_forever,daemon=True);cls.thread.start();cls.port=cls.http.server_port
    @classmethod
    def tearDownClass(cls):cls.http.shutdown();cls.http.server_close();cls.thread.join();cls.temp.cleanup()
    def setUp(self):
        self.admin=Client(self.port);self.admin.login('admin@example.test');self.alice=Client(self.port);self.alice.login('alice@example.test');self.bob=Client(self.port);self.bob.login('bob@example.test')
    def ticket(self,title='Printer offline'):
        status,r=self.alice.request('/api/tickets','POST',{'title':title,'description':'Cannot print from workstation.','priority':'High'});self.assertEqual(status,201);return r['id']
    def test_unauthenticated_and_wrong_password(self):
        c=Client(self.port);self.assertEqual(c.request('/api/tickets')[0],401);self.assertEqual(c.request('/api/login','POST',{'email':'admin@example.test','password':'incorrect'})[0],401)
    def test_requester_isolation(self):
        tid=self.ticket();self.assertEqual(self.bob.request('/api/tickets/'+str(tid))[0],404)
        _,rows=self.bob.request('/api/tickets');self.assertNotIn(tid,[r['id'] for r in rows]);self.assertEqual(self.bob.request(f'/api/tickets/{tid}/comments','POST',{'body':'unauthorized'})[0],404)
    def test_requester_cannot_manage(self):
        tid=self.ticket();self.assertEqual(self.alice.request('/api/assets')[0],403);self.assertEqual(self.alice.request(f'/api/tickets/{tid}','PATCH',{'status':'Resolved','version':1})[0],403)
    def test_csrf(self):self.assertEqual(self.alice.request('/api/tickets','POST',{'title':'a'},csrf=False)[0],403)
    def test_status_conflict_and_audit(self):
        tid=self.ticket();p=f'/api/tickets/{tid}';d={'status':'Resolved','version':1,'assignee_id':2,'asset_id':None}
        self.assertEqual(self.admin.request(p,'PATCH',d)[0],200);self.assertEqual(self.admin.request(p,'PATCH',d)[0],409)
        _,t=self.admin.request(p);self.assertEqual(t['version'],2);self.assertIsNotNone(t['resolved_at']);self.assertEqual(len(t['history']),2)
        d.update(status='Open',version=2);self.admin.request(p,'PATCH',d);_,t=self.admin.request(p);self.assertIsNone(t['resolved_at'])
    def test_invalid_assignment_rolls_back(self):
        tid=self.ticket();p=f'/api/tickets/{tid}'
        self.assertEqual(self.admin.request(p,'PATCH',{'status':'Resolved','version':1,'asset_id':999999})[0],409)
        _,t=self.admin.request(p);self.assertEqual(t['status'],'Open');self.assertEqual(t['version'],1)
    def test_comments_persist(self):
        tid=self.ticket();self.assertEqual(self.alice.request(f'/api/tickets/{tid}/comments','POST',{'body':'<script>alert(1)</script>'})[0],201)
        _,t=self.admin.request(f'/api/tickets/{tid}');self.assertEqual(t['comments'][0]['body'],'<script>alert(1)</script>')
    def test_validation(self):
        for payload in [{'title':' ','description':'ok','priority':'Low'},{'title':'ok','description':'ok','priority':'Urgent'}]:self.assertEqual(self.alice.request('/api/tickets','POST',payload)[0],400)
        self.assertEqual(self.alice.request('/api/tickets','POST',[])[0],400)
    def test_asset_unique_and_link(self):
        d={'tag':'TEST-01','name':'Laptop','department':'IT','state':'Active'}
        self.assertEqual(self.admin.request('/api/assets','POST',d)[0],201);self.assertEqual(self.admin.request('/api/assets','POST',d)[0],409)
        _,rows=self.admin.request('/api/assets');tid=self.ticket();self.assertEqual(self.admin.request(f'/api/tickets/{tid}','PATCH',{'status':'In Progress','version':1,'asset_id':rows[0]['id']})[0],200)
    def test_search_and_csv(self):
        tid=self.ticket('=DangerousFormula');_,rows=self.alice.request('/api/tickets?q=DangerousFormula&status=Open');self.assertIn(tid,[r['id'] for r in rows])
        _,csv=self.alice.request('/api/report.csv?q=DangerousFormula');self.assertIn("'=DangerousFormula",csv)
        _,csv=self.bob.request('/api/report.csv');self.assertNotIn('DangerousFormula',csv)
    def test_analytics_scope_and_overdue(self):
        tid=self.ticket()
        with server.connect() as db:db.execute("UPDATE tickets SET due_at='2000-01-01T00:00:00+00:00' WHERE id=?",(tid,))
        _,a=self.alice.request('/api/analytics');_,b=self.bob.request('/api/analytics');self.assertGreaterEqual(a['overdue'],1);self.assertEqual(b['total'],0);self.assertEqual(len(a['trend']),7)
    def test_logout_and_expiry(self):
        self.alice.request('/api/logout','POST',{});self.assertEqual(self.alice.request('/api/me')[0],401)
        with server.connect() as db:db.execute('UPDATE sessions SET expires=0 WHERE csrf=?',(self.bob.csrf,))
        self.assertEqual(self.bob.request('/api/me')[0],401)
    def test_password_not_plaintext_and_static_allowlist(self):
        with server.connect() as db:value=db.execute('SELECT password FROM users LIMIT 1').fetchone()[0]
        self.assertNotIn('Test-password',value);self.assertTrue(server.verify('Test-password-123!',value));self.assertEqual(self.admin.request('/../server.py')[0],404)
        self.assertEqual(self.admin.request('/')[0],200)
if __name__=='__main__':unittest.main(verbosity=2)
