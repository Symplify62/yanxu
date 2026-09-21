# STATE-01｜自动流程状态与业务身份 v1.3

本文件是当前状态语义唯一来源。U-11取消普通人工审核门槛，旧PENDING_REVIEW/Approval只存在历史包，不作为首版正常状态。

## 1. 身份和对象

Room、Device、DeviceCredential负责设备和归属配置；User/IdentityBinding/Department/Role/Grant/AccessGroup负责企业身份和人员范围。DeviceScanChallenge一次性且绑定设备/员工/有效期；EmployeeControlSession只控制本场，录音开始后冻结RecordingSession的initiator_user_id、department_id与room/device快照。

员工本地保存成功自动退出，但RecordingSession/AudioAsset/UploadSession/Job仍由设备或服务身份保全和推进。Meeting以(device_id,client_session_id)稳定去重，归属不使用姓名猜测，主部门变化不改历史。

TranscriptVersion、SummaryVersion、ActionItem保留来源版本和证据；自动生成版本立即按权限可见。PublicationSnapshot绑定指定内容/目标/策略/访问版本；DistributionJob和Attempt保存外部状态，不再依赖逐场Approval对象。

## 2. 平板状态

扫码：WAIT_SCAN → AUTHENTICATING → SIGNED_IN；过期EXPIRED，停用/跨企业DENIED；挑战消费后不可复用。网络不可用不能新建扫码身份，本场已经开始的采集不因网络丢失停止。

采集：READY → STARTING → RECORDING ↔ PAUSED → FINALIZING → LOCAL_SAVED。故障进入INTERRUPTED/RECOVERY_REQUIRED。只有封存成功进入LOCAL_SAVED并清除员工控制会话；失败不伪称成功、不套用下一位人员。恢复不能无提示重开麦克风。

## 3. 上传、完整性与处理

上传：QUEUED/WAITING_NETWORK/UPLOADING/VERIFYING/RECEIVED_VERIFIED/RETRY_WAIT/AUTH_REQUIRED/CONFLICT/REJECTED/MANUAL_REQUIRED。上传100%不等于校验归档；收据绑定原场身份与清单。

完整性：UNKNOWN/COMPLETE/INCOMPLETE/CORRUPT。缺口/中断不能在补传后抹去。正常发布需要完整有效产物；不完整进入技术异常，保全和恢复由管理员处理。

转写/总结：BLOCKED_CONFIG/QUEUED/RUNNING/RETRY_WAIT/SUCCEEDED/FAILED/CANCELED，无有效语音NO_SPEECH。未知负责人/日期属于内容字段，不把整场置为待人核对。产物各自完成即可看，不等全部资料或人工操作。

## 4. 自动分发

UNCONFIGURED：缺路由/部署配置；BLOCKED：全局停发、撤权、删除、硬故障；READY：已冻结正常消息快照；SENDING：请求已提交；ACCEPTED：渠道已接收；FAILED_RETRYABLE/FAILED_FINAL：明确失败；UNKNOWN：可能成功无可靠响应，不盲重发；CANCELED：任务作废。

用户保存更正产生新内容版本，不修改旧快照、不自动创建第二个分发任务。用户只读共享也不产生群消息。管理员改变宽松规则默认仅影响新会议；历史待发的安全收紧要实时检查。

## 5. 时间、长录音与保留

绝对时间保存时区和可信度；持续/偏移为毫秒。长录音不设业务截止，片段清单保持顺序、暂停/缺口和原件关联；技术段不是新的会议，也不各段重复发群。最终总结覆盖整场，资源停止如实标中断。

公司四类档案长期保留；设备缓存只有归档/独立备份/批准策略满足才可清。主动删除和保留锁另走受控流程，恢复应用删除/撤销/去重记录。

## 6. 全链路不变量

INV-01 没有可恢复原件不显示已保存；INV-02 没有持久校验不显示已归档；INV-03 上游失败不删除原件；INV-04 同会话重复只有一场；INV-05 同键不同内容不覆盖；INV-06 错误不触发暗录；INV-07 未知目标/未批准服务不猜测放行；INV-08 AI不改变权限/群，人工更正不自动覆盖发送；INV-09 UNKNOWN不盲重发，ACCEPTED不等于已读；INV-10 恢复不复活已删/撤权也不重发已送达。

INV-11 本场员工身份不可串给下一场；INV-12 成功退出员工后设备任务继续；INV-13 正常自动闭环不存在人工核对前置；INV-14 共享不等于群发；INV-15 部门归属不等于全部门查看。
