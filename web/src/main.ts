import './plugin';
import {MapLibreAdapter} from './maplibre-adapter';
import 'maplibre-gl/dist/maplibre-gl.css';
import './host.css';
const container=document.querySelector<HTMLElement>('#map');
const panel=document.querySelector('urban-impact-panel');
if(container&&panel){const adapter=new MapLibreAdapter(container);panel.mapAdapter=adapter;window.addEventListener('pagehide',()=>adapter.dispose(),{once:true});}
