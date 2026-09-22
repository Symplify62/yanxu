# 真实账号、云端声音档案与说话人识别实施

状态：2026-09-22本地实现、联调及独立审查修复已完成；尚未生产切换。用户在现有本机App与三段后端方案后明确要求“落实”。已确认组织者/管理员账号密码登录，参会人不必登录；公共逐字稿只显示说话人编号，登录授权后显示姓名。现有本机保存同意不等于云端保存同意，不自动上传0.2.0样本。

## 本轮完成条件

A. 可撤销真实会话、初始化管理员、部门/角色/用户/人员目录API及实际管理界面；Android真实登录/目录同步，按服务和账号隔离缓存。
B. 受授权的单人登记、明确云端同意、私有文件、生成/更新/撤回与版本；本机样本显式映射迁移，不按姓名自动合并。
C. 受保护录音和固定名单、幂等上传及旧客户端隔离；纯ASR与说话人归属分离；真实模型提取/匹配、未知拒绝；公共编号/私有实名的服务端投影；原有音频和ASR/DeepSeek回归。
D. 本地隔离数据上端到端及API越权测试、真实模型烟测、Web截图和Android安装；生产迁移/发布另按既有授权边界，不把代码完成当上线。未取得真实同事素材前，不宣称实际会议准确率。

## 分工与文件边界

- 身份代理：backend/yanxu/identity/ + tests/test_identity.py + pyproject/uv.lock；不得修改api.py/store.py/config.py。
- 声音代理：backend/yanxu/voice/ + tests/test_voice*.py + tools/voice-runtime/；独立环境/权重可存.local-data，不修改既有ASR环境；不改api.py/store.py/config.py。
- Android代理：android真实登录、云目录、云登记和受保护会议上传；本轮私有数据不自动外发，默认新功能服务需部署后启用；不改后端/前端。
- 主任务：配置/迁移接入、managed recordings、处理链路/投影、Web管理界面、集成验证与交付记录。

## 接口契约 v1（各任务共用）

身份模块导出 initialize(store), router, current_account(request), require_permission(request, permission)。返回principal为dict：id(账号ID),username,personId,displayName,permissions(list)。权限 record/users/roles/departments/voices，首版单组织；普通成员仅本人声音，组织者可协助本组织人员登记但无后台删除权。

POST /api/auth/login {username,password} → {accessToken,expiresAt,account}; GET /api/auth/me → account；POST /api/auth/logout。
GET /api/people → {items:[{id,name,detail,departmentId,departmentName,active}],departments:[{id,name,parentId}]}。
POST /api/people {name,detail} → Person；组织者的record权限可以新增没有登录账号的参会人，不能通过此入口传账号/密码/角色或修改部门。管理后台带账号的用户创建仍要求users权限。
后台GET/POST /api/admin/users、roles、departments，PATCH/DELETE /api/admin/{resource}/{id}。用户面向Person(id,name,detail,departmentId,active)，可选关联username/password/roleId；bootstrap产生管理员。角色字段id/name/description/permissions；部门id/name/parentId。

声音模块导出 initialize(store), router, process_one(store,engine=None), enqueue_attribution(store,recording_id), protected_transcript(store,row), public_transcript(transcript)。引擎真实实现与测试桩分开，未配置模型明确报未就绪，不能假ready。
GET /api/voice-profiles → {items:[{personId,status,version,recordedAt,error}]}，仅返回有权目录。POST /api/people/{personId}/voice-enrollments {clientId,sha256,totalBytes,nameConfirmed:true,voiceConfirmed:true,cloudConsent:true} → {id,status}。
PUT /api/voice-enrollments/{id}/audio (WAV bytes, bearer)；POST /api/voice-enrollments/{id}/complete → {id,status}；GET /api/voice-enrollments/{id}；POST /api/people/{id}/voice-profile/revoke；GET /api/people/{id}/voice-profile/audio (authenticated)。样本不得经过公开recordings路径。Voice module依赖identity.current_account/require_permission，Person存在性从identity_people表查（字段id,name,detail,department_id,active）。

