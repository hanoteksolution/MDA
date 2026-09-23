import type { Field, Values } from './api';
export function payload(fields: Field[], values: Values): Values {
 return Object.fromEntries(fields.map(f => {
  const value = values[f.name] ?? f.default ?? (f.kind === 'checkbox' ? false : '');
  return [f.name, value === '' && f.nullable ? null : value];
 }));
}
