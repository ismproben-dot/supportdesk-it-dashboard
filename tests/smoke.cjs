// Dependency-free behavior checks with a minimal DOM harness (not browser layout tests).
const vm = require('node:vm'), fs = require('node:fs'), assert = require('node:assert/strict');
const elements = new Map(), storage = new Map();
function element(id) {
 if (!elements.has(id)) elements.set(id, {value:id==='ticketFilter'?'all':'',textContent:'',innerHTML:'',handlers:{},classList:{add(){},remove(){},toggle(){}},addEventListener(n,f){this.handlers[n]=f;},showModal(){this.open=true;},close(){this.open=false;}});
 return elements.get(id);
}
const context=vm.createContext({document:{getElementById:element,querySelectorAll:()=>[]},localStorage:{getItem:k=>storage.get(k)??null,setItem:(k,v)=>storage.set(k,v)},structuredClone,FormData:class {constructor(data){this.data=data;}get(k){return this.data[k];}*[Symbol.iterator](){yield* Object.entries(this.data).filter(([k])=>k!=='reset');}},setTimeout,Blob,URL});
vm.runInContext(fs.readFileSync(require('node:path').join(__dirname,'../app.js'),'utf8'),context);
assert.equal(element('openCount').textContent,3);
element('ticketForm').handlers.submit({preventDefault(){},target:{title:'<script>bad()</script>',user:'Support',priority:'High',status:'Open',reset(){}}});
assert.equal(element('openCount').textContent,4);assert.match(element('ticketTableBody').innerHTML,/&lt;script&gt;/);assert.ok(!element('ticketTableBody').innerHTML.includes('<script>'));
element('ticketSearch').value='<script>';vm.runInContext('renderTickets()',context);assert.equal((element('ticketTableBody').innerHTML.match(/<tr>/g)||[]).length,1);
element('ticketFilter').value='Resolved';vm.runInContext('renderTickets()',context);assert.match(element('ticketTableBody').innerHTML,/No tickets/);
vm.runInContext("tickets[0].status='Resolved';saveTickets();renderStats()",context);assert.equal(element('resolvedCount').textContent,3);assert.equal(JSON.parse(storage.get('supportdeskTickets'))[0].status,'Resolved');
const asset={name:'Laptop',tag:'TEST-01',owner:'IT',state:'Active',reset(){}};
element('assetForm').onsubmit({preventDefault(){},target:asset});assert.equal(element('assetCount').textContent,7);
element('assetForm').onsubmit({preventDefault(){},target:asset});assert.equal(element('assetCount').textContent,7);assert.match(element('notice').textContent,/already exists/);
assert.equal(vm.runInContext('csvCell("=1+1")',context),'"\'=1+1"');
storage.set('broken','oops');assert.equal(vm.runInContext('readData("broken", [1], () => true).length',context),1);
console.log('PASS: ticket creation, escaped rendering, search/filter, status persistence, assets, duplicate tags, CSV protection, corrupt storage recovery');
