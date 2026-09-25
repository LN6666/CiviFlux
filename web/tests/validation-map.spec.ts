import {expect,test} from '@playwright/test';

const collection=(features:unknown[]=[])=>({type:'FeatureCollection',features});
const road=(id:string,layer:string)=>({type:'Feature',geometry:{type:'LineString',coordinates:[[13.38,52.516],[13.39,52.516]]},properties:{id,layer,name:'Unter den Linden',route_labels:['west_to_east']}});

test('GIS validation map separates frozen plugin output from scenario inputs and observations',async({page})=>{
  const bundle={
    schema_version:'civiflux-validation-map-v1',event_id:'berlin-marathon-2026',status:'PRE_EVENT_BASELINE_ONLY',prediction_frozen_at_utc:'2026-09-25T18:20:40Z',
    observation_snapshot:{captured_at_utc:'2026-09-25T18:45:10Z',traffic:{feed_time_stamp:'2026-09-25T18:45:05Z',sha256:'test'}},
    event_snapshot:null,comparison_metrics:null,
    counts:{context_roads:1,predicted_route_impact_edges:1,restriction_input_edges:1,traffic_segments:1,marathon_reports:0},
    layers:{context_roads:collection([road('context','context')]),predicted_route_impact:collection([road('prediction','predicted_route_impact')]),restriction_inputs:collection([road('input','restriction_input')]),viz_traffic:collection([{type:'Feature',geometry:{type:'LineString',coordinates:[[13.38,52.517],[13.39,52.517]]},properties:{unique_id:'viz-1',los:2,speedavg:32,closed:0}}]),viz_marathon_reports:collection(),observed_change:collection()},
    comparison_note:'test fixture',
  };
  await page.route('**/validation/berlin-local.json',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(bundle)}));
  await page.goto('/validation.html');
  await expect(page.getByRole('status')).toContainText('已载入赛前地图');
  await expect(page.locator('#summary')).toContainText('插件影响道路：1 条');
  await expect(page.locator('#summary')).toContainText('输入封路候选：1 条');
  await expect(page.getByLabel('橙色 · 插件预测影响路段')).toBeChecked();
  await page.getByLabel('紫色 · 输入的封路候选').uncheck();
  await expect(page.getByLabel('紫色 · 输入的封路候选')).not.toBeChecked();
  await expect(page.locator('canvas.maplibregl-canvas')).toBeVisible();
});
