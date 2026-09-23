import {NullMapAdapter} from './plugin';
import './host.css';
const panel=document.querySelector('urban-impact-panel');
if(panel)panel.mapAdapter=new NullMapAdapter();
