const fs=await import('node:fs/promises');const t=await taskSpace(36),p=t.page('p1');const root='/Users/alec/嘉谏言序/会议室录音系统_PRD_v1.3/evidence/screenshots';const measurements=[];
const c=a=>p.click(`loc=css:${a==='close'?'.dialog-footer ':''}[data-act="${a}"]`);
async function size(w,h){await p.cdp('Emulation.setDeviceMetricsOverride',{width:w,height:h,deviceScaleFactor:1,mobile:false})}
async function snap(name){await p.screenshot({path:root+'/'+name+'.png'});measurements.push({name,...await p.evaluate(()=>({width:innerWidth,bodyWidth:document.documentElement.scrollWidth,overflow:document.documentElement.scrollWidth>innerWidth+2,dialog:!!document.querySelector('[role=dialog]')}))})}
await p.goto('file:///Users/alec/嘉谏言序/会议录音系统_可点击原型_v0.3.html');await p.reload();await size(1280,900);await snap('v03-01-tablet-scan');
await c('scan');await p.selectOption('loc=css:#scan-user','lin');await c('scan-confirm');await c('start');await p.evaluate(()=>{S.seconds=14407;render()});await size(1024,900);await snap('v03-02-long-recording');
await c('end');await p.waitForFunction(()=>S.phase==='saved',undefined,{timeout:5000});await snap('v03-03-saved-logout');
await c('mode:phone');await p.selectOption('loc=css:#phone-user','lin');await c('phone-in');await c('open:m1');await size(390,844);await snap('v03-04-phone-detail');
await c('edit');await snap('v03-05-mobile-edit');await c('close');await c('ptab:tasks');await snap('v03-06-mobile-tasks');await c('phone-list');await size(1280,900);await snap('v03-07-phone-list');
await c('mode:admin');await c('admin-in');await c('admin-tab:routes');await size(1600,1000);await snap('v03-08-admin-routes');
await p.evaluate(()=>{S.records.push({id:'rec-fault-view',title:'不向维护者显示的正文标题',owner:'lin',dept:'sales',duration:1800,progress:2,state:'AI_FAILED',summary:'',version:1,versions:[],snapshot:null,sent:false,attempts:2,grants:[],events:[],scenario:'ai_fail',target:'销售管理群（虚构）',sendCount:0})});await c('admin-tab:exceptions');await size(960,900);await snap('v03-09-admin-exceptions');
await p.cdp('Emulation.clearDeviceMetricsOverride',{});await fs.writeFile(root+'/layout-checks-v0.3.json',JSON.stringify(measurements,null,2));console.log(measurements);console.log(await p.snapshot());
