# DES-08｜数据模型与一致性设计

版本1.3-draft；以下为逻辑模型和建议字段，不是已执行SQL。关系型数据库产品与物理类型待T-01/T-05。正式迁移需另行实现验证。

## 1. 基本约定

ID为稳定不透明标识，接口统一字符串；设备离线会话建议UUID并结合认证device_id唯一约束。时间点用UTC存储、带偏移格式传输，展示用会议时区；持续/偏移统一整数毫秒。缺失日期/人员映射使用null。名字可改，关系不使用姓名作键。

可并发编辑记录带version；重要状态变更保留updated_at和关联事件。正文版本、授权变更和发布快照不可通过普通覆盖丢失历史。单公司不硬编码业务room或群，但不预建商业多租户计费模型。

## 2. 身份与组织实体

| 实体 | 关键字段建议 | 关系/约束 |
| --- | --- | --- |
| User | id, account_key, display_name, primary_department_id, status, auth_version, version | account_key按批准规范化后唯一；停用不删除历史引用 |
| IdentityBinding | id, user_id, provider, issuer, external_subject, status | (provider,issuer,external_subject)唯一；不按同名自动合并 |
| Department | id,parent_id,name,owner_user_id,status,version | 根节点受保护；祖先循环在事务校验；停用先处理依赖 |
| Role / RolePermission | role_id,name,protected,version / permission_code | 权限码来自固定目录；保护角色普通编辑禁止 |
| AccessGroup / Membership | group_id,name,version / user_id,valid_from,valid_until | 成员变化保留历史；历史访问由grant边界另约束 |
| Grant | id,subject_type/id,role_id,scope_type/id,valid_from/until,history_mode,history_from,version,revoked_at,delegation_ref | 每条独立绑定角色和范围；撤销记录保留 |
| Delegation | id,subject_id,allowed_permission_set,allowed_scope,valid_until,version | “本人可操作”不等于“可授予他人”；不能递归无限委派 |
| Session | id,user_id,auth_version,expires_at,revoked_at | 只存令牌摘要/会话标识；账号停用使所有旧会话失效 |

历史边界草案：授权有效期判断请求时是否可用；history_mode决定匹配哪些会议，建议EXPLICIT_OBJECT、FROM_TIME、ALL_IN_SCOPE三类；FROM_TIME使用稳定会议采集时刻，不能用每次查询的当前时间。设备时间不可信时归属/历史范围待核对，不悄悄改成上传时间放权。群成员新加入的历史政策D-18必须明确后配置。

## 3. 录音与资产实体

| 实体 | 关键字段建议 | 关系/约束 |
| --- | --- | --- |
| Room | id,name,status,default_policy_version | 改名保留采集快照；缺策略不扩权限 |
| Device / DeviceCredential | device_id,room_id,status,config_version / key_id,digest,expires_at,revoked_at | 凭证作用域独立；轮换/撤销可审计 |
| RecordingSession | id,device_id,client_session_id,start/end,timezone,clock_trust,end_reason,manifest_hash | UNIQUE(device_id,client_session_id)；记录中断与暂停 |
| UploadSession / UploadPart | upload_id,session_id,status,version / asset_id,part_no,byte_count,sha256 | UNIQUE(upload_id,asset_id,part_no)；同键不同摘要冲突 |
| Asset | id,session_id,kind,storage_key,size,sha256,codec,duration_ms,status,parent_asset_id | storage_key私有；原件不可变，转码另建派生件 |
| AudioManifest | session_id,version,ordered_asset_ids,pause_map,gap_map,hash | 清单封存后不可同版本改内容 |
| Receipt | id,session_id,meeting_id,manifest_hash,received_at,status | 稳定收据；绑定同会话同清单；不隐含备份完成 |
| Meeting | id,session_id,title,room_snapshot,department_id,owner_user_id,initiator_user_id,scan_session_id,ownership_status,integrity_status,classification,version,deleted_at | session_id唯一；扫码绑定的发起人不能被后续认领或调岗改写 |

文件与数据库提交边界见DES-07；对象存储路径不能由上传文件名拼接。内容摘要算法草案为SHA-256，正式固定前在T-05确认双方一致。

## 4. 内容、任务与自动分发实体

| 实体 | 关键字段建议 | 重要约束 |
| --- | --- | --- |
| TranscriptVersion / Segment | meeting_id,version,source_manifest_hash,kind / segment_id,start_ms,end_ms,text,speaker_label | 段落指向具体版本；说话人仅在本会议有效 |
| SummaryVersion | id,meeting_id,source_transcript_version,kind,body,coverage,author_id,reason,created_at | 原始/人工/确认版本分别保留；当前版本引用显式更新 |
| ActionItemVersion | summary_version_id,text,owner_text,owner_user_id,due_text,due_at,evidence_refs,confirmation_status | 空值保留；整理状态不等于执行完成 |
| ProcessingJob / Attempt | 输入指纹、配置版本、状态、租约 / external_request_id,outcome,usage,error | 任务重试不创造新的逻辑内容版本；不确定外部结果保留 |
| PublicationSnapshot | content_version,target_set_hash,policy_version,access_version,initiator_user_id,generated_at | 自动冻结指定版本与配置，无逐场审批；编辑不改快照 |
| DistributionJob / Attempt | meeting_id,content_version,target_id,publish_id,type,status,payload_snapshot / request_id,result | UNIQUE(meeting_id,content_version,target_id,publish_id,type)；已发快照不变 |
| Outbox / ConsumedEvent | event_id,type,payload_ref,created_at / consumer,event_id | 消费键唯一；事件引用对象，不复制全正文 |
| AuditEvent | actor_type/id,action,object_ref,reason,before/after_ref,request_id,time | 访问需权限；不写秘密或无必要正文 |
| RetentionLock / Tombstone | object_id,reason,expires_at / object_id,deleted_at,scope | 恢复旧备份先应用撤销/删除/去重信息 |

## 5. 索引与授权查询

候选索引：Meeting(room_id,started_at,id)、Meeting(department_id,started_at,id)、Grant(subject_type,subject_id,revoked_at)、Membership(user_id,group_id)、Job(status,next_run_at)、Audit(object_ref,time)。实际命名和字段映射在物理设计确定；不能把索引存在当作性能验收。

查询必须在授权范围内筛选后再分页/计数。建议首期关系库检索与统一范围过滤，是否独立全文索引由T-05验证；若使用外部索引，同步权限版本、删除标记和最终回源校验，禁止只过滤页面上展示的结果。

列表稳定排序建议started_at、id组合；时间过滤明确边界和时区。搜索命中、计数、建议词和导出均复用授权查询。

## 6. 迁移、保留与恢复

每次schema变更有版本化迁移、测试数据和回退判断。先向后兼容扩展字段，再切换读写，最后经批准删除旧结构；不能让新App上传旧服务无法理解且无错误说明的清单。

业务删除用受控流程，不能用级联删除清掉必要审计/撤销/发送去重。账号停用不级联删除会议。备份同时包含数据库、资产清单、密钥恢复材料、撤销与删除清单；恢复验证参见DEL-02和ACC-02。

## 7. 完成条件

交付逻辑实体图或等价关系表、数据字典、约束/索引、迁移脚本、测试seed、权限查询和故障数据验证。落实唯一会话、分片冲突、版本竞争、删除恢复和历史边界测试后才能宣称数据模型可用。
