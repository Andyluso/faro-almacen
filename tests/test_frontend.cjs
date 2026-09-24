const fs = require('fs'), vm = require('vm'), assert = require('assert');
const source = fs.readFileSync(process.argv[2], 'utf8');
function extract(name) { const start = source.indexOf('function '+name+'('); const end=source.indexOf('\n}',start)+2; return source.slice(start,end); }
const children=[];
const container={innerHTML:'',appendChild(x){children.push(x)},querySelectorAll(){return []}};
const context={document:{getElementById(id){return id==='tasksListContainer'?container:null},createElement(){return {}}},tasksList:[{id:1,title:'<img src=x onerror=alert(1)>',category:'<script>alert(1)</script>',priority:'Alta',day_of_week:'Diario',is_completed:0}],currentTasksFilter:'all',initIcons(){}};
vm.createContext(context);
vm.runInContext(extract('escapeHtml')+'\n'+extract('renderTasksList')+'\nrenderTasksList();',context);
if (process.argv.includes('--baseline')) {
 assert(children[0].innerHTML.includes('<img src=x onerror=alert(1)>')); console.log('CONFIRMED: original task renderer inserts active HTML');
} else {
 assert(!children[0].innerHTML.includes('<img src=x')); assert(children[0].innerHTML.includes('&lt;img'));
 vm.runInContext(extract('escapeJsAttribute'),context);
 const payload="a');globalThis.pwned=true;//\\\"\nñ";
 context.payload=payload;
 const encoded=vm.runInContext('escapeJsAttribute(payload)',context);
 context.result=null;
 vm.runInContext("result='"+encoded+"'",context);
 assert.strictEqual(context.result,payload); assert.strictEqual(context.pwned,undefined);
 console.log('PASS: task rendering and inline-handler escaping preserve text without executing it');
}
