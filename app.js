const defaultTickets = [
  { id: 1042, title: 'Network access unavailable', user: 'Finance Department', priority: 'High', status: 'In Progress' },
  { id: 1041, title: 'Printer driver installation', user: 'Administrative Office', priority: 'Medium', status: 'Open' },
  { id: 1040, title: 'Windows user profile issue', user: 'HR Department', priority: 'Critical', status: 'Open' },
  { id: 1039, title: 'Microsoft Office activation', user: 'Registry Office', priority: 'Low', status: 'Resolved' },
  { id: 1038, title: 'Shared folder permissions', user: 'Accounting', priority: 'Medium', status: 'Resolved' }
];

const defaultAssets = [
  { icon: '💻', name: 'Dell OptiPlex 7090', tag: 'PC-ADM-021', owner: 'Administration', state: 'Active' },
  { icon: '🖥️', name: 'HP ProDesk 600', tag: 'PC-FIN-014', owner: 'Finance', state: 'Active' },
  { icon: '🖨️', name: 'HP LaserJet Pro', tag: 'PRN-008', owner: 'Registry', state: 'Maintenance' },
  { icon: '🌐', name: 'Cisco Switch 24P', tag: 'NET-003', owner: 'Server Room', state: 'Active' },
  { icon: '💾', name: 'Backup NAS', tag: 'SRV-002', owner: 'IT Office', state: 'Active' },
  { icon: '📡', name: 'Wi-Fi Access Point', tag: 'NET-011', owner: 'Public Hall', state: 'Active' }
];

const priorities = ['Low', 'Medium', 'High', 'Critical'];
const statuses = ['Open', 'In Progress', 'Resolved'];
const notice = message => { document.getElementById('notice').textContent = message; };
const escapeHTML = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function readData(key, fallback, valid) {
  try {
    const raw = localStorage.getItem(key);
    if (raw === null) return structuredClone(fallback);
    const data = JSON.parse(raw);
    if (!Array.isArray(data) || !data.every(valid)) throw new Error('Invalid data');
    return data;
  } catch { notice('Saved data could not be loaded. Sample data is shown.'); return structuredClone(fallback); }
}
let tickets = readData('supportdeskTickets', defaultTickets, t => t && Number.isSafeInteger(t.id) && typeof t.title === 'string' && typeof t.user === 'string' && priorities.includes(t.priority) && statuses.includes(t.status));
let assets = readData('supportdeskAssets', defaultAssets, a => a && ['name','tag','owner'].every(k => typeof a[k] === 'string') && ['Active','Maintenance','Retired'].includes(a.state));
function persist(key, value) {
  try { localStorage.setItem(key, JSON.stringify(value)); notice('Changes saved in this browser.'); }
  catch { notice('Storage unavailable. Changes only last until this page closes. Export tickets to keep a copy.'); }
}

const views = {
  dashboard: document.getElementById('dashboardView'),
  tickets: document.getElementById('ticketsView'),
  assets: document.getElementById('assetsView'),
  knowledge: document.getElementById('knowledgeView')
};
const titles = { dashboard: 'Operations Dashboard', tickets: 'Support Tickets', assets: 'Asset Inventory', knowledge: 'Knowledge Base' };

function saveTickets(){ persist('supportdeskTickets', tickets); }

function priorityBadge(priority){ return `<span class="badge ${priority.toLowerCase()}">${priority}</span>`; }

function renderStats(){
  document.getElementById('openCount').textContent = tickets.filter(t => t.status !== 'Resolved').length;
  document.getElementById('resolvedCount').textContent = tickets.filter(t => t.status === 'Resolved').length;
  document.getElementById('criticalCount').textContent = tickets.filter(t => t.priority === 'Critical' && t.status !== 'Resolved').length;
  document.getElementById('assetCount').textContent = assets.length;
}

function renderRecent(){
  document.getElementById('recentTickets').innerHTML = tickets.slice(0,4).map(t => `
    <div class="ticket-row">
      <div><strong>#${t.id} · ${escapeHTML(t.title)}</strong><p>${escapeHTML(t.user)} · ${t.status}</p></div>
      ${priorityBadge(t.priority)}
    </div>`).join('');
}

