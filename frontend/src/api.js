export const API=import.meta.env.VITE_API_URL||'http://localhost:8000'
export const getTok=()=>localStorage.getItem('token')
export const setTok=t=>t?localStorage.setItem('token',t):localStorage.removeItem('token')
/** All calls go through here so the signed-in user's token is always sent. */
export async function api(path,{method='GET',body,form,raw}={}){
  const h={};if(getTok())h.Authorization='Bearer '+getTok();if(body)h['Content-Type']='application/json'
  const r=await fetch(API+path,{method,headers:h,body:form||(body?JSON.stringify(body):undefined)})
  if(r.status===401){setTok(null);window.dispatchEvent(new Event('auth-expired'))}
  if(raw)return r
  const d=await r.json().catch(()=>({}));if(!r.ok)throw new Error(d.detail||'Request failed');return d}
