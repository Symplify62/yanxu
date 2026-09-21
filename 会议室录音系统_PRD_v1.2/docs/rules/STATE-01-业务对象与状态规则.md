# STATE-01｜业务对象与状态规则

本文件是所有模块的状态、身份、时间和版本唯一口径；接口枚举可在技术设计中映射，但不得改变含义。

## 1. 业务对象和关联

| 对象 | 业务身份及关系 | 不变量 |
| --- | --- | --- |
| 会议室 Room | 首期一个，未来可新增 | 名称可变，稳定身份不变 |
| 设备 Device | 属于公司，带授权和配对历史 | 设备标识不是普通人的账号 |
| 会议 Meeting | 汇总标题、采集、资料、策略和授权 | 标题或部门不作为唯一身份 |
| 录音会话 RecordingSession | 设备离线创建，首期一次开始到结束对应一场会议 | 设备＋会话标识唯一，人工恢复不覆盖 |
| 音频资产/片段 AudioAsset | 原始片段清单、派生播放件、校验信息 | 原件封存后不被无痕改写 |
| 转写版本 TranscriptVersion | 对指定音频清单产生 | 源指纹、段落标识和时间单位明确 |
| 纪要版本 SummaryVersion | 对指定转写版本产生/修订 | 原版、人工版分别保留 |
| 行动事项 ActionItem | 引用明确转写/纪要版本和证据 | 负责人未知保留空，不凭声纹猜人 |
| 处理任务 ProcessingJob | 绑定输入、服务、模板版本和尝试记录 | 新版本与同任务重试不同 |
| 审核 Approval | 绑定内容、目标和策略版本 | 任一重要项变更使原批准失效 |
| 分发任务 DistributionJob | 会议＋内容版本＋目标＋发送类型 | 外部成功状态不等于已读 |
| 访问策略/业务组 | 与角色共同决定内容权限 | 群目标和访问组分别维护 |
| 审计/保留锁/删除标记 | 生命周期与操作证据 | 删除正文不等于抹去必要审计 |

首期不提供任意合并/拆分会议的复杂编辑。多片段是一场录音的技术组织，不因为分段就多发群。异常后人工再次录音默认新会话，可标关联，不悄悄掩盖中断。

## 2. 时间与字段语义

持久时间采用有时区含义的时间点，展示使用会议室已批准时区。保留 device_started_at、device_ended_at、server_received_at、设备时钟偏差/可信状态。录音实际时长来自音频和单调时钟，不由可能跳变的墙上时间相减决定。

全文定位统一使用相对录音有效时间的毫秒整数；暂停区间另存墙上时间映射，异常缺口独立表示。没有可靠偏移的外部结果要对齐或标记不可精确定位，不编造。相对日期转换保留原句、采用的会议日期/时区和人工确认状态。

关键字段最小字典：room_id、device_id、client_session_id、meeting_id、capture_config_version、content_access_policy_version、distribution_policy_version、audio_manifest_hash、source_asset_id、duration_ms、coverage、transcript_version_id、summary_version_id、action_id、evidence_segment_ids、owner_text、owner_user_id(可空)、due_text、due_at(可空)、approval_id、distribution_job_id、target_id、attempt_id、test_flag、integrity_status。字段类型和API路径在DES-02冻结，不来自Wave。

## 3. 采集状态

| 状态 | 进入条件 | 允许动作和后续 |
| --- | --- | --- |
| READY | 配置/权限/空间预检满足 | 人工开始；不自动开录 |
| STARTING | 用户开始，创建本地会话 | 成功进入RECORDING；失败回就绪并记失败 |
| RECORDING | 已确认采集与写入 | 暂停、结束；故障进入INTERRUPTED |
| PAUSED | 停止采音并记录暂停点 | 人工继续或结束 |
| FINALIZING | 人工结束，收尾封存 | 成功LOCAL_SAVED；失败RECOVERY_REQUIRED |
| LOCAL_SAVED | 可恢复本地记录完成 | 自动上传排队；不可等同服务器接收 |
| INTERRUPTED | 被强停、断电或采集错误 | 保护片段、记录缺口；恢复不能自动新录 |
| RECOVERY_REQUIRED | 文件收尾/清单不完整 | 管理员恢复、隔离；不能显示完整成功 |

“暂停”不是“设备静音状态”的同义词；暂停不保存新的环境音。NORMAL_END 与 INTERRUPTED 是结束原因，不能在补传后清空异常标志。

## 4. 上传与完整性状态

上传：QUEUED → UPLOADING → VERIFYING → RECEIVED_VERIFIED。网络问题为WAITING_NETWORK，明确可重试为RETRY_WAIT，授权问题为AUTH_REQUIRED，内容冲突为CONFLICT，非法输入为REJECTED，放弃自动尝试为MANUAL_REQUIRED。重试和乱序回调不得将已校验状态回退为普通待传。

