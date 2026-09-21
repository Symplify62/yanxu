const fs=await import('node:fs/promises');const t=await taskSpace(36),p=t.page('p1');
const out='/Users/alec/嘉谏言序/会议室录音系统_PRD_v1.3/evidence';const checks=[];
const c=a=>p.click(`loc=css:${a==='close'?'.dialog-footer ':''}[data-act="${a}"]`),fill=(id,v)=>p.fill('loc=css:#'+id,v),sel=(id,v)=>p.selectOption('loc=css:#'+id,v);
async function check(name,fn){const pass=await p.evaluate(fn);checks.push({name,pass:!!pass});console.log((pass?'PASS ':'FAIL ')+name);await fs.writeFile(out+'/prototype-checks-v0.3.json',JSON.stringify({scope:'synthetic_prototype_only',checks,product_tests_executed:0},null,2));if(!pass)throw Error(name)}
async function login(id){await c('mode:phone');if(await p.evaluate(()=>!!S.phone))await c('phone-out');await sel('phone-user',id);await c('phone-in')}
async function scan(id){await c('scan');await sel('scan-user',id);await c('scan-confirm')}
await p.goto('file:///Users/alec/嘉谏言序/会议录音系统_可点击原型_v0.3.html');await p.reload();
await check('未扫码不能开始录音',()=>!document.querySelector('[data-act="start"]')&&S.employee===null);
await c('expire');await check('过期扫码禁用',()=>document.querySelector('[data-act="scan"]').disabled);await c('refresh-code');
await scan('outside');await check('跨企业身份拒绝',()=>!S.employee&&document.querySelector('[role=alert]').textContent.includes('本企业'));await c('close');
await scan('left');await check('停用身份拒绝',()=>!S.employee&&!!document.querySelector('[role=alert]'));await c('close');
await scan('zhou');await check('有效新员工自动开户基础角色',()=>user('zhou').registered&&S.employee==='zhou'&&S.phase==='ready'&&!S.admin);
await c('exit-session');await check('未开录退出回新挑战',()=>S.employee===null&&S.phase==='scan'&&!S.consumed);
await scan('lin');await check('默认主部门且无任意群选择',()=>S.dept==='sales'&&!!document.querySelector('#capture-dept')&&!document.body.textContent.includes('本场不发群'));
await c('start');await c('pause');await check('暂停仍同一发起人',()=>S.phase==='paused'&&S.employee==='lin');await c('resume');
await p.evaluate(()=>{S.seconds=4*3600+3;render()});await check('超过4小时没有业务截止',()=>S.phase==='recording'&&document.querySelector('#timer').textContent==='04:00:03');
await c('end');await p.waitForFunction(()=>Proto3.state.phase==='saved',undefined,{timeout:5000});
await check('本地保存后员工退出而任务存在',()=>S.employee===null&&S.records.at(-1).owner==='lin'&&S.records.at(-1).duration>=14403);
await p.waitForFunction(()=>Proto3.state.records.at(-1).sent,undefined,{timeout:15000});
await check('无会后操作自动完成四类资料与发送',()=>S.records.at(-1).progress===4&&S.records.at(-1).sendCount===1&&S.records.at(-1).snapshot.target==='销售管理群（虚构）');
await check('无正常人工核对状态',()=>!document.body.textContent.includes('待审核')&&!document.querySelector('[data-act="approve"]'));
await login('lin');const rid=await p.evaluate(()=>S.last);await c('open:'+rid);await check('本人手机可见资料',()=>document.body.textContent.includes('AI 生成')&&!!document.querySelector('[data-act="edit"]'));
await c('ptab:tasks');await check('未知事项不阻断已发送',()=>document.body.textContent.includes('负责人未明确')&&S.records.find(m=>m.id===S.selected).sent);
await c('ptab:audio');await check('未附音频不假播放，下载独立禁用',()=>document.body.textContent.includes('未附真实音频')&&[...document.querySelectorAll('button')].some(x=>x.disabled&&x.textContent.includes('下载')));
await c('ptab:summary');await c('edit');await fill('edit-text','更正后的合成纪要 <script>alert(1)</script>');await c('save-edit');await check('缺少更正原因不保存且保留输入',()=>S.records.find(m=>m.id===S.selected).version===1&&document.querySelector('#edit-text').value.includes('更正'));
await fill('edit-reason','合成原文校对');await fill('task-owner-1','刘工');await fill('task-due-1','下周三（人工补充，日期未解析）');await c('save-edit');await check('保存更正不重发旧快照',()=>{const m=S.records.find(x=>x.id===S.selected);return m.version===2&&m.snapshot.v===1&&m.sendCount===1&&!document.querySelector('.meeting-text script')});
await check('事项可选更正保留证据且不改群快照',()=>{const m=S.records.find(x=>x.id===S.selected);return m.tasks[1].owner==='刘工'&&m.tasks[1].source==='seg-007'&&m.snapshot.tasks[1].owner===''&&m.sendCount===1});
await c('share');await sel('share-user','chen');await c('add-share');await c('close');await check('只读共享不新增群消息',()=>S.records.find(m=>m.id===S.selected).sendCount===1);
await login('chen');await c('open:'+rid);await check('跨部门明确授权可看但不能编辑',()=>document.body.textContent.includes('更正后的合成纪要')&&!document.querySelector('[data-act="edit"]'));
await login('lin');await c('open:'+rid);await c('share');const grant=await p.evaluate(()=>S.records.find(m=>m.id===S.selected).grants.find(g=>g.active).id);await c('revoke:'+grant);await c('close');
await login('chen');await p.evaluate(id=>{S.selected=id;render()},rid);await check('撤销后旧链接无权且不泄露标题正文',()=>document.body.textContent.includes('无法访问')&&!document.body.textContent.includes('更正后的合成纪要'));
await c('mode:tablet');await c('next');await scan('chen');await sel('scenario','save_fail');await c('start');await c('end');await p.waitForFunction(()=>S.phase==='save-error',undefined,{timeout:5000});
await check('保存失败不伪退出或归属下一人',()=>S.employee==='chen'&&S.phase==='save-error'&&!document.querySelector('[data-act="next"]'));
await c('retry-save');await p.waitForFunction(()=>S.phase==='saved',undefined,{timeout:5000});await check('保存恢复仍归属原人',()=>S.employee===null&&S.records.at(-1).owner==='chen');
await c('next');await scan('lin');await c('start');await c('network');await c('end');await p.waitForFunction(()=>S.phase==='saved',undefined,{timeout:5000});await check('离线保存退出且保留待传',()=>S.records.at(-1).owner==='lin'&&S.records.at(-1).state==='WAITING_NETWORK'&&S.employee===null);await c('next');await check('离线不能新场冒用旧身份',()=>document.querySelector('[data-act="scan"]').disabled&&S.employee===null);await c('network');
await scan('zhou');await c('start');await check('下一场独立人员且旧任务继续',()=>S.employee==='zhou'&&S.records.some(m=>m.id.startsWith('rec')&&m.owner==='lin'));await c('end');await p.waitForFunction(()=>S.phase==='saved',undefined,{timeout:5000});
// Fault injection model checks use synthetic tasks; no network or external service.
await p.evaluate(()=>{for(const [id,scenario,progress,target] of [['rec-ai','ai_fail',1,'销售管理群（虚构）'],['rec-missing','no_route',3,''],['rec-unknown','unknown',3,'销售管理群（虚构）']])S.records.push({id,title:'仅故障样例',owner:'lin',dept:'sales',duration:99,progress,state:'READY',summary,version:1,versions:[],snapshot:{v:1,text:summary,target},sent:false,attempts:0,grants:[],events:[],scenario,target,sendCount:0});});
await p.waitForFunction(()=>S.records.find(m=>m.id==='rec-ai').state==='AI_FAILED'&&S.records.find(m=>m.id==='rec-unknown').state==='UNKNOWN',undefined,{timeout:10000});
await check('AI自动重试耗尽后只产生管理员告警',()=>S.records.find(m=>m.id==='rec-ai').attempts===2&&S.audit.some(e=>e.action==='管理员告警'&&e.detail.includes('rec-ai')));
await check('无路由不猜群、不落待审核',()=>S.records.find(m=>m.id==='rec-missing').state==='UNCONFIGURED'&&S.records.find(m=>m.id==='rec-missing').sendCount===0);
await p.evaluate(()=>{const m=S.records.find(x=>x.id==='rec-unknown');for(let i=0;i<5;i++)advance(m)});await check('UNKNOWN不会盲重发',()=>S.records.find(m=>m.id==='rec-unknown').sendCount===0);
await login('lin');await p.evaluate(()=>{S.selected='rec-ai';render()});await check('员工可见失败但无管理员恢复按钮',()=>document.body.textContent.includes('管理员')&&!document.querySelector('[data-act^="recover:"]'));
await c('mode:admin');await c('admin-in');await c('admin-tab:exceptions');await c('recover:rec-unknown');await c('save-recover');await check('异常处理依据必填',()=>S.records.find(m=>m.id==='rec-unknown').state==='UNKNOWN'&&!!document.querySelector('[role=alert]'));
await fill('recovery-reason','演示已查看虚构渠道记录');await c('save-recover');await check('人工核对标识不伪造渠道回执',()=>S.records.find(m=>m.id==='rec-unknown').manualResolution&&document.body.textContent.includes('人工记录已核对'));
await c('recover:rec-ai');await fill('recovery-reason','模拟AI依赖恢复');await c('save-recover');await p.waitForFunction(()=>S.records.find(m=>m.id==='rec-ai').sent,undefined,{timeout:10000});await check('恢复失败阶段自动完成、不重做人工核对',()=>S.records.find(m=>m.id==='rec-ai').sent&&S.records.find(m=>m.id==='rec-ai').sendCount===1);
await c('admin-tab:users');await c('toggle-user:zhou');await login('zhou');await check('已开户员工停用后不能重新开户绕过',()=>S.phone===null&&user('zhou').registered&&!user('zhou').active);
await c('mode:admin');await c('admin-tab:audit');await check('审计安全展示而非执行输入',()=>!document.querySelector('.audit-entry script'));
console.log(JSON.stringify({passed:checks.filter(x=>x.pass).length,total:checks.length}));console.log(await p.snapshot());
