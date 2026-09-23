import { describe, expect, it } from 'vitest';
import { attendancePayload, markAll, slotReady, tally, timetableGrid, toMarks, unmarked } from './academics';
import { commands } from './workflows';
import { resources } from './config';

const students = [{student_id:'a',student_name:'Amina',roll_number:'1',status:null,remarks:''},{student_id:'b',student_name:'Bilal',roll_number:'2',status:'absent',remarks:'sick'}];

describe('attendance marking', () => {
 it('starts unmarked and counts progress', () => {
  const marks = toMarks(students);
  expect(unmarked(marks)).toBe(1);
  expect(unmarked(markAll(marks, 'present'))).toBe(0);
  expect(tally(marks)).toMatchObject({present:0, absent:1});
 });
 it('sends only marked students, drops period fields for daily and never sends the campus', () => {
  const data = attendancePayload({branch_id:'c',school_class_id:'k',section_id:'',date:'2026-09-21',mode:'daily',period_id:'p'}, toMarks(students), false);
  expect(data).toEqual({school_class_id:'k',date:'2026-09-21',mode:'daily',records:[{student_id:'b',status:'absent',remarks:'sick'}],submit:false});
  expect(attendancePayload({mode:'period',period_id:'p'}, [], true)).toMatchObject({period_id:'p',submit:true});
 });
 it('requires a period for period attendance', () => {
  expect(slotReady({school_class_id:'k',date:'d',mode:'daily'})).toBe(true);
  expect(slotReady({school_class_id:'k',date:'d',mode:'period'})).toBe(false);
  expect(slotReady({date:'d',mode:'daily'})).toBe(false);
 });
});

describe('timetable grid', () => {
 it('orders periods by clock time and places lessons in their slot', () => {
  const periods = [{id:'p2',name:'P2',start_time:'09:00'},{id:'p1',name:'P1',start_time:'08:00'}] as never[];
  const entries = [{id:'e',weekday:2,period_id:'p2'},{id:'f',weekday:2,period_id:'p2'}] as never[];
  const grid = timetableGrid(periods, entries);
  expect(grid.map(r => r.period.id)).toEqual(['p1','p2']);
  expect(grid[1].cells[1].entries).toHaveLength(2);
  expect(grid[0].cells.every(c => c.entries.length === 0)).toBe(true);
 });
});

describe('phase 4 commands and catalog', () => {
 const row = (status: string) => ({id:'1',name:'x',status});
 it('offers publish only for drafts and approval only while pending', () => {
  expect(commands('timetable-versions', row('draft')).map(c => c.action)).toEqual(['publish','clone']);
  expect(commands('timetable-versions', row('published')).map(c => c.action)).toEqual(['clone']);
  expect(commands('timetable-versions', row('archived'))).toEqual([]);
  expect(commands('attendance-corrections', row('pending')).map(c => c.action)).toEqual(['approve','reject']);
  expect(commands('attendance-corrections', row('approved'))).toEqual([]);
  expect(commands('attendance-sessions', row('submitted'))).toEqual([]);
 });
 it('rejection needs a note and corrections need a reason', () => {
  expect(commands('attendance-corrections', row('pending'))[1].fields[0].required).toBe(true);
  expect(commands('attendance-records', row('present'))[0].fields.every(f => f.required)).toBe(true);
 });
 it('keeps historical attendance resources read-only', () => {
  for (const key of ['attendance-sessions','attendance-records','attendance-corrections']) expect(resources[key].readonly).toBe(true);
 });
});
