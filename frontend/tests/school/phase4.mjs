// Run against the guarded disposable Phase 4 fixture and production preview on :5177.
import { createRequire } from 'node:module';
import fs from 'node:fs';
import assert from 'node:assert/strict';
const require=createRequire(import.meta.url);
const {chromium}=require(process.env.SCHOOL_PLAYWRIGHT||'/tmp/school25-tooling/node_modules/playwright');
const fx=JSON.parse(fs.readFileSync('/tmp/school-phase4-browser-fixture.json','utf8'));
const BASE='http://127.0.0.1:5177';
const browser=await chromium.launch({headless:true,args:['--no-sandbox']});
const report={checks:[],errors:[],responses:[]};
async function session(username){
 const context=await browser.newContext({viewport:{width:1366,height:900}});
 const login=await context.request.post(BASE+'/api/v1/auth/login/',{data:{username,password:'LocalPhase4Only123!'}});
 assert.equal(login.status(),200,await login.text());const tokens=(await login.json()).data;
 await context.addInitScript(({access,refresh})=>{localStorage.setItem('access_token',access);localStorage.setItem('refresh_token',refresh);},tokens);
 const page=await context.newPage();page.setDefaultTimeout(15000);
 page.on('pageerror',e=>report.errors.push(e.message));
 page.on('dialog',d=>d.accept());
 page.on('response',r=>{if(r.url().includes('/school/'))report.responses.push({who:username,method:r.request().method(),path:new URL(r.url()).pathname,status:r.status()});});
 const go=async url=>{await page.goto(BASE+url);await page.waitForLoadState('networkidle');};
 const field=async(name,value)=>{const l=page.locator('#sis-'+name);await l.waitFor({state:'visible'});await page.waitForFunction(id=>!document.getElementById(id)?.disabled,'sis-'+name);if(await l.evaluate(e=>e.tagName)==='SELECT')await l.selectOption(String(value));else await l.fill(String(value));};
 const action=async(title,values={})=>{await page.getByRole('button',{name:title,exact:true}).click();for(const [k,v] of Object.entries(values))await field(k,v);const r=page.waitForResponse(x=>x.url().includes('/school/sis/')&&x.request().method()==='POST');await page.getByRole('button',{name:'Confirm',exact:true}).click();const res=await r;assert.equal(res.status(),200,JSON.stringify(await res.json()));await page.waitForLoadState('networkidle');await page.waitForTimeout(250);report.checks.push(title);};
 return {context,page,go,field,action};
}
async function lesson(o,values,expect){
 await o.go(`/school/sis/timetable-entries/new?version_id=${fx.version}`);
 for(const [k,v] of Object.entries(values))await o.field(k,v);
 const r=o.page.waitForResponse(x=>x.url().endsWith('/sis/timetable-entries/')&&x.request().method()==='POST');
 await o.page.getByRole('button',{name:'Save',exact:true}).click();const res=await r;assert.equal(res.status(),expect,JSON.stringify(await res.json()));return res;
}
try {
 const owner=await session('owner');
 const base={weekday:'1',school_class_id:fx.klass,version_id:fx.version};
 await lesson(owner,{...base,period_id:fx.p1,subject_offering_id:fx.math,staff_id:fx.staff1,classroom_id:fx.room1},201);report.checks.push('Lesson created');
 await lesson(owner,{...base,period_id:fx.p1,subject_offering_id:fx.sci,classroom_id:fx.room2},400);
 assert.match(await owner.page.getByRole('alert').first().innerText(),/overlapping period|already has a lesson/i);report.checks.push('Conflicting lesson rejected with a visible message');
 await lesson(owner,{...base,period_id:fx.p2,subject_offering_id:fx.sci,staff_id:fx.staff2,classroom_id:fx.room2},201);report.checks.push('Second lesson created');
 await owner.go(`/school/sis/timetable-versions/${fx.version}`);await owner.action('Publish timetable');
 assert.match(await owner.page.locator('main').innerText(),/published/i);
 await owner.go('/school/timetable');await owner.field('version_id',fx.version);await owner.page.waitForLoadState('networkidle');
 const grid=await owner.page.locator('table').innerText();assert.match(grid,/M5/);assert.match(grid,/S5/);report.checks.push('Timetable grid shows published lessons');
 await owner.go(`/school/sis/timetable-versions/${fx.version}`);
 // Published timetables are immutable in the UI too: lessons cannot be added to a non-draft version.
 const teacher=await session(fx.teacher);
 await teacher.go(`/school/sis/timetable-versions/${fx.version}`);
 assert.equal(await teacher.page.getByRole('button',{name:'Publish timetable',exact:true}).count(),0);report.checks.push('Teacher has no publish command');
 await teacher.go('/school/attendance');
 await teacher.field('branch_id',fx.branch);await teacher.field('school_class_id',fx.klass);await teacher.field('section_id',fx.section);
 await teacher.page.getByRole('button',{name:'Load class list',exact:true}).click();await teacher.page.waitForLoadState('networkidle');
 await teacher.page.getByRole('button',{name:'Mark all present',exact:true}).click();
 const statuses=teacher.page.locator('select[id^="st-"]');assert.equal(await statuses.count(),3);await statuses.nth(1).selectOption('absent');
 await teacher.page.getByRole('button',{name:'Save draft',exact:true}).click();await teacher.page.waitForSelector('text=saved as a draft');report.checks.push('Draft attendance saved');
 await teacher.page.getByRole('button',{name:'Submit attendance',exact:true}).click();await teacher.page.waitForSelector('text=submitted and locked');
 assert(await statuses.first().isDisabled());report.checks.push('Submitted attendance is locked');
 await teacher.go(`/school/sis/attendance-records?session_id=`);
 await teacher.page.locator('tbody tr',{hasText:'absent'}).getByRole('link',{name:'View'}).click();await teacher.page.waitForLoadState('networkidle');
 const which=await teacher.page.locator('main').innerText();
 await teacher.action('Request correction',{new_status:'present',reason:'Arrived late and was missed at roll call'});report.checks.push('Correction requested');
 await owner.go('/school/sis/attendance-corrections');await owner.page.locator('tbody').getByRole('link',{name:'View'}).first().click();await owner.page.waitForLoadState('networkidle');
 await owner.action('Approve correction',{decision_note:'Confirmed'});
 await owner.go('/school/sis/attendance-corrections');assert.match(await owner.page.locator('tbody').innerText(),/approved/i);report.checks.push('Correction approved');
 void which;
 for(const [name,o] of [['owner',owner],['teacher',teacher]])for(const width of [1366,768,390]){await o.page.setViewportSize({width,height:900});for(const url of ['/school/attendance','/school/timetable']){await o.go(url);assert(await o.page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`overflow ${name} ${url} at ${width}`);}}
 report.checks.push('No horizontal page overflow at 1366/768/390');
 const bad=report.responses.filter(r=>r.status>=400);
 assert.deepEqual(report.errors,[]);
 assert.deepEqual(bad.map(r=>`${r.method} ${r.path} ${r.status}`),['POST /api/v1/school/sis/timetable-entries/ 400'],'only the deliberate conflict may fail');
 console.log(JSON.stringify({checks:report.checks,errors:report.errors},null,2));
} finally {
 fs.writeFileSync('/tmp/school-phase4-browser-report.json',JSON.stringify(report,null,2));await browser.close();
}
