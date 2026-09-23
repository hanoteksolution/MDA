import type { Field, Row, Values } from './api';
export type Command = {action:string; title:string; permission:string; fields:Field[]; placement?:boolean};
const field=(name:string,kind='text',required=false):Field=>({name,label:name.replace(/_/g,' '),kind,required});
const reason=field('reason','textarea',true);
const effective=field('effective_date','date',true);
const choice=(name:string,values:string[]):Field=>({...field(name,'select',true),choices:values.map(value=>({value,label:value.replace(/_/g,' ')}))});
export function commands(resource:string,row:Row):Command[] {
 const status=String(row.status);const result:Command[]=[];
 const add=(action:string,title:string,permission:string,fields:Field[]=[],placement=false)=>result.push({action,title,permission,fields,placement});
 if(resource==='applications') {
  if(status==='draft')add('submit','Submit application','admission.submit');
  if(status==='submitted')add('review','Review documents','admission.review');
  if(['document_review','assessment_completed','interview_completed'].includes(status))add('under-review','Complete review','admission.review');
  if(['under_review','waitlisted'].includes(status))add('decide','Record decision','admission.decide',[choice('decision',['accepted','waitlisted','rejected']),reason,{...field('approved_class_id','relation'),lookup:'classes'},{...field('approved_section_id','relation'),lookup:'sections',nullable:true},field('offer_expiry','date'),field('conditions','textarea'),field('document_override_reason','textarea')]);
  if(status==='accepted')add('enroll','Enroll student','admission.enroll',[field('start_date','date',true),field('roll_number'),field('notes','textarea'),field('document_override_reason','textarea')]);
  if(!['enrolled','rejected','withdrawn','cancelled'].includes(status))add('withdraw','Withdraw application','admission.withdraw',[reason]);
 }
 if(resource==='students') {
  if(['active','suspended'].includes(status)){
   add('transfer','Transfer placement','student.transfer',[reason,effective],true);
   add('withdraw','Withdraw student','student.withdraw',[reason,effective]);
   if(status==='active')add('suspend','Suspend student','student.change_status',[reason,effective]);
   else add('reactivate','Reactivate student','student.change_status',[reason,effective]);
  }
  if(['withdrawn','transferred','inactive'].includes(status))add('reenroll','Re-enroll student','student.reenroll',[reason,effective],true);
 }
 if(['assessments','interviews'].includes(resource)&&status==='scheduled') {
  const permission=resource==='assessments'?'admission.assess':'admission.interview';
  add('complete','Complete appointment',permission,[field('score','number'),resource==='assessments'?choice('result',['pass','fail','review','not_required']):choice('recommendation',['accept','reject','review']),field('notes','textarea')]);
  add('cancel','Cancel appointment',permission,[reason]);
 }
 if(['applicant-documents','student-documents'].includes(resource))add('verify','Verify document',resource==='applicant-documents'?'admission_document.verify':'student_document.verify',[choice('verification_status',['verified','rejected','expired','requires_reupload']),reason]);
 if(resource==='timetable-versions'){
  if(status==='draft')add('publish','Publish timetable','timetable.publish');
  if(status!=='archived')add('clone','Clone into new draft','timetable.create',[field('name','text',true),field('effective_from','date',true)]);
 }
 if(resource==='attendance-records')add('correct','Request correction','attendance_correction.request',[choice('new_status',['present','absent','late','excused','half_day']),reason]);
 if(resource==='attendance-corrections'&&status==='pending'){
  add('approve','Approve correction','attendance_correction.approve',[field('decision_note','textarea')]);
  add('reject','Reject correction','attendance_correction.approve',[{...field('decision_note','textarea',true)}]);
 }
 if(resource==='attendance-sessions'&&status==='open')add('submit','Submit attendance','attendance.take');
 if(resource==='assignments'){
  if(status==='draft')add('publish','Publish assignment','assignment.publish');
  if(status==='published')add('close','Close assignment','assignment.close');
 }
 if(resource==='submissions')add('grade','Grade submission','submission.grade',[field('score','number',true),field('feedback','textarea')]);
 if(resource==='exams'){
  if(status==='draft')add('submit','Submit marks','exam.submit');
  if(status==='submitted')add('moderate','Approve moderated marks','exam.moderate');
  if(status==='moderated')add('publish','Publish report cards','exam.publish');
  if(status!=='draft')add('reopen','Reopen with reason','exam.reopen',[reason]);
 }
 if(resource==='promotion-batches'&&status==='preview')add('commit','Commit saved promotion preview','promotion.commit');
 if(resource==='fee-structures'){
  if(status==='draft')add('activate','Activate fee structure','fee_structure.activate');
  if(status==='active')add('close','Close fee structure','fee_structure.close');
 }
 if(resource==='fee-discounts'&&status==='requested'){
  add('approve','Approve discount','fee_discount.approve');add('reject','Reject discount','fee_discount.reject');
 }
 if(resource==='fee-batches'&&status==='preview')add('issue','Issue saved fee preview','fee_batch.issue');
 if(resource==='billing-receipts'&&status==='posted')add('reverse','Reverse receipt','billing_receipt.reverse',[reason]);
 if(resource==='billing-allocations'&&!row.reversal_id)add('reverse','Reverse allocation','billing_allocation.reverse',[reason]);
 if(['billing-credits','billing-refunds'].includes(resource)&&!row.reversal_id)add('reverse','Reverse adjustment',resource==='billing-credits'?'billing_credit.reverse':'billing_refund.reverse',[reason]);
 return result;
}
export function commandPayload(command:Command,values:Values,placement:Values,row:Row):Values {
 const data={...values};
 if(command.permission.startsWith('exam.'))data.expected_revision=row.revision;
 if(['promotion.commit','fee_batch.issue'].includes(command.permission))data.fingerprint=row.fingerprint;
 for(const key of Object.keys(data))if(data[key]==='')delete data[key];
 if(command.action==='enroll')return {placement:{start_date:data.start_date,roll_number:data.roll_number||'',notes:data.notes||''},document_override_reason:data.document_override_reason||''};
 if(command.placement)data.placement=placement;
 if(row.current_enrollment_id)data.enrollment_id=row.current_enrollment_id;
 return data;
}
