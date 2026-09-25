import {expect,test} from '@playwright/test';

const collection=(features:unknown[]=[])=>({type:'FeatureCollection',features});
const road=(id:string,layer:string)=>({type:'Feature',geometry:{type:'LineString',coordinates:[[13.38,52.516],[13.39,52.516]]},properties:{id,layer,name:'Unter den Linden',route_labels:['west_to_east']}});

test('GIS validation map separates frozen plugin output from scenario inputs and observations',async({page})=>{
  const bundle={
    schema_version:'civiflux-validation-map-v1',event_id:'berlin-marathon-2026',status:'PRE_EVENT_BASELINE_ONLY',prediction_frozen_at_utc:'2026-09-25T18:20:40Z',
    observation_snapshot:{captured_at_utc:'2026-09-25T18:45:10Z',traffic:{feed_time_stamp:'2026-09-25T18:45:05Z',sha256:'test'}},
    event_snapshot:null,comparison_metrics:null,
    control_plan:{treated_segments:1,treated_segments_with_controls:1,control_segments:1,selection_sha256:'fixed-baseline-test'},
    counts:{context_roads:1,predicted_route_impact_edges:1,restriction_input_edges:1,traffic_segments:1,marathon_reports:0},
    layers:{context_roads:collection([road('context','context')]),predicted_route_impact:collection([road('prediction','predicted_route_impact')]),restriction_inputs:collection([road('input','restriction_input')]),viz_traffic:collection([{type:'Feature',geometry:{type:'LineString',coordinates:[[13.38,52.517],[13.39,52.517]]},properties:{unique_id:'viz-1',los:2,speedavg:32,closed:0}}]),viz_controls:collection([{type:'Feature',geometry:{type:'LineString',coordinates:[[13.4,52.519],[13.41,52.519]]},properties:{unique_id:'control-1',layer:'viz_control',baseline_speed_kph:32,freeflow_speed_kph:45}}]),viz_marathon_reports:collection(),observed_change:collection()},
    comparison_note:'test fixture',
  };
  await page.route('**/validation/berlin-local.json',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(bundle)}));
  await page.goto('/validation.html');
  await expect(page.getByRole('status')).toContainText('已载入赛前地图');
  await expect(page.locator('#summary')).toContainText('插件影响道路：1 条');
  await expect(page.locator('#summary')).toContainText('输入封路候选：1 条');
  await expect(page.locator('#summary')).toContainText('赛前选定对照：1/1 个预测重合 VIZ 路段找到对照；1 条独立对照路段');
  await expect(page.locator('input[data-layer="predicted"]')).toBeChecked();
  await expect(page.locator('fieldset')).toContainText('深橙 / 浅橙 · 插件预测路段有 / 无赛前 VIZ 空间覆盖');
  await page.getByLabel('深蓝虚线 · 仅据赛前信息匹配的对照路段').uncheck();
  await expect(page.getByLabel('深蓝虚线 · 仅据赛前信息匹配的对照路段')).not.toBeChecked();
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
    control_plan:{treated_segments:1,treated_segments_with_controls:1,control_segments:2,selection_sha256:'before-only'},
    control_indicator:{valid_treated_control_groups:1,median_pair_adjusted_speed_drop_fraction:.4,newly_reported_closed_treated:0,newly_reported_closed_controls:0},
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
  await expect(page.locator('#summary')).toContainText('额外降速中位数：40.0 个百分点（描述性间接指标）');
  await expect(page.getByLabel('Road comparison verdict legend')).toContainText('绿色 命中');
  await expect(page.getByLabel('Road comparison verdict legend')).toContainText('红色 漏报');
  await expect(page.getByLabel('Road comparison verdict legend')).toContainText('紫色 误报');
  await expect(page.locator('canvas.maplibregl-canvas')).toBeVisible();
});

