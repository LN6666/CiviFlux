import type {FeatureCollection, Geometry} from 'geojson';
export type MapSelection = {id:string;type:string;name?:string};
/** Small host boundary; the component never sees a MapLibre instance. */
export interface MapAdapter {
  setData(data:FeatureCollection):void;
  highlight(ids:string[]):void;
  setPerimeter(geometry:Geometry|null):void;
  fitExtent():void;
  onSelect(callback:(selection:MapSelection)=>void):()=>void;
  drawPolygon?(callback:(geometry:Geometry)=>void):void;
  dispose():void;
}
export class NullMapAdapter implements MapAdapter {
  data:FeatureCollection={type:'FeatureCollection',features:[]};
  selected:string[]=[];
  private callbacks=new Set<(selection:MapSelection)=>void>();
  setData(data:FeatureCollection){this.data=data;}
  highlight(ids:string[]){this.selected=[...ids];}
  setPerimeter(_geometry:Geometry|null){}
  fitExtent(){}
  onSelect(callback:(selection:MapSelection)=>void){this.callbacks.add(callback);return()=>this.callbacks.delete(callback);}
  select(selection:MapSelection){this.callbacks.forEach(callback=>callback(selection));}
  dispose(){this.callbacks.clear();}
}
