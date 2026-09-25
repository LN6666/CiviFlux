import {expect,test} from '@playwright/test';

const line=(id:string,layer:string,name:string)=>({
  type:'Feature',
  geometry:{type:'LineString',coordinates:[[49.853,40.375],[49.856,40.375]]},
  properties:{id,layer,name,source_id:'fixture'},
});
const collection=(...features:unknown[])=>({type:'FeatureCollection',features});

test('Baku map keeps the closure input, computed detour, and announcement separate',async({page})=>{
  const bundle={
    schema_version:'civiflux-baku-indirect-v1',
    status:'RETROSPECTIVE_INDIRECT_PLAN_COMPARISON',
    case_id:'baku-f1-2026-pushkin-indirect',
    bbox:[49.85,40.37,49.86,40.38],
    summary:{
      input_candidate_directed_edges:1,
      unique_new_detour_directed_edges:1,
      indirect_exact_street_name_agreement_edges:1,
      proxy_new_detour_edge_name_overlap_pct:100,
      indirect_exact_street_name_agreement_names:['28 May küçəsi'],
      synthetic_od_routes:[{id:'synthetic-one',delta_distance_m:100,delta_freeflow_time_s:10,origin_snap_gap_m:0,target_snap_gap_m:0}],
    },
    layers:{
      context_roads:collection(),
      bcc_pushkin_candidates:collection(line('closure','bcc_input','Puşkin küçəsi')),
      synthetic_baseline:collection(line('baseline','baseline','Puşkin küçəsi')),
      synthetic_new_detour:collection(line('detour','conditional_new_detour','28 May küçəsi')),
      ayna_named_street_candidates:collection(line('announcement','ayna_plan_street','28 May küçəsi')),
      street_name_agreement:collection(line('agreement','street_name_agreement','28 May küçəsi')),
    },
  };
  await page.route('**/validation/baku-indirect.json',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(bundle)}));
  await page.goto('/baku-indirect.html');
  await expect(page.getByRole('status')).toContainText('间接 GIS 对照');
  await expect(page.locator('#summary')).toContainText('BCC 封路输入候选：1 条');
  await expect(page.locator('#summary')).toContainText('其中在 AYNA 独立公告街名上：1 条');
  await expect(page.locator('#summary')).toContainText('街名重合比例：100.0%（1/1；不是实际命中率）');
  await expect(page.locator('#summary')).toContainText('不是实际公交路径或预测准确率');
  await expect(page.getByLabel('红色 · BCC 普希金街封路输入候选')).toBeChecked();
  await page.getByLabel('青色虚线 · AYNA 改线公告街名候选').uncheck();
  await expect(page.getByLabel('青色虚线 · AYNA 改线公告街名候选')).not.toBeChecked();
  await expect(page.locator('canvas.maplibregl-canvas')).toBeVisible();
});
