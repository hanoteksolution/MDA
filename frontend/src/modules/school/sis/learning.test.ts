import { describe,it,expect } from 'vitest';
import { commands,commandPayload } from './workflows';
import { resources } from './config';
import type { Row } from './api';
describe('Phase 5 workflows',()=>{
 it('passes revision through moderation and requires reason to reopen',()=>{
  const row={id:'e',name:'Exam',status:'submitted',revision:7} as Row;
  const actions=commands('exams',row);expect(actions.map(a=>a.action)).toEqual(['moderate','reopen']);
  expect(commandPayload(actions[0],{}, {},row)).toEqual({expected_revision:7});
  expect(actions[1].fields.find(f=>f.name==='reason')?.required).toBe(true);
 });
 it('only commits an unchanged saved preview',()=>{
  const row={id:'b',name:'Batch',status:'preview',fingerprint:'saved-hash'} as Row;
  const cmd=commands('promotion-batches',row)[0];expect(commandPayload(cmd,{}, {},row)).toEqual({fingerprint:'saved-hash'});
  expect(commands('promotion-batches',{...row,status:'committed'})).toEqual([]);
 });
 it('keeps publications reports and promotion history read only',()=>{
  for(const resource of ['marks','result-publications','report-cards','promotion-items','promotion-batches'])expect(resources[resource].readonly).toBe(true);
 });
 it('separates assignment publish and close',()=>{
  expect(commands('assignments',{id:'a',name:'A',status:'draft'})[0].permission).toBe('assignment.publish');
  expect(commands('assignments',{id:'a',name:'A',status:'published'})[0].action).toBe('close');
 });
});
