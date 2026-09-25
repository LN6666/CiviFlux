import * as maplibregl from 'maplibre-gl';
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url';
import type {FeatureCollection,Feature,LineString,Position} from 'geojson';
import './validation.css';

maplibregl.setWorkerUrl(workerUrl);

type LayerName='context_roads'|'predicted_route_impact'|'restriction_inputs'|'viz_traffic'|'viz_controls'|'viz_marathon_reports'|'observed_change';
type Metrics={hit:number;miss:number;false_alarm:number;unscored:number;scored_segments:number;predicted_edge_count:number;predicted_edges_with_viz_match:number;matched_viz_segments:number;scored_matched_viz_segments:number;precision:number|null;recall:number|null};
type Coverage={predicted_edges_with_viz_match:number;predicted_edges_without_viz_match:number;matched_viz_segments:number;scored_matched_viz_segments:number};
type ControlPlan={treated_segments:number;treated_segments_with_controls:number;control_segments:number;selection_sha256:string};
type ControlIndicator={valid_treated_control_groups:number;median_pair_adjusted_speed_drop_fraction:number|null;newly_reported_closed_treated:number;newly_reported_closed_controls:number};
type Bundle={schema_version:string;event_id:string;status:string;prediction_frozen_at_utc:string;observation_snapshot:{captured_at_utc:string;traffic:{feed_time_stamp:string;sha256:string}};event_snapshot:{traffic:{feed_time_stamp:string}}|null;comparison_metrics:Metrics|null;pre_event_coverage?:Coverage;control_plan?:ControlPlan;control_indicator?:ControlIndicator|null;counts:Record<string,number>;layers:Record<LayerName,FeatureCollection>;comparison_note:string};

const empty:FeatureCollection={type:'FeatureCollection',features:[]};
const $=<T extends HTMLElement>(selector:string)=>{const element=document.querySelector<T>(selector);if(!element)throw Error(`Missing ${selector}`);return element;};
const status=$<HTMLParagraphElement>('#status');
const summary=$<HTMLDivElement>('#summary');
const details=$<HTMLElement>('#details');
let bundle:Bundle|null=null;
const map=new maplibregl.Map({container:'map',center:[13.381,52.518],zoom:12,attributionControl:false,style:{version:8,sources:{},layers:[{id:'background',type:'background',paint:{'background-color':'#edf2ee'}}]}});
map.addControl(new maplibregl.NavigationControl(),'bottom-right');
map.addControl(new maplibregl.AttributionControl({compact:false,customAttribution:'© OpenStreetMap contributors · Berlin VIZ / VMZ Berlin / HERE'}),'bottom-left');

const specs:[string,LayerName,maplibregl.LayerSpecification][]=[
  ['context','context_roads',{id:'context',type:'line',source:'context',paint:{'line-color':'#bac6c0','line-width':1.4,'line-opacity':.65}}],
  ['traffic','viz_traffic',{id:'traffic',type:'line',source:'traffic',paint:{'line-color':['match',['get','los'],1,'#1a9c79',2,'#74a67d',3,'#ecab42',7,'#53616c','#93a49b'],'line-width':3,'line-opacity':.72}}],
  ['controls','viz_controls',{id:'controls',type:'line',source:'controls',paint:{'line-color':'#184d90','line-width':5,'line-offset':-7,'line-dasharray':[3,2]}}],
  ['changes','observed_change',{id:'changes',type:'line',source:'changes',filter:['in',['get','verdict'],['literal',['hit','miss','false_alarm']]],paint:{'line-color':['match',['get','verdict'],'hit','#16855a','miss','#c6353e','false_alarm','#9a4ab4','#65776c'],'line-width':6,'line-opacity':.9}}],
  ['reports','viz_marathon_reports',{id:'reports',type:'line',source:'reports',filter:['==',['geometry-type'],'LineString'],paint:{'line-color':'#3474ad','line-width':5,'line-offset':-3,'line-dasharray':[2,2]}}],
  ['predicted','predicted_route_impact',{id:'predicted',type:'line',source:'predicted',paint:{'line-color':['case',['==',['get','viz_baseline_coverage'],false],'#e9aa81','#e56a24'],'line-width':5,'line-offset':4}}],
  ['closures','restriction_inputs',{id:'closures',type:'line',source:'closures',paint:{'line-color':'#8b55aa','line-width':4,'line-offset':-4,'line-dasharray':[2,2]}}],
];

