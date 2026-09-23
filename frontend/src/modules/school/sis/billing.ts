import type { Field } from './api';
import { ApiClientError } from '@/services/api/http';
const relation=(name:string,label:string,lookup:string,sis=true):Field=>({name,label,lookup,sis,kind:'relation',required:true});
const common:Field[]=[{name:'amount',label:'Amount',kind:'number',required:true},{name:'date',label:'Date',kind:'date',required:true}];
export const billingModes={
 'billing-receipts':{title:'Collect receipt / advance',permission:'school.billing_receipt.collect',fields:[relation('branch_id','Campus','lookups/campuses',false),relation('customer_id','Billing customer','billing-customers'),relation('method_id','Payment method','billing-methods'),...common,{name:'reference',label:'Reference',kind:'text'}]},
 'billing-allocations':{title:'Allocate receipt to invoice',permission:'school.billing_allocation.allocate',fields:[relation('receipt_id','Receipt','billing-receipts'),relation('invoice_id','Invoice','billing-invoices'),...common]},
 'billing-credits':{title:'Issue approved credit',permission:'school.billing_credit.issue',fields:[relation('invoice_line_id','Issued fee line','billing-lines'),...common,{name:'reason',label:'Approval reason',kind:'textarea',required:true}]},
 'billing-refunds':{title:'Refund unallocated funds',permission:'school.billing_refund.issue',fields:[relation('receipt_id','Receipt','billing-receipts'),...common,{name:'reason',label:'Approval reason',kind:'textarea',required:true}]},
} satisfies Record<string,{title:string;permission:string;fields:Field[]}>;
export function billingError(e:unknown){return e instanceof ApiClientError?Object.values(e.fieldErrors).flat().join(' ')||e.message:e instanceof Error?e.message:'Financial action failed.';}
