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

test('GIS map shows all three measured road comparison outcomes',async({page})=>{
  const verdicts=['hit','miss','false_alarm'];
  const compared=verdicts.map((verdict,index)=>({type:'Feature',geometry:{type:'LineString',coordinates:[[13.38,52.516+index*.001],[13.39,52.516+index*.001]]},properties:{unique_id:`viz-${index}`,verdict,change_class:verdict==='false_alarm'?'no_large_speed_drop':'speed_drop_30pct',predicted_overlap:verdict!=='miss',baseline_speed_kph:40,event_speed_kph:verdict==='false_alarm'?38:20,baseline_closed:0,event_closed:0}}));
  const bundle={
    schema_version:'civiflux-validation-map-v1',event_id:'berlin-marathon-2026',status:'TWO_SNAPSHOT_SPATIAL_COMPARISON',prediction_frozen_at_utc:'2026-09-25T18:20:40Z',
    observation_snapshot:{captured_at_utc:'2026-09-26T04:45:00Z',traffic:{feed_time_stamp:'2026-09-26T04:45:00Z',sha256:'before'}},
    event_snapshot:{traffic:{feed_time_stamp:'2026-09-26T06:30:00Z'}},
    pre_event_coverage:{predicted_edges_with_viz_match:1,predicted_edges_without_viz_match:1,matched_viz_segments:1,scored_matched_viz_segments:1},
    comparison_metrics:{hit:1,miss:1,false_alarm:1,unscored:0,scored_segments:3,predicted_edge_count:2,predicted_edges_with_viz_match:2,matched_viz_segments:2,scored_matched_viz_segments:2,precision:.5,recall:.5},
    counts:{context_roads:0,predicted_route_impact_edges:2,restriction_input_edges:0,traffic_segments:3,marathon_reports:0},
    layers:{context_roads:collection(),predicted_route_impact:collection([road('p1','predicted_route_impact'),road('p2','predicted_route_impact')]),restriction_inputs:collection(),viz_traffic:collection(),viz_marathon_reports:collection(),observed_change:collection(compared)},
    comparison_note:'synthetic browser fixture',
  };
  await page.route('**/validation/berlin-local.json',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(bundle)}));
  await page.goto('/validation.html');
  await expect(page.getByRole('status')).toContainText('两次交通快照');
  await expect(page.locator('#summary')).toContainText('命中 1 · 漏报 1 · 误报 1');
  await expect(page.locator('#summary')).toContainText('赛前可测覆盖：1/2 条插件路段；1 条没有匹配 VIZ 路段');
  await expect(page.getByLabel('Road comparison verdict legend')).toContainText('绿色 命中');
  await expect(page.getByLabel('Road comparison verdict legend')).toContainText('红色 漏报');
  await expect(page.getByLabel('Road comparison verdict legend')).toContainText('紫色 误报');
  await expect(page.locator('canvas.maplibregl-canvas')).toBeVisible();
});