function renderTickets(){
  const q = document.getElementById('ticketSearch').value.toLowerCase();
  const filter = document.getElementById('ticketFilter').value;
  const rows = tickets.filter(t =>
    (filter === 'all' || t.status === filter) &&
    (`${t.id} ${t.title} ${t.user} ${t.priority}`.toLowerCase().includes(q))
  );
  document.getElementById('ticketTableBody').innerHTML = rows.map(t => `
    <tr>
      <td>#${t.id}</td><td><strong>${escapeHTML(t.title)}</strong></td><td>${escapeHTML(t.user)}</td><td>${priorityBadge(t.priority)}</td>
      <td>${t.status}</td>
      <td><select aria-label="Status for ticket ${t.id}" class="status-select" data-id="${t.id}">
        ${['Open','In Progress','Resolved'].map(s => `<option ${s===t.status?'selected':''}>${s}</option>`).join('')}
      </select></td>
    </tr>`).join('') || '<tr><td colspan="6">No tickets found.</td></tr>';

  document.querySelectorAll('.status-select').forEach(select => select.addEventListener('change', e => {
    const ticket = tickets.find(t => t.id === Number(e.target.dataset.id));
    ticket.status = e.target.value; saveTickets(); renderAll();
  }));
}

function renderAssets(){
  document.getElementById('assetGrid').innerHTML = assets.map(a => `
    <article class="asset-card"><div class="asset-icon">${escapeHTML(a.icon || '💻')}</div><h3>${escapeHTML(a.name)}</h3><p>${escapeHTML(a.tag)} · ${escapeHTML(a.owner)}</p><span class="status ${a.state==='Active'?'good':'warning'}">${a.state}</span></article>`).join('');
}

function renderAll(){ renderStats(); renderRecent(); renderTickets(); renderAssets(); }

function switchView(name){
  Object.values(views).forEach(v => v.classList.remove('active-view'));
  views[name].classList.add('active-view');
  document.getElementById('pageTitle').textContent = titles[name];
  document.querySelectorAll('.nav-item').forEach(btn => btn.classList.toggle('active', btn.dataset.view === name));
}

document.querySelectorAll('.nav-item').forEach(btn => btn.addEventListener('click', () => switchView(btn.dataset.view)));
document.querySelectorAll('[data-go]').forEach(btn => btn.addEventListener('click', () => switchView(btn.dataset.go)));
document.getElementById('ticketSearch').addEventListener('input', renderTickets);
document.getElementById('ticketFilter').addEventListener('change', renderTickets);

const modal = document.getElementById('ticketModal');
document.getElementById('newTicketBtn').addEventListener('click', () => modal.showModal());
document.getElementById('closeModal').addEventListener('click', () => modal.close());
document.getElementById('ticketForm').addEventListener('submit', e => {
  e.preventDefault();
  const data = new FormData(e.target);
  const title = data.get('title').trim(), user = data.get('user').trim();
  if (!title || !user) { notice('Please enter a title and requester.'); return; }
  tickets.unshift({id: Math.max(1000, ...tickets.map(t => t.id)) + 1, title, user, priority: data.get('priority'), status: data.get('status')});
  saveTickets(); e.target.reset(); modal.close(); renderAll(); switchView('tickets');
});
const assetModal = document.getElementById('assetModal');
document.getElementById('newAssetBtn').onclick = () => assetModal.showModal();
document.getElementById('closeAsset').onclick = () => assetModal.close();
document.getElementById('assetForm').onsubmit = e => {
  e.preventDefault();
  const data = Object.fromEntries(new FormData(e.target));
  ['name','tag','owner'].forEach(k => data[k] = data[k].trim());
  if (!data.name || !data.tag || !data.owner) { notice('Please complete every asset field.'); return; }
  if (assets.some(a => a.tag.toLowerCase() === data.tag.toLowerCase())) { notice('That asset tag already exists.'); return; }
  assets.push(data); persist('supportdeskAssets', assets); renderAll(); e.target.reset(); assetModal.close();
};
function csvCell(value) {
  let text = String(value);
  if (/^[=+@\-\t\r\n]/.test(text)) text = "'" + text;
  return '"' + text.replaceAll('"', '""') + '"';
}
document.getElementById('exportBtn').onclick = () => {
  const rows = [['ID','Issue','Requester','Priority','Status'], ...tickets.map(t => [t.id,t.title,t.user,t.priority,t.status])];
  const blob = new Blob(['\ufeff' + rows.map(r => r.map(csvCell).join(',')).join('\r\n')], {type:'text/csv;charset=utf-8;'});
  const url = URL.createObjectURL(blob), link = document.createElement('a');
  link.href = url; link.download = 'supportdesk-tickets.csv'; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
};
renderAll();
