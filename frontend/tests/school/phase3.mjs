// Run against the guarded disposable fixture and production preview on :5177.
import { createRequire } from 'node:module';
import fs from 'node:fs';
import assert from 'node:assert/strict';
const require=createRequire(import.meta.url);
const {chromium}=require(process.env.SCHOOL_PLAYWRIGHT||'/tmp/school25-tooling/node_modules/playwright');
const fixture=JSON.parse(fs.readFileSync('/tmp/school-phase3-browser-fixture.json','utf8'));
const browser=await chromium.launch({headless:true,args:['--no-sandbox']});
const context=await browser.newContext({viewport:{width:1366,height:900}});
const report={checks:[],errors:[],responses:[]};
try {
 const login=await context.request.post('http://127.0.0.1:5177/api/v1/auth/login/',{data:{username:'owner',password:'LocalPhase3Only123!'}});
 assert.equal(login.status(),200,await login.text());const session=(await login.json()).data;
 await context.addInitScript(({access,refresh})=>{localStorage.setItem('access_token',access);localStorage.setItem('refresh_token',refresh);},session);
 const page=await context.newPage();page.setDefaultTimeout(15000);
 page.on('pageerror',e=>report.errors.push(e.message));
 page.on('dialog',dialog=>dialog.accept());
 page.on('response',r=>{if(r.url().includes('/school/'))report.responses.push({path:new URL(r.url()).pathname,status:r.status()});});
 async function go(url){await page.goto('http://127.0.0.1:5177'+url);await page.waitForLoadState('networkidle');}
 async function field(name,value){const locator=page.locator('#sis-'+name);await locator.waitFor({state:'visible'});await page.waitForFunction(id=>!document.getElementById(id)?.disabled,'sis-'+name);if(await locator.evaluate(e=>e.tagName)==='SELECT')await locator.selectOption(value);else await locator.fill(value);}
 async function create(resource,values){await go(`/school/sis/${resource}/new`);for(const [key,value]of Object.entries(values))await field(key,value);const response=page.waitForResponse(r=>r.url().endsWith(`/sis/${resource}/`)&&r.request().method()==='POST');await page.getByRole('button',{name:'Save',exact:true}).click();const r=await response;assert.equal(r.status(),201,JSON.stringify(await r.json()));const row=(await r.json()).data;await page.waitForURL(`**/${row.id}`);await page.waitForLoadState('networkidle');report.checks.push(resource+' create and detail');return row;}
 async function action(title,values={}){await page.getByRole('button',{name:title,exact:true}).click();for(const [key,value]of Object.entries(values))await field(key,value);const response=page.waitForResponse(r=>r.url().includes('/school/sis/')&&r.request().method()==='POST');await page.getByRole('button',{name:'Confirm',exact:true}).click();const r=await response;assert.equal(r.status(),200,JSON.stringify(await r.json()));await page.waitForLoadState('networkidle');await page.waitForTimeout(250);report.checks.push(title);return (await r.json()).data;}
 await create('guardians',{branch_id:fixture.branch,first_name:'Browser parent',national_id:'LOCAL-TEST',phone:'123456'});
 const applicant=await create('applicants',{branch_id:fixture.branch,first_name:'Browser child',last_name:'Phase3',date_of_birth:'2015-02-02'});
 await create('applications',{branch_id:fixture.branch,applicant_id:applicant.id,academic_year_id:fixture.year,school_class_id:fixture.klass,section_id:fixture.section});
 await action('Submit application');await action('Review documents');await action('Complete review');
 await action('Record decision',{decision:'accepted',reason:'Browser acceptance'});
 await action('Enroll student',{start_date:'2026-09-01'});
 await page.getByRole('link',{name:'Open enrolled student',exact:true}).click();await page.waitForLoadState('networkidle');
 const studentUrl=new URL(page.url()).pathname;
 await action('Transfer placement',{reason:'Move stream',effective_date:'2026-09-02',academic_year_id:fixture.year,school_class_id:fixture.klass});
 await page.getByRole('link',{name:'Enrollments',exact:true}).click();await page.waitForLoadState('networkidle');assert.match(await page.locator('tbody').innerText(),/transferred/);report.checks.push('Preserved enrollment history');
 await go(studentUrl);await action('Withdraw student',{reason:'Relocation',effective_date:'2026-09-03'});
 await action('Re-enroll student',{reason:'Returned',effective_date:'2026-09-04',academic_year_id:fixture.year,school_class_id:fixture.klass});
 await go('/school/admissions');assert.match(await page.locator('main').innerText(),/Total applications/i);report.checks.push('Admissions dashboard');
 for(const width of [1366,768,390]){await page.setViewportSize({width,height:900});await go('/school/sis/students');assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`overflow at ${width}`);report.checks.push(`Student list ${width}px`);}
 assert.deepEqual(report.errors,[]);assert.deepEqual(report.responses.filter(r=>r.status>=400),[]);
 console.log(JSON.stringify({checks:report.checks,errors:report.errors},null,2));
} finally {
 fs.writeFileSync('/tmp/school-phase3-browser-report.json',JSON.stringify(report,null,2));await browser.close();
}
