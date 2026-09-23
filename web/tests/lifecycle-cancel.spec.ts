import {test,expect,type APIRequestContext,type Page} from '@playwright/test';

const cancelHost='http://127.0.0.1:8767';

async function ready(page:Page,path:string){
  await page.goto(path);
  await expect(page.getByRole('status')).toContainText('Ready');
  await expect(page.getByLabel('Citypack',{exact:true})).toHaveValue('TOY-DUAL-CORRIDOR');
}

async function jobState(request:APIRequestContext,runId:string){
  const session=await request.get(`${cancelHost}/api/v1/session`);
  const {token}=await session.json() as {token:string};
  const headers={Authorization:`Bearer ${token}`};
  return {headers,get:()=>request.get(`${cancelHost}/api/v1/runs/${runId}`,{headers})};
}

test('vanilla component releases subscriptions and aborts in-flight requests across repeated mounts',async({page})=>{
  await ready(page,'/headless.html');
  await page.evaluate(()=>{
    const globals=window as typeof window & {__panel?:Element;__adapter?:unknown;__signals?:AbortSignal[];__errors?:number};
    const panel=document.querySelector('urban-impact-panel')!;
    globals.__panel=panel;
    globals.__adapter=(panel as typeof panel & {mapAdapter:unknown}).mapAdapter;
    globals.__signals=[];
    globals.__errors=0;
    panel.addEventListener('error',()=>globals.__errors!++);
    const originalFetch=window.fetch.bind(window);
    window.fetch=(input,init)=>{
      if(String(input).includes('/api/v1/citypacks')&&init?.signal)globals.__signals!.push(init.signal);
      return originalFetch(input,init);
    };
  });
  for(let cycle=0;cycle<5;cycle++){
    const afterRemove=await page.evaluate(()=>{
      const globals=window as typeof window & {__panel:Element;__adapter:{callbacks:Set<unknown>};__signals:AbortSignal[]};
      globals.__panel.remove();
      return {subscriptions:globals.__adapter.callbacks.size,allAborted:globals.__signals.every(signal=>signal.aborted)};
    });
    expect(afterRemove).toEqual({subscriptions:0,allAborted:true});
    await page.evaluate(()=>{
      const globals=window as typeof window & {__panel:Element};
      document.querySelector('main')!.append(globals.__panel);
    });
    await expect(page.getByRole('status')).toContainText('Ready');
    expect(await page.evaluate(()=>((window as typeof window & {__adapter:{callbacks:Set<unknown>}}).__adapter.callbacks.size))).toBe(1);
  }
  let releaseRoute:()=>void=()=>{};
  let intercepted:()=>void=()=>{};
  const requestIntercepted=new Promise<void>(resolve=>intercepted=resolve);
  const routeReleased=new Promise<void>(resolve=>releaseRoute=resolve);
  await page.route('**/api/v1/citypacks',async route=>{
    intercepted();
    await routeReleased;
    await route.continue().catch(()=>{});
  });
  try{
    await page.evaluate(()=>{
      const globals=window as typeof window & {__panel:Element};
      globals.__panel.remove();document.querySelector('main')!.append(globals.__panel);
    });
    await requestIntercepted;
    const held=await page.evaluate(()=>{
      const globals=window as typeof window & {__panel:Element;__signals:AbortSignal[]};
      const signal=globals.__signals.at(-1)!;
      const pendingBeforeRemoval=!signal.aborted;
      globals.__panel.remove();
      return {pendingBeforeRemoval,abortedAfterRemoval:signal.aborted};
    });
    expect(held).toEqual({pendingBeforeRemoval:true,abortedAfterRemoval:true});
  }finally{
    releaseRoute();await page.unroute('**/api/v1/citypacks');
  }
  await page.evaluate(()=>{
    const globals=window as typeof window & {__panel:Element};
    document.querySelector('main')!.append(globals.__panel);
  });
  await expect(page.getByRole('status')).toContainText('Ready');
  expect(await page.evaluate(()=>(window as typeof window & {__errors:number}).__errors)).toBe(0);
});

test('MapLibre host disposes real map instances while remounting the same component',async({page})=>{
  await ready(page,'/');
  await expect(page.locator('canvas.maplibregl-canvas')).toHaveCount(1);
  for(let cycle=0;cycle<3;cycle++){
    const cleanup=await page.evaluate(()=>{
      const panel=document.querySelector('urban-impact-panel') as HTMLElement & {mapAdapter:any};
      const old=panel.mapAdapter;
      const MapAdapter=old.constructor;
      const canvas=old.map.getCanvas() as HTMLCanvasElement;
      panel.remove();
      const subscriptions=old.listeners.size as number;
      old.dispose();old.dispose();
      const canvasStillAttached=canvas.isConnected;
      panel.mapAdapter=new MapAdapter(document.querySelector('#map')!);
      document.querySelector('.workspace')!.prepend(panel);
      return {subscriptions,canvasStillAttached};
    });
    expect(cleanup).toEqual({subscriptions:0,canvasStillAttached:false});
    await expect(page.getByRole('status')).toContainText('Ready');
    await expect(page.locator('canvas.maplibregl-canvas')).toHaveCount(1);
    expect(await page.evaluate(()=>{
      const panel=document.querySelector('urban-impact-panel') as unknown as HTMLElement & {mapAdapter:{listeners:Set<unknown>}};
      return panel.mapAdapter.listeners.size;
    })).toBe(1);
  }
});

