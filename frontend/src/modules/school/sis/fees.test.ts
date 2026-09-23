import { describe,it,expect } from 'vitest';
import { commands,commandPayload } from './workflows';
import { resources } from './config';
import { billingModes,billingError } from './billing';
import { ApiClientError } from '@/services/api/http';
describe('Phase 6 financial controls',()=>{
 it('issues only the saved preview fingerprint',()=>{
  const row={id:'batch',name:'Fees',status:'preview',fingerprint:'fee-hash'};const action=commands('fee-batches',row)[0];expect(action.permission).toBe('fee_batch.issue');expect(commandPayload(action,{}, {},row)).toEqual({fingerprint:'fee-hash'});expect(commands('fee-batches',{...row,status:'issued'})).toEqual([]);
 });
 it('requires reasons for financial reversals and removes replay buttons',()=>{
  for(const resource of ['billing-allocations','billing-credits','billing-refunds']){
   const row={id:'x',name:'Entry'};expect(commands(resource,row)[0].fields.find(f=>f.name==='reason')?.required).toBe(true);expect(commands(resource,{...row,reversal_id:'done'})).toEqual([]);
  }
 });
 it('keeps monetary history and balances read only',()=>{
  for(const key of ['fee-batches','fee-assignments','fee-invoices','billing-invoices','billing-receipts','billing-allocations','billing-credits','billing-refunds','billing-lines'])expect(resources[key].readonly).toBe(true);
 });
 it('separates receipt recording from allocation and bounds credit to a fee line',()=>{
  expect(billingModes['billing-receipts'].fields.some(f=>f.name==='invoice_id')).toBe(false);
  expect(billingModes['billing-allocations'].fields.find(f=>f.name==='invoice_id')?.lookup).toBe('billing-invoices');
  expect(billingModes['billing-credits'].fields.find(f=>f.name==='invoice_line_id')?.required).toBe(true);
 });
 it('displays the server financial blocker',()=>{
  expect(billingError(new ApiClientError('Validation failed',{fieldErrors:{billing:['Period is closed.']}}))).toBe('Period is closed.');
 });
});
