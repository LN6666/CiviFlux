import * as maplibregl from 'maplibre-gl';
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url';
import type {FeatureCollection,Feature} from 'geojson';
import './validation.css';

maplibregl.setWorkerUrl(workerUrl);

type LayerName='context_roads'|'bcc_pushkin_candidates'|'synthetic_baseline'|'synthetic_new_detour'|'ayna_named_street_candidates'|'street_name_agreement'|'active_walk_only'|'active_cycle_only'|'active_walk_cycle'|'pedestrian_areas';
type Route={id:string;delta_distance_m:number;delta_freeflow_time_s:number;origin_snap_gap_m:number;target_snap_gap_m:number};
type ActiveCounts={walk_only_directed_edges:number;cycle_only_directed_edges:number;walk_cycle_directed_edges:number;pedestrian_area_polygons:number;event_restrictions_mapped:boolean};
type Summary={input_candidate_directed_edges:number;unique_new_detour_directed_edges:number;indirect_exact_street_name_agreement_edges:number;proxy_new_detour_edge_name_overlap_pct:number|null;indirect_exact_street_name_agreement_names:string[];synthetic_od_routes:Route[];active_mobility_candidate_layers:ActiveCounts};
type Bundle={schema_version:string;status:string;case_id:string;bbox:[number,number,number,number];summary:Summary;layers:Record<LayerName,FeatureCollection>};
type ActiveMode={exposed_directed_edges:number;exposed_dedicated_nonmotor_edges:number;baseline_reachable_od:number;conditional_reachable_od:number};
type ActiveBundle={schema_version:string;status:string;summary:{multimodal_citypack_sha256:string;buffer_results:{buffer_m:number;modes:{pedestrian:ActiveMode;bicycle:ActiveMode}}[];claim_ceiling:string};layers:Record<string,FeatureCollection>};
const $=<T extends HTMLElement>(selector:string)=>{const value=document.querySelector<T>(selector);if(!value)throw Error(`Missing ${selector}`);return value;};
const summary=$<HTMLDivElement>('#summary');
const activeSummary=$<HTMLDivElement>('#active-summary');
const status=$<HTMLParagraphElement>('#status');
const details=$<HTMLElement>('#details');
const empty:FeatureCollection={type:'FeatureCollection',features:[]};
const map=new maplibregl.Map({container:'map',center:[49.854,40.377],zoom:14,attributionControl:false,style:{version:8,sources:{},layers:[{id:'background',type:'background',paint:{'background-color':'#edf2ee'}}]}});
map.addControl(new maplibregl.NavigationControl(),'bottom-right');
map.addControl(new maplibregl.AttributionControl({compact:false,customAttribution:'© OpenStreetMap contributors · BCC / AYNA announcement overlay'}),'bottom-left');

const specs:[string,LayerName,maplibregl.LayerSpecification][]=[
  ['context','context_roads',{id:'context',type:'line',source:'context',paint:{'line-color':'#bbc9c0','line-width':1.5,'line-opacity':.7}}],
  ['walkArea','pedestrian_areas',{id:'walkArea',type:'fill',source:'walkArea',paint:{'fill-color':'#b08ad6','fill-opacity':.32,'fill-outline-color':'#8f5ac0'}}],
  ['walk','active_walk_only',{id:'walk',type:'line',source:'walk',paint:{'line-color':'#8064bb','line-width':2.5,'line-opacity':.63}}],
  ['cycle','active_cycle_only',{id:'cycle',type:'line',source:'cycle',paint:{'line-color':'#bd4d9b','line-width':3.5,'line-opacity':.82}}],
  ['walkCycle','active_walk_cycle',{id:'walkCycle',type:'line',source:'walkCycle',paint:{'line-color':'#bb73bb','line-width':3,'line-opacity':.8,'line-dasharray':[2,1]}}],
  ['ayna','ayna_named_street_candidates',{id:'ayna',type:'line',source:'ayna',paint:{'line-color':'#168e9c','line-width':4,'line-opacity':.7,'line-dasharray':[2,2]}}],
  ['baseline','synthetic_baseline',{id:'baseline',type:'line',source:'baseline',paint:{'line-color':'#376eb0','line-width':4,'line-opacity':.9,'line-offset':-2,'line-dasharray':[2,2]}}],
  ['detour','synthetic_new_detour',{id:'detour',type:'line',source:'detour',paint:{'line-color':'#e56a24','line-width':6,'line-opacity':.95,'line-offset':3}}],
  ['agreement','street_name_agreement',{id:'agreement',type:'line',source:'agreement',paint:{'line-color':'#19865a','line-width':7,'line-opacity':.95,'line-offset':3}}],
  ['bcc','bcc_pushkin_candidates',{id:'bcc',type:'line',source:'bcc',paint:{'line-color':'#bb333a','line-width':6,'line-opacity':.95,'line-offset':-3}}],
];
const activeSpecs:[string,string,maplibregl.LayerSpecification][]=[
  ['activeWalkBaseline','pedestrian_baseline',{id:'activeWalkBaseline',type:'line',source:'activeWalkBaseline',paint:{'line-color':'#634a9d','line-width':3,'line-opacity':.8,'line-dasharray':[1,2]}}],
  ['activeCycleBaseline','bicycle_baseline',{id:'activeCycleBaseline',type:'line',source:'activeCycleBaseline',paint:{'line-color':'#ad286c','line-width':3,'line-opacity':.8,'line-dasharray':[1,2]}}],
  ['activeWalkExposure','pedestrian_exposed_15m',{id:'activeWalkExposure',type:'line',source:'activeWalkExposure',paint:{'line-color':'#5d2a9c','line-width':6,'line-opacity':.85,'line-offset':-2}}],
  ['activeCycleExposure','bicycle_exposed_15m',{id:'activeCycleExposure',type:'line',source:'activeCycleExposure',paint:{'line-color':'#cf2f7f','line-width':5,'line-opacity':.85,'line-offset':2}}],
];