function validate(value:unknown):Bundle{
  if(!value||typeof value!=='object')throw Error('验证包必须是 JSON 对象');
  const candidate=value as Partial<Bundle>;
  if(candidate.schema_version!=='civiflux-validation-map-v1'||candidate.event_id!=='berlin-marathon-2026')throw Error('验证包版本或赛事 ID 不匹配');
  if(candidate.layers&&!candidate.layers.viz_controls)candidate.layers.viz_controls=empty;
  for(const [,key] of specs){const layer=candidate.layers?.[key];if(layer?.type!=='FeatureCollection'||!Array.isArray(layer.features))throw Error(`缺少 ${key} GeoJSON 图层`);}
  return candidate as Bundle;
}

function sourceData(name:string,data:FeatureCollection){(map.getSource(name) as maplibregl.GeoJSONSource).setData(data);}
function setBundle(next:Bundle){
  bundle=next;
  for(const [name,key] of specs)sourceData(name,next.layers[key]);
  const c=next.counts;
  const m=next.comparison_metrics;
  const coverage=next.pre_event_coverage;
  summary.textContent=`预测冻结：${next.prediction_frozen_at_utc}\n赛前交通：${next.observation_snapshot.traffic.feed_time_stamp}${next.event_snapshot?`\n赛时交通：${next.event_snapshot.traffic.feed_time_stamp}`:''}\n插件影响道路：${c.predicted_route_impact_edges} 条\n输入封路候选：${c.restriction_input_edges} 条\nVIZ 交通路段：${c.traffic_segments} 条\n赛事封路通报：${c.marathon_reports} 条${coverage?`\n\n赛前可测覆盖：${coverage.predicted_edges_with_viz_match}/${c.predicted_route_impact_edges} 条插件路段；${coverage.predicted_edges_without_viz_match} 条没有匹配 VIZ 路段\n匹配的 VIZ 路段：${coverage.matched_viz_segments}，其中可评分 ${coverage.scored_matched_viz_segments}`:''}${m?`\n\n赛时空间对照 · ${m.scored_segments} 个可评分 VIZ 路段\n预测路段 VIZ 匹配：${m.predicted_edges_with_viz_match}/${m.predicted_edge_count}（其余无 VIZ 覆盖）\n命中 ${m.hit} · 漏报 ${m.miss} · 误报 ${m.false_alarm} · 缺测 ${m.unscored}\n精确率 ${m.precision===null?'无分母':(100*m.precision).toFixed(1)+'%'} · 召回率 ${m.recall===null?'无分母':(100*m.recall).toFixed(1)+'%'}`:''}`;
  if(next.control_plan)summary.textContent+=`\n\n赛前选定对照：${next.control_plan.treated_segments_with_controls}/${next.control_plan.treated_segments} 个预测重合 VIZ 路段找到对照；${next.control_plan.control_segments} 条独立对照路段`;
  if(next.control_indicator)summary.textContent+=`\n两时刻对照有效组：${next.control_indicator.valid_treated_control_groups}；额外降速中位数：${next.control_indicator.median_pair_adjusted_speed_drop_fraction===null?'无法计算':(100*next.control_indicator.median_pair_adjusted_speed_drop_fraction).toFixed(1)+' 个百分点'}（描述性间接指标）\n新增封闭字段：预测重合路段 ${next.control_indicator.newly_reported_closed_treated} · 对照路段 ${next.control_indicator.newly_reported_closed_controls}`;
  summary.style.whiteSpace='pre-wrap';
  status.textContent=next.status==='PRE_EVENT_BASELINE_ONLY'?'已载入赛前地图；赛时观测和差异评分待采集。':'已载入两次交通快照的空间对照。';
  status.dataset.error='false';
  fitPrediction();
}