test('unmounting during a real active job clears poll timer and stops browser requests',async({page,request})=>{
  await request.post(`${cancelHost}/__browser_test__/reset`);
  await ready(page,`${cancelHost}/headless.html`);
  await page.evaluate(()=>{
    const globals=window as typeof window & {__polls?:number;__cleared?:number[]};
    globals.__polls=0;globals.__cleared=[];
    const originalFetch=window.fetch.bind(window);
    window.fetch=(input,init)=>{
      if(/\/api\/v1\/runs\/run-[^/]+$/.test(String(input)))globals.__polls!++;
      return originalFetch(input,init);
    };
    const originalClear=window.clearTimeout.bind(window);
    window.clearTimeout=((id:number)=>{globals.__cleared!.push(id);originalClear(id);}) as typeof window.clearTimeout;
  });
  const created=page.waitForResponse(response=>response.request().method()==='POST'&&response.url().endsWith('/api/v1/runs'));
  await page.getByLabel('Confirm scenario assumptions',{exact:true}).check();
  await page.getByRole('button',{name:'Validate & run'}).click();
  const runId=(await (await created).json() as {run_id:string}).run_id;
  await expect.poll(async()=>((await (await request.get(`${cancelHost}/__browser_test__/state`)).json()) as {started:boolean}).started).toBe(true);
  await expect.poll(()=>page.evaluate(()=>{
    const panel=document.querySelector('urban-impact-panel') as unknown as HTMLElement & {pollTimer?:number};
    return panel.pollTimer;
  })).toBeGreaterThan(0);
  const afterDetach=await page.evaluate(()=>{
    const panel=document.querySelector('urban-impact-panel') as unknown as HTMLElement & {pollTimer?:number;lifetime:{signal:AbortSignal};mapAdapter:{callbacks:Set<unknown>}};
    const timer=panel.pollTimer!;
    (window as typeof window & {__panel?:HTMLElement}).__panel=panel;
    panel.remove();
    const globals=window as typeof window & {__polls:number;__cleared:number[]};
    return {timerCleared:globals.__cleared.includes(timer),aborted:panel.lifetime.signal.aborted,subscriptions:panel.mapAdapter.callbacks.size,polls:globals.__polls};
  });
  expect(afterDetach.timerCleared).toBe(true);
  expect(afterDetach.aborted).toBe(true);
  expect(afterDetach.subscriptions).toBe(0);
  try{
    await page.waitForTimeout(750);
    expect(await page.evaluate(()=>(window as typeof window & {__polls:number}).__polls)).toBe(afterDetach.polls);
    const state=await jobState(request,runId);
    expect((await request.post(`${cancelHost}/api/v1/runs/${runId}/cancel`,{headers:state.headers})).ok()).toBe(true);
  }finally{
    await request.post(`${cancelHost}/__browser_test__/release`);
  }
  const state=await jobState(request,runId);
  await expect.poll(async()=>((await (await state.get()).json()) as {status:string}).status).toBe('cancelled');
  await page.evaluate(()=>document.querySelector('main')!.append((window as typeof window & {__panel:HTMLElement}).__panel));
  await expect(page.getByRole('status')).toContainText('Ready');
  await expect(page.getByRole('button',{name:'Validate & run'})).toBeVisible();
});

test('Cancel in the browser reaches terminal cancelled state with no completed result',async({page,request})=>{
  await request.post(`${cancelHost}/__browser_test__/reset`);
  const external:string[]=[];
  await page.route('**/*',route=>{
    if(new URL(route.request().url()).origin!==cancelHost){external.push(route.request().url());return route.abort();}
    return route.continue();
  });
  await ready(page,`${cancelHost}/headless.html`);
  await page.evaluate(()=>{
    const globals=window as typeof window & {__completed?:number};globals.__completed=0;
    document.querySelector('urban-impact-panel')!.addEventListener('run-complete',()=>globals.__completed!++);
  });
  const resultRequests:string[]=[];
  page.on('request',request=>{if(/\/api\/v1\/runs\/run-[^/]+\/results$/.test(request.url()))resultRequests.push(request.url());});
  const created=page.waitForResponse(response=>response.request().method()==='POST'&&response.url().endsWith('/api/v1/runs'));
  await page.getByLabel('Confirm scenario assumptions',{exact:true}).check();
  await page.getByRole('button',{name:'Validate & run'}).click();
  const runId=(await (await created).json() as {run_id:string}).run_id;
  await expect.poll(async()=>((await (await request.get(`${cancelHost}/__browser_test__/state`)).json()) as {started:boolean}).started).toBe(true);
  await expect(page.getByRole('button',{name:'Cancel 取消'})).toBeVisible();
  try{
    const cancellation=page.waitForResponse(response=>response.request().method()==='POST'&&response.url().endsWith(`/api/v1/runs/${runId}/cancel`));
    await page.getByRole('button',{name:'Cancel 取消'}).click();
    const accepted=await cancellation;
    expect(accepted.status()).toBe(200);
    expect((await accepted.json() as {stage:string}).stage).toBe('cancelling');
  }finally{
    await request.post(`${cancelHost}/__browser_test__/release`);
  }
  await expect(page.getByRole('status')).toContainText('Cancelled · no completed result');
  const state=await jobState(request,runId);
  await expect.poll(async()=>((await (await state.get()).json()) as {status:string}).status).toBe('cancelled');
  const results=await request.get(`${cancelHost}/api/v1/runs/${runId}/results`,{headers:state.headers});
  expect(results.status()).toBe(409);
  await expect(page.getByRole('table',{name:'Baseline and event routing'})).toHaveCount(0);
  await expect(page.getByRole('button',{name:'Export ZIP'})).toHaveCount(0);
  expect(await page.evaluate(()=>(window as typeof window & {__completed:number}).__completed)).toBe(0);
  expect(resultRequests).toEqual([]);
  expect(external).toEqual([]);
});
