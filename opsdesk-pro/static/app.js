'use strict';
const $ = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let user, assets=[], agents=[], selected, activeView='overview', messageTimer, searchTimer, listVersion=0;
function notify(message){ const dialog=document.querySelector('dialog[open]'); if(dialog){let status=dialog.querySelector('.dialog-status');if(!status){status=document.createElement('p');status.className='dialog-status';status.setAttribute('role','status');dialog.prepend(status);}status.textContent=message;} $('message').textContent=message; $('message').hidden=false; clearTimeout(messageTimer); messageTimer=setTimeout(()=>$('message').hidden=true,6000); }
async function api(path,method='GET',data){
 const response=await fetch('/api/'+path,{method,headers:{'Content-Type':'application/json','X-CSRF-Token':user?.csrf||''},body:data?JSON.stringify(data):undefined});
 const result=await response.json();
 if(!response.ok){if(response.status===401){document.querySelectorAll('dialog[open]').forEach(d=>d.close());$('workspace').hidden=true;$('login').hidden=false;}throw Error(result.error||'Request failed.');}
 return result;
}
function safe(fn){return async event=>{try{await fn(event);}catch(error){notify(error.message);}};}
function date(value){return new Date(value).toLocaleString([], {month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'});}
function badge(value){return `<span class="tag ${esc(value.split(' ')[0])}">${esc(value)}</span>`;}
function show(view){activeView=view;document.querySelectorAll('.view').forEach(el=>el.hidden=el.id!==view);document.querySelectorAll('nav button').forEach(el=>el.classList.toggle('active',el.dataset.view===view));$('pageTitle').textContent=({overview:'Overview',tickets:'Service desk',assets:'Equipment',knowledge:'Playbooks'})[view];}
function ticketRows(rows){return rows.map(t=>`<tr><td><button class="link" data-ticket="${t.id}"><small>#${t.id} · ${esc(t.requester)}</small><strong>${esc(t.title)}</strong></button></td><td>${badge(t.priority)}</td><td>${badge(t.status)}</td><td>${esc(t.assignee||'Unassigned')}</td><td class="${t.status!=='Resolved'&&new Date(t.due_at)<new Date()?'overdue':''}">${date(t.due_at)}</td></tr>`).join('')||'<tr><td colspan="5">No requests found.</td></tr>';}
async function loadTickets(){
 const current=++listVersion;
 const rows=await api('tickets?'+new URLSearchParams({q:$('search').value,status:$('filter').value}));
 if(current!==listVersion)return;
 $('rows').innerHTML=ticketRows(rows);$('count').textContent=rows.length+' requests';
}
async function refresh(){
 const [stats,tickets]=await Promise.all([api('analytics'),api('tickets')]);
 $('stats').innerHTML=[['Open requests',stats.open,'Awaiting resolution'],['Resolved',stats.resolved,'Completed requests'],['Overdue',stats.overdue,'Past resolution target'],['Avg. resolution',stats.resolution_hours===null?'—':stats.resolution_hours+'h','Currently resolved tickets']].map(([label,value,hint])=>`<article class="stat"><span>${label}</span><strong>${value}</strong><small>${hint}</small></article>`).join('');
 $('trend').innerHTML=stats.trend.map(d=>`<div class="bar-row"><span>${d.day.slice(5)}</span><progress aria-label="Requests on ${d.day}" value="${d.count}" max="${Math.max(1,...stats.trend.map(x=>x.count))}"></progress><b>${d.count}</b></div>`).join('');
 $('priorities').innerHTML=Object.entries(stats.priorities).map(([p,n])=>`<div class="bar-row"><span>${p}</span><progress aria-label="${p} requests" value="${n}" max="${Math.max(1,stats.open)}"></progress><b>${n}</b></div>`).join('');
 $('recent').innerHTML=`<div class="table-scroll"><table><thead><tr><th>Request</th><th>Priority</th><th>Status</th><th>Assigned to</th><th>Due</th></tr></thead><tbody>${ticketRows(tickets.slice(0,5))}</tbody></table></div>`;
 if(user.role!=='requester'){
 [assets,agents]=await Promise.all([api('assets'),api('users')]);
 $('assetGrid').innerHTML=assets.map(a=>`<article class="card"><div class="device-icon">▣</div><p class="asset-tag">${esc(a.tag)}</p><h2>${esc(a.name)}</h2><p class="muted">${esc(a.department)}</p>${badge(a.state)}</article>`).join('')||'<p>No equipment yet. Register your first asset.</p>';
 }
 await loadTickets();
}
async function enter(){user=await api('me');$('userName').textContent=user.name;$('role').textContent=user.role;document.querySelectorAll('[data-staff]').forEach(el=>el.hidden=user.role==='requester');$('login').hidden=true;$('workspace').hidden=false;show('overview');await refresh();}
async function detail(id){
 selected=await api('tickets/'+id);$('detailTitle').textContent='#'+selected.id+' · '+selected.title;$('description').textContent=selected.description;$('detailMeta').textContent=`${selected.priority} · ${selected.status} · Created ${date(selected.created_at)} · Due ${date(selected.due_at)}`;
 const form=$('updateForm');form.elements.status.value=selected.status;
 form.elements.assignee_id.innerHTML='<option value="">Unassigned</option>'+agents.map(a=>`<option value="${a.id}">${esc(a.name)}</option>`).join('');form.elements.assignee_id.value=selected.assignee_id||'';
 form.elements.asset_id.innerHTML='<option value="">No linked equipment</option>'+assets.map(a=>`<option value="${a.id}">${esc(a.tag)} · ${esc(a.name)}</option>`).join('');form.elements.asset_id.value=selected.asset_id||'';
 $('comments').innerHTML=selected.comments.map(c=>`<div class="entry"><strong>${esc(c.author)}</strong><p>${esc(c.body)}</p><time>${date(c.created_at)}</time></div>`).join('')||'<p class="muted">No comments yet.</p>';
 $('history').innerHTML=selected.history.map(h=>`<div class="entry"><strong>${esc(h.author)}</strong><p>${esc(h.action)}</p><time>${date(h.created_at)}</time></div>`).join('');
 if(!$('detailDialog').open)$('detailDialog').showModal();
}
function bindForm(id, action){$(id).onsubmit=safe(async e=>{e.preventDefault();const button=e.target.querySelector('button:not([type="button"])');button.disabled=true;try{await action(Object.fromEntries(new FormData(e.target)),e.target);}finally{button.disabled=false;}});}
bindForm('loginForm',async(d,f)=>{await api('login','POST',d);f.reset();await enter();});
bindForm('createForm',async(d,f)=>{const t=await api('tickets','POST',d);f.reset();$('createDialog').close();await refresh();await detail(t.id);notify('Request created.');});
bindForm('assetForm',async(d,f)=>{await api('assets','POST',d);f.reset();$('assetDialog').close();await refresh();notify('Equipment registered.');});
bindForm('updateForm',async d=>{await api('tickets/'+selected.id,'PATCH',{...d,version:selected.version,assignee_id:d.assignee_id?Number(d.assignee_id):null,asset_id:d.asset_id?Number(d.asset_id):null});await detail(selected.id);await refresh();notify('Changes saved.');});
bindForm('commentForm',async(d,f)=>{await api('tickets/'+selected.id+'/comments','POST',d);f.reset();await detail(selected.id);});
document.addEventListener('click',safe(async e=>{const b=e.target.closest('button');if(!b)return;if(b.dataset.view){show(b.dataset.view);await refresh();}if(b.dataset.ticket)await detail(Number(b.dataset.ticket));if(b.hasAttribute('data-close'))b.closest('dialog').close();}));
$('newTicket').onclick=()=> $('createDialog').showModal();$('newAsset').onclick=()=> $('assetDialog').showModal();
$('logout').onclick=safe(async()=>{await api('logout','POST',{});user=null;document.querySelectorAll('dialog[open]').forEach(d=>d.close());$('workspace').hidden=true;$('login').hidden=false;});
$('search').oninput=()=>{clearTimeout(searchTimer);searchTimer=setTimeout(safe(loadTickets),250);};$('filter').onchange=safe(loadTickets);
$('export').onclick=safe(async()=>{const response=await fetch('/api/report.csv?'+new URLSearchParams({q:$('search').value,status:$('filter').value}));if(!response.ok)throw Error('Export failed. Please sign in again.');const url=URL.createObjectURL(await response.blob());const link=document.createElement('a');link.href=url;link.download='opsdesk-report.csv';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
enter().catch(error=>{if(error.message!=='Please sign in.')notify(error.message);});
