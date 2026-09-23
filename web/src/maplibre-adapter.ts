import * as maplibregl from 'maplibre-gl';
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url';
maplibregl.setWorkerUrl(workerUrl);
import type {FeatureCollection, Geometry, Position} from 'geojson';
import type {MapAdapter,MapSelection} from './map-adapter';
export class MapLibreAdapter implements MapAdapter {
  private map:maplibregl.Map;
  private data:FeatureCollection={type:'FeatureCollection',features:[]};
  private listeners=new Set<(selection:MapSelection)=>void>();
  private polygon:Geometry|null=null;
  private ids:string[]=[];
  private drawPoints:Position[]|null=null;
  private drawDone:((geometry:Geometry)=>void)|null=null;
  private disposed=false;
  constructor(container:HTMLElement){
    this.map=new maplibregl.Map({container,center:[24.95,60.18],zoom:12,attributionControl:false,
      style:{version:8,sources:{},layers:[{id:'background',type:'background',paint:{'background-color':'#eef2f0'}}]}});
    this.map.addControl(new maplibregl.NavigationControl(),'bottom-right');
    this.map.addControl(new maplibregl.AttributionControl({compact:false,customAttribution:'Local registered data · source licenses in results'}),'bottom-left');
    this.map.on('load',()=>{this.mountLayers();this.updateData();});
    this.map.on('click',event=>{
      if(this.drawPoints){this.drawPoints.push([event.lngLat.lng,event.lngLat.lat]);this.renderDraft();return;}
      const features=this.map.queryRenderedFeatures(event.point,{layers:['facilities','roads']});
      const p=features[0]?.properties;
      if(p?.id)this.listeners.forEach(callback=>callback({id:String(p.id),type:String(p.type??'RoadSegment'),name:String(p.name??'')}));
    });
    this.map.on('dblclick',event=>{
      if(!this.drawPoints)return;
      event.preventDefault();
      const points=this.drawPoints.filter((p,i,a)=>i===0||p[0]!==a[i-1][0]||p[1]!==a[i-1][1]);
      if(points.length<3)return;
      const geometry:Geometry={type:'Polygon',coordinates:[[...points,points[0]]]};
      this.drawPoints=null;this.setPerimeter(geometry);this.drawDone?.(geometry);this.drawDone=null;
      this.map.doubleClickZoom.enable();this.map.getCanvas().style.cursor='';
    });
  }
  private mountLayers(){
    this.map.addSource('city',{type:'geojson',data:this.data});
    this.map.addSource('perimeter',{type:'geojson',data:{type:'FeatureCollection',features:[]}});
    this.map.addLayer({id:'perimeter',type:'fill',source:'perimeter',filter:['==',['geometry-type'],'Polygon'],paint:{'fill-color':'#c27135','fill-opacity':.18}});
    this.map.addLayer({id:'perimeter-line',type:'line',source:'perimeter',paint:{'line-color':'#ad5b28','line-width':2,'line-dasharray':[3,2]}});
    this.map.addLayer({id:'roads',type:'line',source:'city',filter:['==',['geometry-type'],'LineString'],paint:{'line-color':'#a7b5b1','line-width':3}});
    this.map.addLayer({id:'selected',type:'line',source:'city',filter:['in',['get','id'],['literal',this.ids]],paint:{'line-color':'#da7846','line-width':6}});
    this.map.addLayer({id:'facilities',type:'circle',source:'city',filter:['==',['geometry-type'],'Point'],paint:{'circle-radius':6,'circle-color':'#176a5e','circle-stroke-color':'white','circle-stroke-width':2}});
  }
  private updateData(){
    (this.map.getSource('city') as maplibregl.GeoJSONSource|undefined)?.setData(this.data);
    this.highlight(this.ids);this.setPerimeter(this.polygon);this.fitExtent();
  }
  setData(data:FeatureCollection){this.data=data;this.updateData();}
  highlight(ids:string[]){this.ids=ids;if(this.map.getLayer('selected'))this.map.setFilter('selected',['in',['get','id'],['literal',ids]]);}
  setPerimeter(geometry:Geometry|null){this.polygon=geometry;(this.map.getSource('perimeter') as maplibregl.GeoJSONSource|undefined)?.setData({type:'FeatureCollection',features:geometry?[{type:'Feature',properties:{},geometry}]:[]});}
  private renderDraft(){if(this.drawPoints&&this.drawPoints.length>1){const points=this.drawPoints;this.setPerimeter({type:points.length>2?'Polygon':'LineString',coordinates:points.length>2?[[...points,points[0]]]:points} as Geometry);}}
  fitExtent(){
    const coords:Position[]=[];
    for(const f of this.data.features){if(f.geometry.type==='Point')coords.push(f.geometry.coordinates);else if(f.geometry.type==='LineString')coords.push(...f.geometry.coordinates);}
    if(!coords.length)return;
    const bounds=new maplibregl.LngLatBounds();coords.forEach(p=>{if(Number.isFinite(p[0])&&Number.isFinite(p[1]))bounds.extend([p[0],p[1]]);});
    if(!bounds.isEmpty())this.map.fitBounds(bounds,{padding:70,maxZoom:16,duration:0});
  }
  onSelect(callback:(selection:MapSelection)=>void){this.listeners.add(callback);return()=>this.listeners.delete(callback);}
  drawPolygon(callback:(geometry:Geometry)=>void){this.drawPoints=[];this.drawDone=callback;this.map.doubleClickZoom.disable();this.map.getCanvas().style.cursor='crosshair';}
  dispose(){if(this.disposed)return;this.disposed=true;this.listeners.clear();this.drawPoints=null;this.drawDone=null;this.map.remove();}
}
