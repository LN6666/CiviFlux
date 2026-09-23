export class LocalAPI {
  private token='';
  constructor(readonly base='/api/v1'){
    const url=new URL(base,location.origin);
    if(url.origin!==location.origin)throw new Error('The plugin requires a same-origin deployment API.');
  }
  async request<T>(path:string,options:RequestInit={},signal?:AbortSignal):Promise<T>{
    if(!this.token){const session=await fetch(`${this.base}/session`,{signal});if(!session.ok)throw new Error(`Session unavailable (${session.status})`);this.token=(await session.json()).token;}
    const response=await fetch(`${this.base}${path}`,{...options,signal,headers:{'Content-Type':'application/json','Authorization':`Bearer ${this.token}`,...options.headers}});
    if(!response.ok){const text=await response.text();let message=`Request failed (${response.status})`;try{const error=JSON.parse(text);message=typeof error.detail==='string'?error.detail:JSON.stringify(error.detail??error.error??error.message??message);}catch{/* no HTML/error rendering */}throw new Error(message);}
    return response.json() as Promise<T>;
  }
  async download(path:string,filename:string){
    const response=await fetch(`${this.base}${path}`,{headers:{Authorization:`Bearer ${this.token}`}});
    if(!response.ok)throw new Error(`Export failed (${response.status})`);
    const url=URL.createObjectURL(await response.blob());const link=document.createElement('a');link.href=url;link.download=filename;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
}