function validate(value:unknown):Bundle{
  if(!value||typeof value!=='object')throw Error('对照包必须是 JSON 对象');
  const candidate=value as Partial<Bundle>;
  if(candidate.schema_version!=='civiflux-baku-indirect-v2'||candidate.status!=='RETROSPECTIVE_INDIRECT_PLAN_COMPARISON'||candidate.case_id!=='baku-f1-2026-pushkin-indirect')throw Error('巴库对照包版本或类型不匹配');
  if(!Array.isArray(candidate.bbox)||candidate.bbox.length!==4||!candidate.summary?.active_mobility_candidate_layers)throw Error('缺少范围或对照摘要');
  for(const [,key] of specs){const layer=candidate.layers?.[key];if(layer?.type!=='FeatureCollection'||!Array.isArray(layer.features))throw Error(`缺少 ${key} GeoJSON 图层`);}
  return candidate as Bundle;
}

let bundle:Bundle|null=null;
function showActive(value:unknown,base:Bundle){
  if(!value||typeof value!=='object')throw Error('步骑条件探针不是 JSON 对象');
  const next=value as Partial<ActiveBundle>;
  if(next.schema_version!=='civiflux-active-indirect-v1'||next.status!=='HYPOTHETICAL_INDIRECT_STRESS_TEST'||next.summary?.multimodal_citypack_sha256!==(base.summary as Summary&{multimodal_citypack_sha256:string}).multimodal_citypack_sha256)throw Error('步骑探针与地图来源不匹配');
  for(const [name,key] of activeSpecs){const layer=next.layers?.[key];if(layer?.type!=='FeatureCollection'||!Array.isArray(layer.features))throw Error(`缺少 ${key} 条件图层`);(map.getSource(name) as maplibregl.GeoJSONSource).setData(layer);}
  const narrow=next.summary.buffer_results?.find(item=>item.buffer_m===.2);
  const broad=next.summary.buffer_results?.find(item=>item.buffer_m===15);
  if(!narrow||!broad)throw Error('缺少 0.2 m / 15 m 敏感性结果');
  const line=(mode:'pedestrian'|'bicycle',label:string)=>`${label}：0.2 m 缓冲暴露 ${narrow.modes[mode].exposed_directed_edges} 条；15 m 缓冲暴露 ${broad.modes[mode].exposed_directed_edges} 条，其中无机动车权限通道 ${broad.modes[mode].exposed_dedicated_nonmotor_edges} 条。固定 2 组合成 OD 中，基线可达 ${broad.modes[mode].baseline_reachable_od}，假设受限后可达 ${broad.modes[mode].conditional_reachable_od}。`;
  activeSummary.textContent=`步骑间接指标 · 假设敏感性（非现场封闭）\n${line('pedestrian','步行')}\n${line('bicycle','骑行')}\n模型速度假设：步行 1.4 m/s、骑行 4.0 m/s；路线时间不是实测。公告没有给出逐段步骑封闭，地图加粗线仅是 15 m 缓冲范围内的潜在暴露，不是赛事影响判定。`;
  activeSummary.style.whiteSpace='pre-wrap';
}
function fit(){if(bundle)map.fitBounds([[bundle.bbox[0],bundle.bbox[1]],[bundle.bbox[2],bundle.bbox[3]]],{padding:45,duration:0});}
function show(next:Bundle){
  bundle=next;
  for(const [name,key] of specs)(map.getSource(name) as maplibregl.GeoJSONSource).setData(next.layers[key]);
  const s=next.summary;
  const rows=s.synthetic_od_routes.map(r=>`${r.id}: 合成路由 +${r.delta_distance_m.toFixed(1)} m / +${r.delta_freeflow_time_s.toFixed(1)} s`).join('\n');
  const active=s.active_mobility_candidate_layers;
  summary.textContent=`BCC 封路输入候选：${s.input_candidate_directed_edges} 条有向路段\n条件绕行新增：${s.unique_new_detour_directed_edges} 条有向路段\n其中在 AYNA 独立公告街名上：${s.indirect_exact_street_name_agreement_edges} 条\n街名重合比例：${s.proxy_new_detour_edge_name_overlap_pct?.toFixed(1)??'—'}%（${s.indirect_exact_street_name_agreement_edges}/${s.unique_new_detour_directed_edges}；不是实际命中率）\n重合街名：${s.indirect_exact_street_name_agreement_names.join('、')||'无'}\n\n中央范围另有步行专用候选 ${active.walk_only_directed_edges} 条、自行车专用候选 ${active.cycle_only_directed_edges} 条、步骑共用候选 ${active.walk_cycle_directed_edges} 条；显示范围有步行区域候选 ${active.pedestrian_area_polygons} 处。赛事真实步骑限制仍未知，下方仅有明确假设的间接敏感性。\n\n${rows}\n\n上述数字不是实际公交路径或预测准确率。`;
  summary.style.whiteSpace='pre-wrap';
  status.textContent='已载入 BCC 输入与 AYNA 公告的间接 GIS 对照；无赛时实测。';
  status.dataset.error='false';
  fit();
  fetch('/validation/baku-active-indirect.json').then(response=>{if(!response.ok)throw Error('未找到步骑条件探针数据');return response.json();}).then(data=>showActive(data,next)).catch(error=>{activeSummary.textContent=`步骑条件探针不可用：${String(error)}`;});
}

