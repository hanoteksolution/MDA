import { createRequire } from 'node:module';
import fs from 'node:fs';
import assert from 'node:assert/strict';
const require=createRequire(import.meta.url);
const {default:AxeBuilder}=require('/tmp/school25-tooling/node_modules/@axe-core/playwright');
const {chromium}=require(process.env.SCHOOL_PLAYWRIGHT || '/tmp/school25-tooling/node_modules/playwright');
const sessions=JSON.parse(fs.readFileSync('/tmp/school25-browser-session.json','utf8'));
const out='/tmp/school25-ux';fs.mkdirSync(out,{recursive:true});
const browser=await chromium.launch({headless:true,args:['--no-sandbox']});
const report={version:browser.version(),checks:[],errors:[],network:[],responsive:[]};
const run=Date.now().toString().slice(-7);const rows={};
async function contextFor(role){
 const c=await browser.newContext({viewport:{width:1366,height:900}});
 const response=await c.request.post('http://127.0.0.1:5174/api/v1/auth/login/',{data:{username:'browser_'+role,password:'LocalVerificationOnly123!'}});
 assert.equal(response.status(),200,await response.text());
 const session=(await response.json()).data;
 await c.addInitScript(({access,refresh})=>{if(!localStorage.getItem('access_token')){localStorage.setItem('access_token',access);localStorage.setItem('refresh_token',refresh);}},session);
 c.schoolToken=session.access;return c;
}
const context=await contextFor('A1_owner');const page=await context.newPage();page.setDefaultTimeout(15000);
page.on('pageerror',e=>report.errors.push(e.message));
page.on('response',r=>{if(r.url().includes('/api/v1/'))report.network.push({status:r.status(),path:new URL(r.url()).pathname});});
const base='/school/academics/';
async function go(path){console.log('PAGE',path);await page.goto('http://127.0.0.1:5174'+path);await page.waitForLoadState('networkidle');await page.waitForTimeout(1000);}
async function field(key,value){const el=page.locator('#'+key);await el.waitFor({state:'visible'});if(await el.evaluate(e=>e.tagName)==='SELECT'){await page.waitForFunction(id=>!document.getElementById(id)?.disabled,key);await el.selectOption(value);}else await el.fill(String(value));}
async function create(resource,values){await go(base+resource+'/new');for(const [key,value]of Object.entries(values))await field(key,value);const response=page.waitForResponse(r=>r.url().endsWith('/school/'+resource+'/')&&r.request().method()==='POST');await page.getByRole('button',{name:/^Save /}).last().click();const r=await response;assert.equal(r.status(),201,JSON.stringify(await r.json()));const data=(await r.json()).data;rows[resource]=data;await page.waitForURL('**/'+data.id);report.checks.push(resource+' create/detail');await page.getByRole('link',{name:'Edit',exact:true}).click();await page.waitForLoadState('networkidle');await field(resource==='campus-access'?'is_active':'name',resource==='campus-access'?'':values.name+' edited');const edited=page.waitForResponse(r=>r.request().method()==='PATCH'&&r.url().includes(data.id));await page.getByRole('button',{name:/^Save /}).last().click();assert.equal((await edited).status(),200);await page.waitForURL('**/'+data.id);report.checks.push(resource+' edit');return data.id;}
async function action(resource,label){await go(base+resource+'/'+rows[resource].id+(label==='Restore'?'?archived=true':''));await page.getByRole('button',{name:label,exact:true}).click();const dialog=page.getByRole('dialog');await dialog.waitFor();if(label==='Archive'&&resource==='subject-offerings'){await page.keyboard.press('Tab');report.checks.push('dialog focus inside: '+await dialog.evaluate(e=>e.contains(document.activeElement)));await page.screenshot({path:out+'/dialog.png'});}const response=page.waitForResponse(r=>r.request().method()==='POST'&&r.url().includes(rows[resource].id));await dialog.getByRole('button',{name:label==='Make current'?'activate':label.toLowerCase(),exact:true}).click();const r=await response;assert.equal(r.status(),200,await r.text());await page.waitForURL('**/'+resource);report.checks.push(resource+' '+label);}
try{
// Real rendered-page accessibility in both supported themes.
for(const dark of [false,true]){
 await go('/school');
 if(await page.locator('html').evaluate(e=>e.classList.contains('dark'))!==dark)await page.getByRole('button',{name:dark?'Switch to dark mode':'Switch to light mode'}).click();
 for(const path of ['/school',base+'subjects',base+'classes/new','/school/settings']){
  await go(path);
  const result=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();
  report.checks.push({path,dark,violations:result.violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))}))});
  await page.screenshot({path:out+'/'+(dark?'dark':'light')+'-'+path.split('/').filter(Boolean).join('-')+'.png',fullPage:true});
 }
}
// Keyboard dialog behavior and unsaved history navigation.
await go(base+'subjects');await page.getByRole('link',{name:'New subject',exact:true}).click();await field('name','Unsaved history');await page.waitForTimeout(250);console.log('HISTORY BEFORE',page.url(),await page.evaluate(()=>history.state));
page.once('dialog',d=>{console.log('BACK DIALOG',d.message());return d.dismiss();});await page.evaluate(()=>history.back());await page.waitForTimeout(600);console.log('HISTORY AFTER',page.url(),await page.evaluate(()=>history.state));assert.ok(page.url().endsWith('/new'));assert.equal(await page.locator('#name').inputValue(),'Unsaved history');
page.once('dialog',d=>d.accept());await page.getByRole('link',{name:'Cancel',exact:true}).click();report.checks.push('browser back and Cancel preserve/discard unsaved edits');
const subject=await create('subjects',{name:'UX subject '+run,code:'UX'+run});
await page.getByRole('button',{name:'Archive',exact:true}).click();const dialog=page.getByRole('dialog');await dialog.waitFor();
for(let i=0;i<8;i++){await page.keyboard.press('Tab');assert.ok(await dialog.evaluate(e=>e.contains(document.activeElement)));}
await page.keyboard.press('Escape');await dialog.waitFor({state:'hidden'});assert.equal(await page.getByRole('button',{name:'Archive',exact:true}).evaluate(e=>e===document.activeElement),true);report.checks.push('dialog focus trap Escape focus return');
// Table search / sort / empty / columns / action menu keyboard.
await go(base+'subjects');await page.getByPlaceholder('Search subjects…',{exact:true}).fill('UX subject '+run);await page.waitForTimeout(800);assert.equal(await page.getByRole('link',{name:'UX subject '+run+' edited',exact:true}).count(),1);
await page.getByRole('combobox',{name:'Sort records'}).selectOption('-name');await page.waitForTimeout(700);
await page.getByRole('button',{name:/Actions for UX subject/}).click();await page.getByRole('menuitem',{name:'View details'}).focus();await page.keyboard.press('Escape');assert.equal(await page.getByRole('menu').count(),0);
await page.getByPlaceholder('Search subjects…',{exact:true}).fill('missing-unique-'+run);await page.waitForTimeout(800);assert.ok((await page.locator('body').innerText()).includes('No subjects match'));report.checks.push('search sort empty row-menu keyboard');
// Page-size and pagination requests use actual server parameters.
for(let i=0;i<23;i++){const response=await page.request.post('http://127.0.0.1:5174/api/v1/school/subjects/',{headers:{Authorization:'Bearer '+context.schoolToken},data:{name:'Page sample '+run+' '+i,code:'PG'+run+i}});assert.equal(response.status(),201);}
await go(base+'subjects');await page.getByRole('combobox',{name:'Rows per page'}).click();await page.getByRole('option',{name:'10 / page',exact:true}).click();await page.waitForTimeout(600);const next=page.waitForResponse(r=>r.url().includes('/school/subjects/?')&&r.url().includes('page=2'));await page.getByRole('button',{name:'Next page',exact:true}).click();assert.equal((await next).status(),200);report.checks.push('server page size and next page');
await page.getByText('Visible columns',{exact:true}).click();await page.getByRole('checkbox',{name:'Short name',exact:true}).uncheck();assert.equal(await page.getByRole('columnheader',{name:'Short name',exact:true}).count(),0);report.checks.push('column visibility');
// Save & new persists once and resets the form.
await go(base+'subjects/new');await field('name','Save new '+run);await field('code','SN'+run);let saveRequests=0;const countSave=r=>{if(r.method()==='POST'&&r.url().endsWith('/school/subjects/'))saveRequests++;};page.on('request',countSave);const saveNew=page.waitForResponse(r=>r.url().endsWith('/school/subjects/')&&r.request().method()==='POST');await page.getByRole('button',{name:'Save & new',exact:true}).click({clickCount:2});assert.equal((await saveNew).status(),201);await page.getByRole('status').filter({hasText:'saved'}).waitFor();assert.equal(await page.locator('#name').inputValue(),'');assert.equal(saveRequests,1);page.off('request',countSave);report.checks.push('Save & new reset and duplicate-submit protection');
// Actual browser file input upload uses the shared media endpoint.
await go('/school/settings');await page.getByRole('combobox',{name:'Campus',exact:true}).selectOption(sessions.campus_A1);await page.waitForFunction(()=>document.getElementById('school_name')&&!document.getElementById('school_name').disabled);const upload=page.waitForResponse(r=>r.url().includes('/school/profile/logo/')&&r.request().method()==='POST');await page.getByLabel('Upload campus logo').setInputFiles({name:'logo.png',mimeType:'image/png',buffer:Buffer.from('iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2AAAAGUlEQVR4nGP0ZmhiIAUwkaR6VMOohiGlAQCmLQDt7QUqYwAAAABJRU5ErkJggg==','base64')});const uploaded=await upload;assert.equal(uploaded.status(),200,await uploaded.text());await page.getByRole('img',{name:'Campus logo'}).waitFor();report.checks.push('profile logo upload');
// Backend field validation, no duplicate Save while request is pending.
await go(base+'subjects/new');await field('name','Invalid marks');await field('code','BAD'+run);await field('maximum_marks','10');await field('pass_mark','50');
const invalid=page.waitForResponse(r=>r.request().method()==='POST'&&r.url().endsWith('/subjects/'));await page.getByRole('button',{name:'Save subject',exact:true}).click();assert.equal((await invalid).status(),400);assert.ok(await page.getByRole('alert').count());report.checks.push('backend validation visible');
page.once('dialog',d=>d.accept());await page.getByRole('link',{name:'Cancel',exact:true}).click();
// Controlled network failure and retry, without changing backend authorization.
await page.route('**/api/v1/school/subjects/?*',route=>route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({message:'Verification temporary outage'})}));
await go(base+'subjects');assert.ok(await page.getByRole('alert').count());await page.unroute('**/api/v1/school/subjects/?*');await page.getByRole('button',{name:'Retry',exact:true}).click();await page.waitForTimeout(1000);assert.equal(await page.getByRole('alert').count(),0);report.checks.push('network error Retry recovers');
for(const role of ['A1_principal','A1_teacher']){
 const c=await contextFor(role);const p=await c.newPage();await p.goto('http://127.0.0.1:5174/school/academics/classes');await p.waitForLoadState('networkidle');
 const options=await p.locator('#filter-branch_id option').allTextContents();assert.ok(options.includes('Campus A1'));assert.ok(!options.includes('Campus A2'));
 if(role==='A1_teacher'){assert.equal(await p.getByRole('link',{name:'New class',exact:true}).count(),0);await p.goto('http://127.0.0.1:5174'+base+'subjects/'+subject);await p.waitForLoadState('networkidle');assert.equal(await p.getByRole('link',{name:'Edit',exact:true}).count(),0);assert.equal(await p.getByRole('button',{name:'Archive',exact:true}).count(),0);}
 report.checks.push(role+' campus and action UI');await c.close();
}
}catch(e){report.failure=e.stack;console.error(e);await page.screenshot({path:out+'/failure.png',fullPage:true});}finally{fs.writeFileSync(out+'/report.json',JSON.stringify(report,null,2));await browser.close();}
if(report.failure)process.exitCode=1;
