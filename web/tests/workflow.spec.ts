import {test,expect,type Page} from '@playwright/test';

async function ready(page:Page,path='/'){
  await page.goto(path);
  await expect(page.getByRole('status')).toContainText('Ready');
  await expect(page.getByLabel('Citypack',{exact:true})).toHaveValue('TOY-DUAL-CORRIDOR');
}
async function run(page:Page){
  await page.getByLabel('Confirm scenario assumptions',{exact:true}).check();
  await page.getByRole('button',{name:'Validate & run'}).click();
  await expect(page.getByRole('status')).toContainText('Complete',{timeout:25000});
  await expect(page.getByRole('table',{name:'Baseline and event routing'})).toBeVisible();
}
for(const [host,path] of [['map','/'],['vanilla','/headless.html']] as const){
  test(`${host} host executes actual backend, object view and reproducible export`,async({page})=>{
    const external:string[]=[];
    await page.route('**/*',route=>{if(new URL(route.request().url()).origin!=='http://127.0.0.1:8766'){external.push(route.request().url());return route.abort();}return route.continue();});
    await ready(page,path);
    await expect(page.getByRole('button',{name:'Validate & run'})).toBeDisabled();
    if(host==='map'){await expect(page.locator('canvas.maplibregl-canvas')).toBeVisible();await expect.poll(()=>page.evaluate(()=>{const panel=document.querySelector('urban-impact-panel') as unknown as {mapAdapter:{map:{queryRenderedFeatures:()=>unknown[]}}};return panel.mapAdapter.map.queryRenderedFeatures().length;})).toBeGreaterThan(0);}
    await run(page);
    await expect(page.getByRole('table',{name:'Baseline and event routing'})).toContainText('unreachable');
    await page.getByRole('button',{name:'hospital',exact:true}).click();
    await expect(page.getByText('Object view / 对象详情')).toBeVisible();
    await expect(page.locator('urban-impact-panel')).toContainText('Synthetic hospital');
    await page.getByRole('tab',{name:'Attention'}).click();
    await expect(page.getByRole('table',{name:'Graph attention scores'})).toContainText('hospital');
    const downloadPromise=page.waitForEvent('download');await page.getByRole('button',{name:'Export ZIP'}).click();
    const download=await downloadPromise;expect(download.suggestedFilename()).toMatch(/^run-.*\.zip$/);
    await download.saveAs(`test-results/${host}-result.zip`);
    await page.getByRole('tab',{name:'Evidence'}).click();
    await expect(page.getByText('No independent measured traffic validation.',{exact:true})).toBeVisible();
    await page.evaluate(()=>window.scrollTo(0,0));
    await page.screenshot({path:`test-results/${host}-workspace.png`,fullPage:true});
    expect(external).toEqual([]);
  });
}

test('fire requires explicit polygon and assumption before a real run',async({page})=>{
  await ready(page,'/headless.html');
  await page.getByLabel('Event type',{exact:true}).selectOption('fire');
  await page.getByLabel('Confirm scenario assumptions',{exact:true}).check();
  await page.getByRole('button',{name:'Validate & run'}).click();
  await expect(page.getByRole('alert')).toContainText('Draw or import a fire perimeter');
  await page.getByText('Perimeter GeoJSON',{exact:true}).click();
  await page.getByLabel('Perimeter GeoJSON',{exact:true}).fill(JSON.stringify({type:'Polygon',coordinates:[[[24.941,60.169],[24.949,60.169],[24.949,60.171],[24.941,60.171],[24.941,60.169]]]}));
  await page.getByRole('button',{name:'Apply perimeter'}).click();
  await run(page);
  await page.getByRole('tab',{name:'Evidence'}).click();
  await expect(page.locator('urban-impact-panel')).toContainText('not a measured hazard boundary');
});

test('Qwen API unavailable is distinct from computed results and never falls back',async({page})=>{
  await ready(page,'/headless.html');
  await page.getByLabel('Analysis mode',{exact:true}).selectOption('A3');
  await page.getByLabel('Confirm scenario assumptions',{exact:true}).check();
  await page.getByRole('button',{name:'Validate & run'}).click();
  await expect(page.getByRole('alert')).toContainText('Qwen API');
  await expect(page.getByRole('table',{name:'Baseline and event routing'})).toHaveCount(0);
});

test('invalid time window is rejected before committing an action',async({page})=>{
  await ready(page,'/headless.html');
  await page.getByLabel('End time UTC',{exact:true}).fill('2026-05-15T00:00');
  await page.getByLabel('Confirm scenario assumptions',{exact:true}).check();
  await page.getByRole('button',{name:'Validate & run'}).click();
  await expect(page.getByRole('alert')).toBeVisible();
  await expect(page.getByRole('table',{name:'Baseline and event routing'})).toHaveCount(0);
});

test('map selection opens baseline object and routing vehicle is independent of blocked class',async({page})=>{
  await ready(page);
  await expect.poll(()=>page.evaluate(()=>{const panel=document.querySelector('urban-impact-panel') as unknown as {mapAdapter:{map:{queryRenderedFeatures:()=>unknown[]}}};return panel.mapAdapter.map.queryRenderedFeatures().length;})).toBeGreaterThan(0);
  const point=await page.evaluate(()=>{const panel=document.querySelector('urban-impact-panel') as unknown as {mapAdapter:{map:{project:(p:number[])=>{x:number;y:number}}}};const p=panel.mapAdapter.map.project([24.96,60.17]);return{x:p.x,y:p.y};});
  await page.locator('canvas.maplibregl-canvas').click({position:point});
  await expect(page.locator('urban-impact-panel')).toContainText('Synthetic hospital');
  await expect(page.getByRole('alert')).toHaveCount(0);
  await page.getByLabel('Analysis vehicle',{exact:true}).selectOption('bus');
  await run(page);
  const table=page.getByRole('table',{name:'Baseline and event routing'});
  await expect(table).not.toContainText('unreachable');
  await expect(table.getByRole('button',{name:'Event route',exact:true})).toBeVisible();
});
