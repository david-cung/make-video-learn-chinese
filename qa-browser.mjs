import {spawn} from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
const root=path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/,'$1'));
const browser=spawn('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',['--headless=new','--disable-gpu','--no-first-run','--remote-debugging-port=9595',`--user-data-dir=${path.join(root,'qa-profile')}`,'http://127.0.0.1:3015'],{windowsHide:true,stdio:'ignore'});
let ws;const pending=new Map();let id=0;
async function rpc(method,params={}){const n=++id;return new Promise((resolve,reject)=>{pending.set(n,{resolve,reject});ws.send(JSON.stringify({id:n,method,params}));});}
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
async function evaluate(expression){const result=await rpc('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});if(result.exceptionDetails)throw Error(JSON.stringify(result.exceptionDetails));return result.result.value;}
try{
 let pages;
 for(let n=0;n<25;n++){try{pages=await(await fetch('http://127.0.0.1:9595/json/list')).json();if(pages.some(p=>p.url.includes('3015')))break;}catch{}await sleep(400);}
 const page=pages.find(p=>p.url.includes('3015'));if(!page)throw Error('Preview page unavailable');
 ws=new WebSocket(page.webSocketDebuggerUrl);await new Promise((r,j)=>{ws.onopen=r;ws.onerror=j;});
 ws.onmessage=e=>{const d=JSON.parse(e.data);if(d.id){const p=pending.get(d.id);pending.delete(d.id);d.error?p.reject(Error(JSON.stringify(d.error))):p.resolve(d.result);}};
 await rpc('Page.enable');await rpc('Emulation.setDeviceMetricsOverride',{width:1440,height:1100,deviceScaleFactor:1,mobile:false});await sleep(1000);
 await evaluate(`document.getElementById('topic').value='Gọi cà phê';document.getElementById('plan').click();`);
 for(let n=0;n<30;n++){if(await evaluate(`document.querySelectorAll('.scene').length===5`))break;await sleep(200);}
 const desktop=await evaluate(`({scenes:document.querySelectorAll('.scene').length,canRender:!document.getElementById('render').disabled,preview:document.getElementById('previewHanzi').textContent,overflow:document.documentElement.scrollWidth>innerWidth,jobs:document.querySelectorAll('.job').length})`);
 if(desktop.scenes!==5||!desktop.canRender||desktop.overflow||desktop.jobs<1)throw Error(JSON.stringify(desktop));
 const screenshot=await rpc('Page.captureScreenshot',{format:'png',captureBeyondViewport:true});fs.writeFileSync(path.join(root,'app-desktop.png'),Buffer.from(screenshot.data,'base64'));
 await evaluate(`document.querySelectorAll('.scene-head')[1].click()`);
 const chinese=await evaluate(`document.getElementById('previewText').textContent`);if(!chinese.includes('咖啡'))throw Error('Wrong Chinese scene preview');
 await rpc('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});await sleep(300);
 const mobile=await evaluate(`({overflow:document.documentElement.scrollWidth>innerWidth,width:innerWidth})`);if(mobile.overflow)throw Error('Mobile horizontal overflow');
 const mobileShot=await rpc('Page.captureScreenshot',{format:'png',captureBeyondViewport:true});fs.writeFileSync(path.join(root,'app-mobile.png'),Buffer.from(mobileShot.data,'base64'));
 console.log(JSON.stringify({desktop,mobile,chinese},null,2));
}finally{if(ws)ws.close();spawn('taskkill',['/pid',String(browser.pid),'/T','/F'],{windowsHide:true,stdio:'ignore'});}
