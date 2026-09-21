const fs=await import('node:fs/promises');const t=await taskSpace(35),p=t.page('p1');
const out='/Users/alec/嘉谏言序/会议室录音系统_PRD_v1.1/evidence/screenshots';const measures=[];
const click=a=>p.click(`loc=css:[data-action="${a}"]`);
async function size(w,h){await p.cdp('Emulation.setDeviceMetricsOverride',{width:w,height:h,deviceScaleFactor:1,mobile:false})}
async function capture(name){await p.screenshot({path:out+'/'+name+'.png'});measures.push({name,...await p.evaluate(()=>({width:innerWidth,documentWidth:document.documentElement.scrollWidth,bodyOverflow:document.documentElement.scrollWidth>innerWidth+2,dialog:!!document.querySelector('[role="dialog"]')}))})}
await p.goto('file:///Users/alec/嘉谏言序/会议录音系统_可点击原型_v0.2.html#users');await p.reload();await p.waitForSelector('loc=css:#iam-login-user');
await size(1280,900);await capture('01-login-1280');await click('iam-login');await size(1600,1000);await capture('02-users-1600');
await size(1280,900);await click('iam-tab-org');await capture('03-org-1280');
await size(960,900);await click('iam-tab-roles');await capture('04-roles-960');
await size(390,844);await click('iam-tab-users');await capture('05-users-390');
await size(1280,900);await click('iam-logout');await p.selectOption('loc=css:#iam-login-user','u2');await click('iam-login');
await click('iam-new-grant');await p.selectOption('loc=css:#iam-role','editor');await p.selectOption('loc=css:#iam-history','all');await p.fill('loc=css:#iam-reason','授权核对该场会议纪要');await click('iam-preview');await capture('06-grant-preview-1280');await size(390,844);await capture('07-grant-preview-390');await p.click('loc=css:.dialog-footer [data-action="close-modal"]');
await size(1280,900);await click('iam-tab-groups');await capture('08-groups-1280');await click('iam-tab-effective');await p.selectOption('loc=css:#iam-probe-meeting','m3');await capture('09-denied-1280');
await p.cdp('Emulation.clearDeviceMetricsOverride',{});
await fs.writeFile(out+'/layout-checks.json',JSON.stringify(measures,null,2));console.log(measures);console.log(await p.snapshot());
