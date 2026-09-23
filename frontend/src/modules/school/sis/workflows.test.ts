import { describe, expect, it } from 'vitest';
import { commands, commandPayload } from './workflows';
import { payload } from './payload';
const row={id:'student',name:'Amina',status:'active',current_enrollment_id:'placement'};
describe('School Phase 3 workflow contracts',()=>{
 it('only offers enrollment after acceptance',()=>{
 expect(commands('applications',{...row,status:'under_review'}).map(c=>c.action)).not.toContain('enroll');
 expect(commands('applications',{...row,status:'accepted'}).map(c=>c.action)).toContain('enroll');
 expect(commands('applications',{...row,status:'enrolled'})).toEqual([]);
 });
 it('sends the source placement and reason for transfer',()=>{
 const command=commands('students',row).find(c=>c.action==='transfer')!;
 expect(commandPayload(command,{reason:'Move',effective_date:'2026-09-02'},{branch_id:'B'},row)).toEqual({reason:'Move',effective_date:'2026-09-02',enrollment_id:'placement',placement:{branch_id:'B'}});
 });
 it('keeps accepted placement server-owned during conversion',()=>{
 const command=commands('applications',{...row,status:'accepted'}).find(c=>c.action==='enroll')!;
 expect(commandPayload(command,{start_date:'2026-09-01'}, {}, row)).toEqual({placement:{start_date:'2026-09-01',roll_number:'',notes:''},document_override_reason:''});
 });
 it('allowlists form values and normalizes nullable relationships',()=>{
 expect(payload([{name:'family_id',label:'Family',kind:'relation',nullable:true}],{family_id:'',status:'graduated'})).toEqual({family_id:null});
 expect(payload([{name:'section_id',label:'Section',kind:'relation',nullable:true}],{})).toEqual({section_id:null});
 });
 it('does not expose later phase promotion workflows',()=>{
 expect(commands('students',row).map(c=>c.action)).not.toContain('promote');
 });
});
