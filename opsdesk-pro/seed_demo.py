"""Populate a fresh local database with fictional records and random credentials."""
import secrets
from datetime import datetime, timedelta, timezone
import server

server.initialize()
with server.connect() as db:
    if db.execute('SELECT COUNT(*) FROM users').fetchone()[0]:
        raise SystemExit('Database already has users. Use a new OPSDESK_DB path for a separate demo.')
accounts=[('Workspace Admin','admin@example.test','admin'),('Support Agent','agent@example.test','agent'),('Demo Requester','requester@example.test','requester')]
credentials=[]
for name,email,role in accounts:
    password=secrets.token_urlsafe(18);server.create_user(name,email,password,role);credentials.append((email,password))
with server.connect() as db:
    for tag,name,department,state in [('PC-001','Dell OptiPlex','Finance','Active'),('PC-002','Lenovo ThinkPad','People Operations','Active'),('PR-001','HP LaserJet','Reception','Maintenance'),('NET-001','Office switch','IT','Active'),('PC-003','HP ProBook','Registry','Active'),('PC-004','Retired workstation','Storage','Retired')]:
        db.execute('INSERT INTO assets(tag,name,department,state) VALUES(?,?,?,?)',(tag,name,department,state))
    titles=['Printer queue stopped','Shared folder access','Workstation update failure','VPN connection drops','New employee setup','Monitor flickering','Email synchronization','Network outlet offline','Application crash','Restore document backup','Slow startup','Replace keyboard']
    for i,title in enumerate(titles):
        created=datetime.now(timezone.utc)-timedelta(hours=i*13+2);priority=list(server.PRIORITIES)[i%4];status=['Open','In Progress','Resolved'][i%3];resolved=created+timedelta(hours=1) if status=='Resolved' else None
        stamp=created.isoformat(timespec='seconds');due=(created+timedelta(hours=server.PRIORITIES[priority])).isoformat(timespec='seconds')
        cur=db.execute('INSERT INTO tickets(title,description,priority,status,requester_id,assignee_id,asset_id,created_at,updated_at,due_at,resolved_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)',(title,'Fictional training request. Record diagnostic steps, communicate with the requester, and document the resolution.',priority,status,3,2,i%6+1,stamp,stamp,due,resolved.isoformat(timespec='seconds') if resolved else None))
        db.execute('INSERT INTO audit(ticket_id,user_id,action,created_at) VALUES(?,?,?,?)',(cur.lastrowid,1,'Imported fictional demonstration record',stamp))
print('Fictional workspace ready. These random passwords are shown once; keep them locally.')
for email,password in credentials:print(f'{email}  {password}')
print('Start: python server.py  →  http://127.0.0.1:8000')