受保护会议：POST /api/managed/recordings，body沿用原RecordingCreate并加participants:[{personId}]、rosterClientId；服务端按当前身份namespace client_id，校验并原子保存快照；后续分片仍用uploadToken，token只属于已认证创建者。GET /api/managed/recordings/{id} 用bearer返回授权实名；GET /api/managed/recordings 返回本账号录音。旧匿名create禁止未知的人员/会话字段，也不得返回managed录音上传token。

本轮v1先将App开始时固定的本机名单附带上传并由服务器校验/存快照；离线录音不丢失，恢复身份后同步。全选上传显式ID集。v1不实施录音中名单追加；不把桌面原型的追加能力当原生已实现。voice模块从recordings.roster_json读取[{personId,name,...}]；owner_account_id保护归属。protected记录participants只在受控接口返回。

新增cfg参数（主任务添加）：identity_enabled=True, session_hours=24, backup_token='', voice_worker_token='', voice_engine_command='', voice_match_threshold=0.75(暂定可配置非概率), voice_match_margin=0.08(待真实样本校准), voice_private_bucket='', voice_private_domain=''。所有私有数据默认cfg.data_dir/private-voices（云端部署亦私有），Qiniu私有适配可配置且核验空间私有；不能误用原公开bucket。现有cfg.db_path共享SQLite，feature_schema表按模块版本迁移，不无条件重置user_version。

声音归属使用独立任务表；主任务在ASR成功后enqueue_attribution并将analysis job置waiting；归属成功/明确失败后才重新置pending，失败保留普通逐字稿。任务完成必须核对租约、输入/声纹/授权revision。声音worker本地或独立机器token远程领取；任何样本/embedding不得放公共transcript里。DeepSeek仅用公共编号投影作分析输入，避免从私有目录增加姓名到公共摘要。

## 本地运行和账号初始化

在`backend/`执行`uv sync`；给`YANXU_DATA_DIR`指定独立持久目录，先启动API，再按身份CLI从标准输入建立管理员，无内置密码。生产目录不能用测试数据覆盖。

```sh
uv run python -m yanxu.identity --username admin --name 管理员 --password-stdin
uv run uvicorn yanxu.api:create_app --factory --host 127.0.0.1 --port 5197
uv run python -m yanxu.worker
uv run python -m yanxu.voice.worker
```

首行只读取标准输入的密码；可由交互终端/密码管理器管道提供，避免将密码写进命令历史。各进程须读取同一`YANXU_DATA_DIR`。前端在`frontend/`运行`npm run build`后，公共页`/`，账号工作台`/account.html`。

独立声音运行时见[模型安装与约束](../../tools/voice-runtime/README.md)。把`YANXU_VOICE_ENGINE_COMMAND`设为该运行器的绝对路径；含空格的路径需在值内保留命令参数引号。默认阈值0.75、第一/第二候选相似度差0.08，属于待真人校准的相似度规则，不是置信概率。

新增管理模块：人员可以没有登录账号；角色为权限集合；部门用于目录；声音页查看、试听、登记和撤回。第一版为单组织。真实工作台和原`/speaker-prototype.html`数据完全独立。

## 当前权限和数据边界