test('pre-onset placebo map labels background changes without event hit rate',async({page})=>{
  const bundle={
    schema_version:'civiflux-validation-map-v1',event_id:'berlin-marathon-2026',status:'PRE_ONSET_PLACEBO',prediction_frozen_at_utc:'2026-09-25T18:20:40Z',
    observation_snapshot:{captured_at_utc:'2026-09-25T18:45:10Z',traffic:{feed_time_stamp:'2026-09-25T18:45:05Z',sha256:'before'}},
    event_snapshot:null,comparison_metrics:null,placebo_snapshot:{traffic:{feed_time_stamp:'2026-09-25T21:03:35Z'}},
    placebo_metrics:{scored_segments:3,overlap_with_background_change:1,nearby_background_change_without_overlap:1,overlap_without_large_change:1,unscored:0},
    counts:{context_roads:0,predicted_route_impact_edges:1,restriction_input_edges:0,traffic_segments:3,marathon_reports:0},
    layers:{context_roads:collection(),predicted_route_impact:collection([road('p1','predicted_route_impact')]),restriction_inputs:collection(),viz_traffic:collection(),viz_controls:collection(),viz_marathon_reports:collection(),observed_change:collection()},
    comparison_note:'two feeds before onset',
  };
  await page.route('**/validation/berlin-placebo-local.json',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(bundle)}));
  await page.goto('/validation.html?bundle=placebo');
  await expect(page.getByRole('status')).toContainText('赛前快照的安慰剂地图');
  await expect(page.locator('#summary')).toContainText('背景变化与预测重合 1');
  await expect(page.locator('#summary')).not.toContainText('精确率');
  await expect(page.getByLabel('Road comparison verdict legend')).toContainText('赛前变化与预测重合');
  await expect(page.getByLabel('Road comparison verdict legend')).not.toContainText('绿色 命中');
  await expect(page.locator('#interpretation')).toContainText('这些颜色不是赛事命中');
});

test('notice geometry audit colors candidate roads without claiming observed impacts',async({page})=>{
  const inputs=[
    {...road('supported','restriction_input'),properties:{id:'supported',layer:'restriction_input',name:'Straße des 17. Juni',viz_mapping_status:'SPATIAL_SUPPORT_DIRECTION_UNRESOLVED',viz_nearest_gap_m:4,viz_maximum_overlap_m:40,viz_required_overlap_m:25}},
    {...road('unsupported','restriction_input'),properties:{id:'unsupported',layer:'restriction_input',name:'Straße des 17. Juni',viz_mapping_status:'NO_SUFFICIENT_SPATIAL_OVERLAP',viz_nearest_gap_m:140,viz_maximum_overlap_m:0,viz_required_overlap_m:25}},
    {...road('no-report','restriction_input'),properties:{id:'no-report',layer:'restriction_input',name:'Unter den Linden',viz_mapping_status:'NO_NAMED_REPORT_IN_SNAPSHOT',viz_nearest_gap_m:null,viz_maximum_overlap_m:0,viz_required_overlap_m:25}},
  ];
  const bundle={
    schema_version:'civiflux-validation-map-v1',event_id:'berlin-marathon-2026',status:'PRE_EVENT_BASELINE_ONLY',prediction_frozen_at_utc:'2026-09-25T18:20:40Z',
    observation_snapshot:{captured_at_utc:'2026-09-25T18:45:10Z',traffic:{feed_time_stamp:'2026-09-25T18:45:05Z',sha256:'traffic'},reports:{sha256:'reports'}},
    event_snapshot:null,comparison_metrics:null,
    mapping_audit:{status:'CANDIDATE_SPATIAL_AUDIT_ONLY',viz_reports_sha256:'reports',cases:[{case_id:'active',candidate_directed_edges:2,sufficient_overlap:1,without_sufficient_overlap:1,same_street_viz_reports:2,direction_verified:0},{case_id:'upcoming',candidate_directed_edges:1,sufficient_overlap:0,without_sufficient_overlap:1,same_street_viz_reports:0,direction_verified:0}]},
    counts:{context_roads:0,predicted_route_impact_edges:0,restriction_input_edges:3,traffic_segments:0,marathon_reports:2},
    layers:{context_roads:collection(),predicted_route_impact:collection(),restriction_inputs:collection(inputs),viz_traffic:collection(),viz_controls:collection(),viz_marathon_reports:collection(),observed_change:collection()},
    comparison_note:'notice geometry only',
  };
  await page.route('**/validation/berlin-mapping-review-local.json',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(bundle)}));
  await page.goto('/validation.html?bundle=mapping');
  await expect(page.getByRole('status')).toContainText('不是现场封路或扰动验证');
  await expect(page.locator('#summary')).toContainText('空间重合支持 1/2 条候选有向边');
  await expect(page.locator('#summary')).toContainText('同名 VIZ 通报 0 条；空间重合支持 0/1');
  await expect(page.locator('#restriction-label')).toContainText('红色 重合不足 / 灰色 无同名通报');
  await expect(page.getByLabel('Road comparison verdict legend')).toBeHidden();
  await expect(page.locator('#interpretation')).toContainText('既不能证明现场执行，也不能核验有向边方向');
  await expect(page.locator('canvas.maplibregl-canvas')).toBeVisible();
});
