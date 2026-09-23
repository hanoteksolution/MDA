import { createRequire } from 'node:module';
import fs from 'node:fs';
import assert from 'node:assert/strict';
const require=createRequire(import.meta.url);
const {chromium}=require(process.env.SCHOOL_PLAYWRIGHT || '/tmp/school25-tooling/node_modules/playwright');
const sessions=JSON.parse(fs.readFileSync('/tmp/school25-browser-session.json','utf8'));
const out='/tmp/school25-browser';fs.mkdirSync(out,{recursive:true});
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
await go('/school');assert.equal(await page.getByRole('heading',{name:'School overview'}).count(),1);
const campus=await create('campuses',{name:'Browser campus '+run,code:'BC'+run,company_id:sessions.company_A});
const year=await create('academic-years',{name:'Browser year '+run,code:'BY'+run,branch_id:campus,start_date:'2026-01-01',end_date:'2026-12-31'});
await action('academic-years','Make current');
const term=await create('terms',{name:'Browser term '+run,code:'BT'+run,branch_id:campus,academic_year_id:year,start_date:'2026-01-01',end_date:'2026-04-01'});await action('terms','Activate');
const level=await create('levels',{name:'Browser level '+run,code:'BL'+run});
const klass=await create('classes',{name:'Browser class '+run,code:'BK'+run,branch_id:campus,education_level_id:level});
const shift=await create('shifts',{name:'Browser shift '+run,code:'BH'+run,branch_id:campus,start_time:'08:00',end_time:'12:00'});
const section=await create('sections',{name:'Browser section '+run,code:'BS'+run,branch_id:campus,school_class_id:klass,shift_id:shift});
const category=await create('subject-categories',{name:'Browser category '+run,code:'BG'+run});
const subject=await create('subjects',{name:'Browser subject '+run,code:'BU'+run,category_id:category});
await create('subject-offerings',{name:'Browser offering '+run,code:'BO'+run,branch_id:campus,academic_year_id:year,term_id:term,school_class_id:klass,section_id:section,subject_id:subject});
await go('/school/settings');await page.getByRole('combobox',{name:'Campus',exact:true}).selectOption(sessions.campus_A1);await page.locator('#school_name').waitFor();await page.waitForFunction(()=>!document.getElementById('school_name').disabled);await field('school_name','Verified school '+run);await field('principal_user_id', await page.locator('#principal_user_id option').nth(1).getAttribute('value'));const profile=page.waitForResponse(r=>r.url().includes('/school/profile/')&&r.request().method()==='PUT');await page.getByRole('button',{name:'Save profile',exact:true}).click();assert.equal((await profile).status(),200);report.checks.push('profile update/principal');
// Unsaved Cancel must retain the form when dismissal is chosen.
await go(base+'subjects/new');await field('name','Unsaved');page.once('dialog',d=>d.dismiss());await page.getByRole('link',{name:'Cancel',exact:true}).click();assert.ok(page.url().endsWith('/new'));assert.equal(await page.locator('#name').inputValue(),'Unsaved');page.once('dialog',d=>d.accept());await page.getByRole('link',{name:'Cancel',exact:true}).click();report.checks.push('unsaved cancel retain/discard');
for(const width of [1920,1366,1024,768,390]){await page.setViewportSize({width,height:900});for(const path of ['/school',base+'subject-offerings',base+'classes/new']){await go(path);const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth+1);report.responsive.push({width,path,overflow});await page.screenshot({path:out+'/'+width+'-'+path.split('/').filter(Boolean).join('-')+'.png',fullPage:true});}}
await page.setViewportSize({width:1366,height:900});
for(const resource of ['subject-offerings','sections','classes','shifts','subjects','subject-categories','levels'])await action(resource,'Archive');await action('terms','Close');await action('terms','Archive');await action('academic-years','Close');await action('academic-years','Archive');await action('campuses','Archive');
for(const resource of ['campuses','academic-years','terms','levels','classes','shifts','sections','subject-categories','subjects','subject-offerings']){await action(resource,'Restore');if(!['campuses','academic-years','terms'].includes(resource)){await go(base+resource+'/'+rows[resource].id+'/edit');await field('status','active');const response=page.waitForResponse(r=>r.request().method()==='PATCH');await page.getByRole('button',{name:/^Save /}).last().click();assert.equal((await response).status(),200);}}
const teacherContext=await contextFor('A1_teacher');const teacher=await teacherContext.newPage();await teacher.goto('http://127.0.0.1:5174'+base+'subjects');await teacher.waitForLoadState('networkidle');assert.equal(await teacher.getByRole('link',{name:/^New subject/}).count(),0);report.checks.push('teacher create hidden');const forbidden=await teacher.request.post('http://127.0.0.1:5174/api/v1/school/subjects/',{headers:{Authorization:'Bearer '+teacherContext.schoolToken},data:{name:'Forbidden',code:'NO'}});assert.equal(forbidden.status(),403);report.checks.push('teacher manual POST forbidden');await teacherContext.close();
}catch(e){report.failure=e.stack;await page.screenshot({path:out+'/failure.png',fullPage:true});console.error(e);}finally{report.rows=rows;fs.writeFileSync(out+'/report.json',JSON.stringify(report,null,2));await browser.close();}
if(report.failure)process.exitCode=1;