function inspect(feature:Feature):string{
  const p=feature.properties??{};
  const label:Record<string,string>={bcc_input:'BCC 封路输入候选（未人工审阅）',baseline:'无封路合成基线路由',conditional_new_detour:'计算绕行新增路段',ayna_plan_street:'AYNA 公告街名的 OSM 候选（范围未核对）',street_name_agreement:'计算绕行与 AYNA 公告的街名重合',context:'OSM 机动车道路背景',walk_only:'步行专用线性候选（无赛事影响判断）',cycle_only:'自行车专用线性候选（无赛事影响判断）',walk_cycle:'步骑共用线性候选（无赛事影响判断）',pedestrian_area:'OSM 步行区域候选（无赛事影响判断）',pedestrian_hypothetical_exposure:'15 m 假设步行通道暴露（非实际封闭）',bicycle_hypothetical_exposure:'15 m 假设骑行通道暴露（非实际封闭）',pedestrian_baseline:'合成 OD 步行基线路由',bicycle_baseline:'合成 OD 骑行基线路由'};
  return `${label[String(p.layer)]??'道路'}\n${p.name||'未命名'}\n有向路段 ID：${p.id}\nOSM 导入来源：${p.source_id}`;
}

map.on('load',()=>{
  for(const [name,,layer] of specs){map.addSource(name,{type:'geojson',data:empty});map.addLayer(layer);}
  for(const [name,,layer] of activeSpecs){map.addSource(name,{type:'geojson',data:empty});map.addLayer(layer);}
  for(const box of document.querySelectorAll<HTMLInputElement>('input[data-layer]')){
    map.setLayoutProperty(box.dataset.layer!,'visibility',box.checked?'visible':'none');
    box.addEventListener('change',()=>map.setLayoutProperty(box.dataset.layer!,'visibility',box.checked?'visible':'none'));
  }
  const inspectable=['bcc','agreement','detour','baseline','ayna','walk','cycle','walkCycle','walkArea','activeWalkExposure','activeCycleExposure','activeWalkBaseline','activeCycleBaseline'];
  map.on('click',event=>{const features=map.queryRenderedFeatures(event.point,{layers:inspectable});if(features.length)details.textContent=inspect(features[0] as Feature);});
  map.on('mouseenter',inspectable,()=>map.getCanvas().style.cursor='pointer');
  map.on('mouseleave',inspectable,()=>map.getCanvas().style.cursor='');
  fetch('/validation/baku-indirect.json').then(response=>{if(!response.ok)throw Error('未找到巴库对照包，请运行 scripts/baku_indirect_map.py 或选择 JSON 文件。');return response.json();}).then(data=>show(validate(data))).catch(error=>{status.textContent=String(error);status.dataset.error='true';});
});
$<HTMLButtonElement>('#fit').addEventListener('click',fit);
$<HTMLInputElement>('#bundle-file').addEventListener('change',async event=>{const file=(event.target as HTMLInputElement).files?.[0];if(!file)return;try{if(file.size>2*1024*1024)throw Error('对照包超过 2 MiB 上限');show(validate(JSON.parse(await file.text())));}catch(error){status.textContent=String(error);status.dataset.error='true';}});
