// Everything, including NumPy/SciPy, loads from this website. No data is sent to a server.
import { loadPyodide } from './runtime/pyodide.mjs';
let initialization;
let queue=Promise.resolve();
const status = (s)=>self.postMessage({status:s});
async function checkedFetch(path,hash) {
 const response=await fetch(new URL(path,import.meta.url));
 if(!response.ok)throw new Error(`Could not load ${path} (HTTP ${response.status}). Keep the complete website folder together.`);
 const data=new Uint8Array(await response.arrayBuffer());
 if(hash) {
  const actual=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',data))).map(b=>b.toString(16).padStart(2,'0')).join('');
  if(actual!==hash)throw new Error(`Scientific source integrity check failed for ${path}. Reload the complete release.`);
 }
 return data;
}
async function initialize() {
 status('Loading local scientific runtime (about 31 MB on first visit)…');
 const base=new URL('./runtime/',import.meta.url).href;
 const py=await loadPyodide({indexURL:base,packageBaseUrl:base});
 status('Loading NumPy and SciPy…');
 await py.loadPackage(['numpy','scipy']);
 const manifest=JSON.parse(new TextDecoder().decode(await checkedFetch('./python/manifest.json')));
 const sources=await Promise.all(manifest.files.map(async file=>({file,data:await checkedFetch('./python/'+file.path,file.sha256)})));
 for(const {file,data} of sources) {
  const path='/app/'+file.path;
  py.FS.mkdirTree(path.slice(0,path.lastIndexOf('/')));
  py.FS.writeFile(path,data);
 }
 py.runPython("import sys; sys.path.insert(0, '/app'); from browser_bridge import handle_json");
 status('Ready · calculations stay on this device');
 return py;
}
self.onmessage=({data})=>{
 queue=queue.then(async()=>{
  try {
   initialization ||= initialize().catch(e=>{initialization=null;throw e;});
   const py=await initialization;
   py.globals.set('_browser_request',JSON.stringify(data));
   let value;
   try { value=await py.runPythonAsync('handle_json(_browser_request)'); }
   finally { py.globals.delete('_browser_request'); }
   self.postMessage({id:data.id,result:JSON.parse(value)});
  } catch(e) {
   const full=String(e.message||e);
   const last=full.match(/(?:ValueError|TypeError|KeyError|RuntimeError|OverflowError): ([^\n]+)/g);
   self.postMessage({id:data.id,error:last?last[last.length-1]:full});
  }
 });
};