- 新App录音由已登录且拥有`record`权限的账号创建；名单在开始录音时固定，上传时由服务端校验并保留姓名快照。会中追加、跨组织和扫码未进入本轮。
- 录音上传幂等键按账号隔离。换账号或换服务不能接走原队列；原账号恢复后才重试。旧匿名API保留兼容，但拒绝人员字段和读取受控上传凭证。
- 受控记录仅创建者、具有账号的参会人、拥有全部管理权限的管理员可读；登录本身不代表有权读取全部实名记录。公共接口只返回编号标签和原有公开资料，`personId`、声音登记ID、向量、候选相似度、私有名单不返回。
- 该规则保护的是发言人身份标签。用户已经允许公开原音和逐字内容；发言者口述的姓名可能仍在原音/正文/摘要中，不提供整份资料匿名化承诺。
- 每次云端登记须确认当前姓名、本人声音、云端保存。旧本机同意只允许本机保存，不批量上传，不按同名自动关联。撤回立即停止私有回听/后续使用，旧逐字稿不再通过该声纹显示姓名；原始会议文本不改写。
- 声纹音频默认在服务器`private-voices`（目录700、文件600），只经鉴权接口返回。可选七牛镜像每次上传核验独立空间为private；本轮没有创建或使用新的生产七牛空间。
- SQLite新增`feature_schema`分别管理core、identity、voice版本；旧录音、上传令牌和ASR结果保留。备份、ASR、声音机器凭证分别配置；ASR凭证不再能下载整个数据库。

## 生产切换与回退

以下为发布准备，尚未执行：从验证后的`release`提交构建前端/APK，备份线上SQLite、配置、原音和新增私有目录；先在副本验证迁移。配置独立备份/声音凭证后再切换API，沿用现有Mac远程ASR并增加`python -m yanxu.voice.remote_worker`，声音权重仍只在Mac。云端保留API、分析和存储，不增加模型内存负担。

HTTPS配置新增私有音频入口16MiB请求上限，其他上传仍按原分片限制。发布前在目标主机执行nginx配置校验，验证私有接口未登录拒绝、旧公共记录/音频可读、真实App登录及登记；最后再发布0.3.0更新清单。APK保持现有包名和签名，未把本地测试包推给现有用户。

回退先停止接收新的受控写入并备份新增数据；保留新库/私有样本，使用已验证副本恢复旧服务，不直接让旧版程序写升级后的生产库。新身份和声音数据不会因回退业务界面而自动丢弃。生产初始化管理员密码、迁移/重启、Git合并推送和APK发布均需按项目发布授权操作。

## 验证记录

在.local-data/evidence/identity-voice下记录每段测试、环境、截图和未闭环项。已有原型与Android 0.2.0改动同属本任务，保留，不提交无关内容，不修改实际数据库或发布目录直到验证和授权明确。

- 后端：身份、云登记/撤回、越权、任务租约、managed录音、旧匿名流水线、预算和恢复综合测试。独立审查已发现并修复仅有users权限即可读取全部实名会议、7天缓存提前删待处理managed原音两处问题；声音快照A→B→A重排、严格256维向量和在途角色撤回三处独立复现也已修复，新增回归通过。
- 真实模型：31.591375秒离线合成双人音频走真实HTTP上传、Qwen本机转写、WeSpeaker归属与DeepSeek分析，最终complete。6个ASR片段，A/B各两段具名，两段跨人保留未识别；同一公共接口仅编号且没有personId。原ASR文本/时间未改写。原始首轮短窗漏绑与通用聚类修复证据分别保留。
- Android：0.3.0/code10覆盖安装到专用`emulator-5560`；Keystore/服务账号隔离、旧样本显式迁移、姓名及云同意、受保护上传、成员新增/全选、原生实名结果与匿名公共WebView分别验证。真实麦克风未开启，模拟器host mic关闭。旧目录两组音频和meta保留；本轮没有覆盖安装前有效SHA基线，不能声称已做跨安装哈希比对。
- Web：实际同源HTTP登录、用户/角色/部门/声纹、公共编号/受控实名、私有样本操作和退出，桌面/平板/手机截图；等待/失败文案另用明确标识的响应模拟验证，不把该用例当真实模型失败证据。
- 导航和图谱：新增专题可从AGENTS一跳定位，模型运行器二跳定位；文档链接检查。GitNexus刷新与diff影响检查覆盖共享入口；动态回调/新文件映射缺口用源码、跨模块API测试和独立审查补充。