function fitPrediction(){
  if(!bundle)return;
  const bounds=new maplibregl.LngLatBounds();
  for(const key of ['predicted_route_impact','viz_controls'] as const)
    for(const feature of bundle.layers[key].features)
      if(feature.geometry.type==='LineString')for(const point of feature.geometry.coordinates)bounds.extend(point as [number,number]);
  if(!bounds.isEmpty())map.fitBounds(bounds,{padding:65,maxZoom:14,duration:0});
}

function lineDetails(feature:Feature):string{
  const p=feature.properties??{};
  const layer=String(p.layer??'VIZ');
  if(layer==='predicted_route_impact')return `插件预测影响路段\n${p.name||p.id}\nID: ${p.id}\n赛前 VIZ 空间覆盖: ${p.viz_baseline_coverage===true?'有':p.viz_baseline_coverage===false?'无':'未检查'}\n影响的冻结 OD: ${(p.route_labels??[]).join(', ')}`;
  if(layer==='restriction_input')return `情景输入的封路候选（不是预测）\n${p.name||p.id}\nID: ${p.id}`;
  if(layer==='viz_control')return `赛前匹配的非预测对照路段\nVIZ ID: ${p.unique_id}\n赛前车速: ${p.baseline_speed_kph} km/h\n自由流车速: ${p.freeflow_speed_kph} km/h\n对照不是赛事未影响的保证。`;
  if(p.change_class)return `VIZ 两快照变化路段\nID: ${p.unique_id}\n类别: ${p.change_class}\n预测几何重合: ${p.predicted_overlap===null?'无法判定':p.predicted_overlap?'是':'否'}\n赛前 / 赛时车速: ${p.baseline_speed_kph??'缺失'} / ${p.event_speed_kph??'缺失'} km/h\n赛前 / 赛时封闭字段: ${p.baseline_closed??'缺失'} / ${p.event_closed??'缺失'}\n空间判定: ${p.verdict}`;
  if(p.unique_id)return `VIZ 实时交通路段\nID: ${p.unique_id}\n车速: ${p.closed===1?'封闭字段为 1，零车速不视作测量':`${p.speedavg??'缺失'} km/h`}\n自由流车速: ${p.freeflowspeed??'缺失'} km/h\nLOS: ${p.los??'缺失'}\n快照: ${bundle?.observation_snapshot.traffic.feed_time_stamp??''}`;
  return `VIZ 马拉松封路通报（可能预先发布）\n${p.street??''}\n${p.content??''}\n通报时段: ${p.validity?.from??'?'} — ${p.validity?.to??'?'}\n通报 ID: ${p.id??''}`;
}

map.on('load',()=>{
  for(const [name,,layer] of specs){map.addSource(name,{type:'geojson',data:empty});map.addLayer(layer);}
  for(const box of document.querySelectorAll<HTMLInputElement>('input[data-layer]'))box.addEventListener('change',()=>map.setLayoutProperty(box.dataset.layer!,'visibility',box.checked?'visible':'none'));
  map.on('click',event=>{
    const features=map.queryRenderedFeatures(event.point,{layers:['changes','closures','predicted','controls','reports','traffic']});
    if(features.length)details.textContent=lineDetails(features[0] as Feature<LineString>);
  });
  map.on('mouseenter',['changes','closures','predicted','controls','reports','traffic'],()=>map.getCanvas().style.cursor='pointer');
  map.on('mouseleave',['changes','closures','predicted','controls','reports','traffic'],()=>map.getCanvas().style.cursor='');
  fetch('/validation/berlin-local.json').then(response=>{if(!response.ok)throw Error('未找到本地验证包，请用下方文件选择，或运行脚本采集并生成。');return response.json();}).then(data=>setBundle(validate(data))).catch(error=>{status.textContent=String(error);status.dataset.error='true';});
});

$<HTMLButtonElement>('#fit').addEventListener('click',fitPrediction);
$<HTMLInputElement>('#bundle-file').addEventListener('change',async event=>{
  const file=(event.target as HTMLInputElement).files?.[0];if(!file)return;
  try{setBundle(validate(JSON.parse(await file.text())));}catch(error){status.textContent=String(error);status.dataset.error='true';}
});
