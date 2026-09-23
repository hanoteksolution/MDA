import { create } from 'zustand';
import { useEffect } from 'react';
import { sisApi } from './api';
import { resources } from './config';
interface State { codes: string[]; loading: boolean; loaded: boolean; error: string; load: () => Promise<void> }
export const useSisStore = create<State>((set) => ({codes:[],loading:false,loaded:false,error:'',load: async () => {
 set({loading:true,error:''});try {set({codes:(await sisApi.capabilities()).data});} catch(e) {set({codes:[],error:e instanceof Error ? e.message:'Permissions could not load.'});} finally {set({loading:false,loaded:true});}
}}));
export function useSisPermissions() {
 const state = useSisStore();
 useEffect(() => { void state.load(); }, [state.load]);
 return {...state, can:(resource: string, action: string) => state.codes.includes(`school.${resources[resource]?.permission || resource}.${action}`)};
}