本轮仅隔离本机API `127.0.0.1:5197`，数据`.local-data/identity-voice-server`，既有5189/生产库未迁移。首个测试管理员凭据在`.local-data/evidence/identity-voice/credentials.json`（600，不入Git），仅用于本地演示；初始化业务管理员请按上方CLI独立创建。

尚未验收：真实同事识别准确率、重叠/远距离/长会议、物理手机与平板持续运行、真实七牛私有空间、生产迁移/HTTPS新配置和自动更新发布。该限制不会由构建、模拟器或合成声音结果自动消除。


### 最终结果与恢复入口

- `backend-final-tests.txt`：全后端 **93 passed**；`voice-security-review.md`记录新增缺陷的先失败再修复证据。
- 前端类型/构建通过；已有Vitest **30 passed**；`web-e2e-final.txt` **9 passed**（8真实API，1明确模拟状态）。
- Android最新存储＋7采样、9录入UI、5人员面板、cloudchecks及真实cloudapi全部通过；最终签名/版本与恢复状态在`android-artifact.json`、`android-final-state.json`。
- 重启加载最终代码后，`runtime-final.json`再次验证公共编号/受控姓名、仅users权限不能读他人记录、私有接口401与no-store。
- 文档检查：34导航文档、276本地链接、11路由用例通过；`git diff --check`通过。最终图谱刷新见`gitnexus-final-index.txt`。

本地服务保持运行：API PID 30088／session 72618，声音worker PID 33523／session 57597，ASR及分析worker PID 33593／session 3129。工作目录为项目根，启动辅助位于被忽略的`.local-data/evidence/identity-voice/server.py`和`local_worker.py`，日志同目录`local-voice-worker.log`、`local-recording-worker.log`。这些是本轮恢复线索，PID需再次核验；正式启动使用上方受版本管理的模块入口。DeepSeek只调用用户已配置的分析服务；本轮模型证据使用新增合成素材。

测试安装包为`.local-data/artifacts/yanxu-0.3.0-identity-voice-debug.apk`，0.3.0/code10，与0.2.0签名一致；SHA256 `5cfc3d19edacfef135dcf5b0434bbcb8de7393ae23df266567bad4a245e13c30`。模拟器已退出本地测试账号并恢复生产地址，生产后端未切换前不会假装登录成功。

本轮没有Git提交/推送、生产数据迁移、线上服务重启或APK自动更新清单发布。功能分支仍为`feat/speaker-enrollment-prototype`，同任务既有原型/本机App改动一并保留。


## 2026-09-22 发布授权与准备

用户已确认将本版提交、合入并推送release，部署阿里云并发布Android更新。本轮在既有阿里云Workbench会话执行，保留原其他业务和实例配置。

发布审查补齐了私有声音的异机备份：`/internal/asr/backup-bundle`使用独立备份凭据，包含一致性SQLite、未撤回声音原件及完整性清单；ECS/Mac保留30份，Mac必须实际临时恢复验证后才保存。恢复入口`python -m yanxu.private_backup <包> --restore-to <新目录>`；总包2GiB、数据库512MiB，超限明确失败。旧SQLite备份接口兼容保留。该切片完成后全后端106项通过。

发布APK从同一源码强制重建，0.3.0/code10，签名与线上0.1.7一致；新包SHA256 `083d3de89184a142b0c40c658432426d3bfa66476e37d853c49c1f2b9eb8146b`，106272字节。与先前200133字节包的全部6个有效ZIP文件逐字节相同；外层重打包清除了增量ZIP空洞，发布清单以本次新包为准。

上线前实际服务器只读检查：原current为20260921-updates，7条记录（5 complete、2 no-speech），无在途处理；SQLite quick_check正常，磁盘可用33GiB、可用内存1047MiB。后续迁移前再次停写备份和副本校验，不把这份预检当最终迁移证据。
