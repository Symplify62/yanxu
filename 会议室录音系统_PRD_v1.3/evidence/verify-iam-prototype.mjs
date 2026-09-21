// Execute with: ego-browser nodejs < this-file. Requires the existing TaskSpace 35.
const fs=await import('node:fs/promises');
const root='/Users/alec/嘉谏言序/会议室录音系统_PRD_v1.1/evidence';
const t=await taskSpace(35),p=t.page('p1');const results=[];
async function check(name,fn){const ok=await p.evaluate(fn);results.push({name,pass:!!ok});console.log((ok?'PASS ':'FAIL ')+name);if(!ok){await fs.writeFile(root+'/prototype-checks.json',JSON.stringify(results,null,2));throw Error(name)}}
const click=a=>p.click(`loc=css:${a==='close-modal'?'.dialog-footer ':''}[data-action="${a}"]`);
const fill=(id,v)=>p.fill('loc=css:#'+id,v);
const select=(id,v)=>p.selectOption('loc=css:#'+id,v);
const reason=()=>fill('iam-reason','原型验收：合成数据变更');
async function commit(){await click('iam-preview');await click('iam-commit')}
async function login(id){if(await p.evaluate(()=>!!I.session))await click('iam-logout');await select('iam-login-user',id);await click('iam-login')}
await p.goto('file:///Users/alec/嘉谏言序/会议录音系统_可点击原型_v0.2.html#users');
await p.reload();await p.waitForSelector('loc=css:#iam-login-user');
await check('后台先显示登录且不展示管理表格',()=>!!document.querySelector('#iam-login-user')&&!document.querySelector('.data-table'));
await select('iam-login-user','u4');await click('iam-login');await check('停用账号不能登录',()=>!I.session&&document.querySelector('.toast').textContent.includes('停用'));
await login('u1');await check('管理员登录后进入用户页',()=>I.session==='u1'&&!!document.querySelector('#iam-search'));
await click('iam-new-user');await click('iam-preview');await check('缺必填内容保留表单并提示',()=>!I.draft&&document.querySelector('.toast').textContent.includes('原因'));
await fill('iam-name','验收员工');await fill('iam-account','viewer.demo');await reason();await click('iam-preview');await check('重复账号被拒绝',()=>!I.draft&&document.querySelector('.toast').textContent.includes('已存在'));
await fill('iam-account','qa.demo');await click('iam-preview');await check('预览不立即创建账号',()=>!!I.draft&&!I.users.some(u=>u.account==='qa.demo'));
await click('close-modal');await check('取消预览无变更',()=>!I.users.some(u=>u.account==='qa.demo'));
await click('iam-new-user');await fill('iam-name','验收员工');await fill('iam-account','qa.demo');await reason();await commit();await check('新增用户成功且没有自动内容权',()=>I.users.some(u=>u.account==='qa.demo')&&!iprobe(I.users.find(u=>u.account==='qa.demo').id,'m1','view').ok);
await fill('iam-search','不存在的员工');await check('搜索空态',()=>document.body.textContent.includes('没有匹配用户'));await fill('iam-search','');
await click('iam-toggle-user-u3');await reason();await commit();await check('停用保留用户与历史并拒绝权限',()=>iu('u3').status==='disabled'&&grantsFor('u3').length===1&&!iprobe('u3','m1','view').ok);
await login('u3');await check('刚停用的账号登录被拒绝',()=>!I.session);
await login('u1');await click('iam-toggle-user-u3');await reason();await commit();
await click('iam-tab-org');await click('iam-new-dept');await fill('iam-name','验收子部门');await select('iam-parent','sales');await reason();await commit();
await check('创建层级部门成功',()=>I.depts.some(d=>d.name==='验收子部门'&&d.parent==='sales'));
const newDept=await p.evaluate(()=>I.depts.find(d=>d.name==='验收子部门').id);
await click('iam-edit-dept-sales');await select('iam-parent',newDept);await reason();await click('iam-preview');await check('组织循环被拒绝',()=>!I.draft&&document.querySelector('.toast').textContent.includes('下级'));
await click('close-modal');await click('iam-toggle-dept-sales');await reason();await click('iam-preview');await check('有依赖部门禁止停用',()=>!I.draft&&document.querySelector('.toast').textContent.includes('依赖'));await click('close-modal');
await click('iam-tab-roles');await click('iam-new-role');await fill('iam-name','验收只读角色');await p.click('loc=css:input[name="iam-perm"][value="view"]');await reason();await commit();await check('业务角色创建成功',()=>I.roles.some(r=>r.name==='验收只读角色'&&r.perms.length===1));
await click('iam-edit-role-reader');await p.click('loc=css:input[name="iam-perm"][value="download"]');await reason();await click('iam-preview');await check('账号管理员不能借角色修改扩大已授权内容',()=>!I.draft&&document.querySelector('.toast').textContent.includes('无权'));await click('close-modal');
await click('iam-expire');await check('会话过期回登录',()=>!I.session&&!!document.querySelector('#iam-login-user'));
await login('u2');await check('业务授权者进入授权页',()=>I.tab==='grants');
await click('iam-new-grant');await reason();await click('iam-preview');await check('历史边界必选',()=>!I.draft&&document.querySelector('.toast').textContent.includes('历史'));
await select('iam-history','all');await select('iam-scope','all');await click('iam-preview');await check('超出公司范围的委派被拒绝',()=>!I.draft&&document.querySelector('.toast').textContent.includes('超出'));
await select('iam-scope','m1');await select('iam-role','editor');await click('iam-preview');await check('授权预览显示角色与范围',()=>I.draft?.data.scope==='m1'&&I.draft?.data.role==='editor'&&!iprobe('u3','m1','edit').ok);
await click('iam-commit');await check('授权后允许编辑指定会议',()=>iprobe('u3','m1','edit').ok&&!iprobe('u3','m2','edit').ok);
const grantId=await p.evaluate(()=>I.grants.find(g=>g.role==='editor').id);
await click('iam-revoke-'+grantId);await reason();await commit();await check('撤销编辑保留独立只读权限',()=>!iprobe('u3','m1','edit').ok&&iprobe('u3','m1','view').ok);
await click('iam-tab-groups');await click('iam-edit-group-g1');await p.click('loc=css:input[name="iam-member"][value="u3"]');await reason();await click('iam-preview');await check('成员变更预览提示继承历史范围',()=>I.draft.preview.some(([k,v])=>k==='继承范围'&&v.includes('历史')));await click('iam-commit');await check('移组撤销组带来的读取资格',()=>!iprobe('u3','m1','view').ok);
await click('iam-edit-group-g1');await p.click('loc=css:input[name="iam-member"][value="u3"]');await reason();await commit();
await click('iam-tab-effective');await select('iam-probe-meeting','m3');await check('普通部门范围不能读取受限会议',()=>!iprobe('u3','m3','view').ok&&document.querySelector('.iam-verdict').textContent.includes('显式授权'));
// Model fixtures to exercise the pairwise scope invariant, separate from UI acceptance.
await p.evaluate(()=>{I.grants.push({id:'test-readall',subject:'user:u3',role:'reader',scope:'all',history:'all',active:true},{id:'test-editsales',subject:'user:u3',role:'editor',scope:'sales',history:'all',active:true})});
await check('全公司只读加销售编辑不变成财务编辑',()=>iprobe('u3','m2','view').ok&&!iprobe('u3','m2','edit').ok&&iprobe('u3','m1','edit').ok);
await p.evaluate(()=>{I.grants=I.grants.filter(g=>!g.id.startsWith('test-'))});
await check('原型变更留下审计',()=>S.audit.some(a=>a.action==='权限管理变更'&&a.detail.includes('原因')));
await p.selectOption('loc=css:#role','reviewer');await p.click('loc=role:button[name="泵组报价与交付协调"]');await click('edit-summary');await fill('summary-edit','原型回归：修订记录');await fill('edit-reason','验证原有版本流程');await click('save-summary');await check('原有纪要修订保留版本且不发送',()=>S.version===2&&S.versions.length===2&&!S.sent);
await click('mode-tablet');await click('start');await check('原录音开始状态',()=>S.phase==='recording');await click('pause');await check('原暂停状态',()=>S.phase==='paused');await click('resume');await check('原继续状态',()=>S.phase==='recording');await p.evaluate(()=>Proto.save());await p.waitForFunction(()=>Proto.state.phase==='saved',undefined,{timeout:10000});await check('结束后模拟保存仍工作',()=>S.phase==='saved'&&S.queue.length>0);
await fs.writeFile(root+'/prototype-checks.json',JSON.stringify({scope:'synthetic_prototype_only',timestamp:new Date().toISOString(),checks:results,product_tests_executed:0},null,2));
console.log(JSON.stringify({passed:results.filter(x=>x.pass).length,total:results.length}));
console.log(await p.snapshot());