完整性独立：UNKNOWN、COMPLETE、INCOMPLETE、CORRUPT。服务端可以保存不完整恢复资料，但“完整接收收据”只确认已声明且验证的清单；完整性仍标INCOMPLETE，不伪造整场无缺口。

## 5. 处理与审核状态

转写和总结各有：BLOCKED_CONFIG、QUEUED、RUNNING、RETRY_WAIT、SUCCEEDED、FAILED、CANCELED；明确无可识别语音为NO_SPEECH，不等于有完整纪要。任务实例重试不创造多个逻辑版本；显式重跑可以产生新版本。

审核：NOT_REQUIRED、PENDING、APPROVED、CHANGES_REQUESTED、INVALIDATED。内容版本、目标、访问范围或重要策略变更使对应批准失效。过时结果可以留档但不能替换已确认版本。

行动事项整理状态：UNCONFIRMED、CONFIRMED、DISMISSED。它们不是任务执行的待办/完成状态，首期不承担自动派单/催办。

## 6. 分发状态与最终结果

| 状态 | 含义 | 禁止混淆 |
| --- | --- | --- |
| UNCONFIGURED | 无有效批准规则或目标 | 不等于发送失败，也不找旧群补发 |
| BLOCKED | 全局停发/保密/删除/质量约束 | 不通过一般重试绕过 |
| PENDING_REVIEW | 指定版本等待审核 | 不是已经排队发送 |
| READY | 条件满足，未提交外部 | 发送前再检查安全收紧 |
| SENDING | 请求正在执行 | 未得到结果不能显示成功 |
| ACCEPTED | 渠道明确返回已接收 | 不表示管理者已读或全文可达 |
| FAILED_RETRYABLE | 明确未成功，可有界重试 | 不与未知结果混淆 |
| FAILED_FINAL | 永久失败/次数用尽 | 原件不删，管理员处理 |
| UNKNOWN | 请求可能成功但无可靠响应 | 默认不盲重发；需确认重复风险 |
| CANCELED | 被版本变更/权限/删除取消 | 不再执行旧任务 |

单次会议多目标只要有一个未成功，汇总显示部分完成，并保留每目标详情。用户主动更正发布创建独立发送类型/发布号，旧发送快照不改。

## 7. 路由、版本和即时安全检查

开始录音时缓存采集配置与默认业务元数据。服务端首次接收时决定并保存处理/访问/分发计划，记录实际采用的配置版本；离线旧配置不能自行扩大外发。

发送计划使用已保存规则快照，不因新规则发布就改变既有目标；但全局停发、删除、访问收紧、目标禁用、本场保密和外部处理禁用必须使用当前状态拦截。扩大权限或改群不得自动应用旧会议，需显式重评并重新审核。

路由顺序：①环境与全局门禁；②删除/保留操作和本场禁发；③目标访问/受众约束；④异常或低质量需要审核；⑤按明确优先级匹配房间/类型/部门规则；⑥无匹配或同级冲突阻断；⑦生成消息快照及审核；⑧发送前重查①至③和版本有效性。管理员可预演解释，不执行外部动作。

若用户在外部请求已经提交后收紧策略，只能阻止后续请求、取消未发目标并记录已披露，不能承诺原子撤回第三方消息。

## 8. 十条跨模块不变量

INV-01：没有可恢复的本地文件/记录，不显示已保存。

INV-02：未完成服务端持久校验，不显示已归档。

INV-03：上游失败不抹去已经安全保存的原件。

INV-04：同一会话重复请求只建立一个逻辑会议。

INV-05：相同标识不同内容不覆盖；不完整不得伪装完整。

INV-06：任何网络/AI失败不触发隐蔽录音或自动删唯一副本。

INV-07：未知目标、未知权限、未批准外部服务都不能猜测放行。

INV-08：AI不能改变路由/权限；转写版本变化不覆盖已审核发布快照。

INV-09：发送UNKNOWN不无界重发；ACCEPTED不等于已读。

INV-10：恢复必须带权限、删除和发送去重信息，不能复活已删或重新群发。

## 9. v1.1 身份与授权对象

新增用户 User（稳定标识、主部门、启用/停用）、外部身份 IdentityBinding（来源＋不可变外部主体标识）、部门 Department（父级、负责人、启用/停用）、角色 Role、固定权限 Permission、角色权限 RolePermission、业务组 AccessGroup 与成员 GroupMembership、授权 Grant（主体＋角色＋范围＋生效/失效＋历史边界＋委派来源）、会话 Session、交接 Handover。

Grant 的范围与角色不可分离混算；记录版本和撤销时间。改名不改身份；用户停用不删除会议；组织改名不改历史快照。会议追加归属状态 UNCONFIRMED/CONFIRMED、负责人和归属来源，匿名录制保留 initiator_user_id 为空，后续认领另记 claimed_by/claimed_at，不回填虚假发起人。
