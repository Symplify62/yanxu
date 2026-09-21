# DES-02｜数据对象与接口契约要求

性质：供下一步技术设计使用的契约需求，不是已实现OpenAPI，也不是Wave厂商协议。具体URL、字段类型、索引和错误码由开发方案冻结；下列语义不可丢失。

## 1. 对外接口组

| 接口组 | 必要输入与输出语义 | 关键约束 |
| --- | --- | --- |
| 一次性配对 | 管理员批准设备/会议室；返回设备身份和限制 | 过期/一次性、最小权限、可撤销 |
| 设备状态/配置 | 自身状态、配置版本、离线有效期 | 不返回其他会议正文和服务器秘密 |
| 创建上传会话 | 客户会话ID、采集快照、音频清单 | 按认证设备归属校验、幂等 |
| 片段上传/状态查询 | 上传范围、片段摘要、已接收范围 | 重复一致可接受、冲突不覆盖 |
| 完成与收据 | 完整清单/结束原因；返回稳定归档结果 | 完成校验后才确认，不等待AI |
| 会议列表/详情 | 筛选、分页、对象授权 | 列表/计数/搜索也鉴权 |
| 音频播放/导出 | 资产与版本、范围/格式 | 有效权限与短效访问，不裸公开 |
| 修订与重跑 | 来源版本、内容、更改理由 | 版本冲突明确返回，不静默覆盖 |
| 自动分发预演 | 会议/内容/目标/规则版本 | 冻结版本，预览无外发 |
| 发布/补发/更正 | 策略、目标、类型、动作幂等标识 | 禁止重复动作和绕过保密 |
| 管理配置/恢复 | 配置版本、预演范围、理由 | 权限及审计，秘密只写不回读 |

## 2. 字段与并发规范

使用不随名字变化的业务ID；客户端会话可离线生成，服务器绑定到认证设备。会议时间保留来源与可信度，时间位置用duration_ms/start_ms/end_ms及明确音频时间轴；未知值使用null而非0、空字符串或编造默认日期。

文件清单包含稳定片段ID、顺序、内容摘要、字节大小、编码说明、持续时间、缺口/暂停关系及源文件名（仅显示）。校验算法和编码由技术决策固定，必须在客户端/服务端一致验证。

变更请求携带内容/配置版本；拒绝过时编辑时返回当前版本和冲突信息。错误结构包含稳定业务错误码、是否可重试、相关对象/关联标识和安全提示，不返回密钥、栈或内部存储路径。

## 3. 发布前必须交付的技术契约

版本化OpenAPI或等价说明、设备认证方案、请求/响应样例、错误码、上传状态与重试规则、文件/JSON样例、分页/排序、权限矩阵、日期单位、最大体积和超时、幂等/冲突规则、版本兼容策略。每个P0外部入口至少有正向和权限/故障契约测试。

本包不伪造具体已存在端点。Codex可以在获批技术路线内设计这些接口并实现，但必须让需求/用例追踪到契约版本。API返回成功不能绕过PRD“持久校验成功”的业务定义。

## 4. 事件与业务数据

事件包含event_id、对象/版本、发生时间、来源环境、test_flag、关联ID和必要状态；不把全文或凭证塞入每个状态事件。监听者按事件ID和业务对象去重，不依赖只送一次。设备离线状态的事件晚到需核对版本/时间，不能逆转新状态。

数据模型应有录音会话、音频清单、会议、内容版本、行动事项、处理任务/尝试、分发计划/尝试、自动发布快照、用户/业务组/对象授权、设备配置、审计与删除保留记录。物理表可合并，业务关系不能省略。

## 5. v1.1 身份管理契约补充

需新增企业微信回调/首次开户/退出/会话撤销，用户生命周期，部门树/依赖，角色权限目录，成员维护，授权预览/提交/撤销，有效权限解释，交接与审计查询接口。身份源已确定企业微信；凭证方案与具体回调URL待接入设计；不得复用设备令牌登录后台。

授权提交携带版本、主体、角色、范围、时间/历史边界、原因及预览引用；服务端重新计算委派资格与影响，不相信浏览器传入的可授权清单。对重复账号、循环部门、最后管理员、过期编辑、越权委派提供可理解的错误。管理列表与权限解释自身也需范围过滤。

分别验证：全公司只读＋销售编辑不允许编辑财务；组加入/角色修改不能自提权；停用后旧会话/音频请求拒绝；恢复不复活撤销资格。

## 6. v1.2 接口协议草案

以下路径/结构是建议的首版契约，用于前后端/安卓共同评审，未实现、未部署、未生成正式OpenAPI。冻结项为T-05；以后修改须同步客户端与契约测试。前缀建议/api/v1；公用设备入口/device与用户入口分开认证；维护动作不能接受设备令牌。

通用：JSON使用UTF-8；ID为不透明字符串；绝对时间为带偏移ISO格式，时间偏移/持续统一整数毫秒；版本为整数。请求以request_id关联日志，业务变更携带expected_version；可重复提交的创建/发布携带Idempotency-Key。键按身份＋用例＋业务对象作用域绑定请求指纹，同键不同内容返回冲突，不用请求ID代替业务幂等。

建议读写响应：成功含data、request_id；失败含error.code、message、field_errors、retryable、request_id，不包含堆栈/秘密。允许HTTP状态与业务码同时表达结果，禁止把全部错误包装成200。创建返回201，已存在的幂等结果返回200；异步受理202只是排队，不是完成。

| HTTP/业务码建议 | 客户端处理 | 服务端约束 |
| --- | --- | --- |
| 401 AUTH_REQUIRED/SESSION_EXPIRED | 重新认证；设备保留待传原件 | 不自动注册或改用管理员身份 |
| 403 ACTION_FORBIDDEN | 显示无操作资格 | 内容不存在/无权详情建议统一404，避免枚举 |
| 404 RESOURCE_UNAVAILABLE | 不披露标题/存在性 | 不能回传隐藏对象元数据 |
| 409 VERSION_CONFLICT | 保留编辑内容，重新核对 | 不无提示覆盖 |
| 409 CONTENT_CONFLICT/IDEMPOTENCY_CONFLICT | 隔离或核对原请求 | 不覆盖旧原件或重复创建 |
| 413 LIMIT_EXCEEDED / 422 INVALID_INPUT | 指出安全可显示字段问题 | 不无限重试 |
| 429 RATE_LIMITED | 按Retry-After和上限退避 | 请求量与单设备资源受控 |
| 503 SERVICE_UNAVAILABLE | 显示可恢复故障 | POST需按幂等/结果查询恢复 |

## 7. 身份与管理接口草案

| 方法与路径 | 关键输入/输出 | 权限/一致性 |
| --- | --- | --- |
| GET /session | 身份、会话状态、功能能力摘要 | 不携带未授权会议列表 |
| POST /session、DELETE /session | 企业微信认证结果换取本系统会话；退出 | 不为普通员工另设密码；身份验证、限速、CSRF与撤销见DES-09 |
| GET/POST /users；PATCH /users/{id} | 分页用户；维护已验证企业身份/自动开户记录；expected_version | user.manage；账号唯一、保护最后管理员 |
| POST /users/{id}/disable | 原因、expected_version | 撤销会话；非删除历史 |
| GET/POST /departments；PATCH /departments/{id} | 部门树、负责人、parent、version | 循环/依赖/变更影响校验 |
| GET/POST /roles；PATCH /roles/{id} | 固定权限码数组、version | role.manage＋受影响范围委派检查 |
| GET/POST /groups；PUT /groups/{id}/members | 成员数组、version、原因 | group.manage＋关联授权影响 |
| POST /grants/preview | 主体、角色、范围、时间与历史边界 | 返回可授权判定、影响和preview_version，无写业务授权 |
| POST /grants；POST /grants/{id}/revoke | 上述字段、原因、expected_version | grant.manage；提交重算委派资格、记录审计 |
| POST /access/explain | 主体、动作、对象引用 | 解释接口自身受控；不能枚举秘密会议 |

批量导入、密码重置、交接接口在对应功能切片前补正式契约，行为已在PRD-07定义；不能据此声称当前表已覆盖所有API。身份源外部回调路径由T-07及实际提供方协议确定。

## 8. 设备和上传接口草案

| 方法与路径 | 输入/输出语义 | 约束 |
| --- | --- | --- |
| POST /device-pairings | 管理员选room，生成一次性短期配对信息 | 人员认证；已用/过期不可重用 |
| POST /device/pair | 一次性配对信息、设备描述→设备凭证与配置 | 无通用匿名设备注册；限速，返回最小凭证 |
| GET /device/config | 配置版本、离线有效期、采集限制 | 仅自身配置；不下发AI/群秘密 |
| POST /device/heartbeat | 实际采集/存储/队列/版本、观测时间 | 最近上报不等于永远在线 |
| POST /device/uploads | client_session_id、清单摘要、采集快照→upload_id | 由认证设备与会话去重，服务端校验room |
| PUT /device/uploads/{upload_id}/assets/{asset_id}/parts/{part_no} | 二进制、字节大小、分片摘要 | 同键同摘要返回原结果；不同摘要冲突 |
| GET /device/uploads/{upload_id} | 已确认/缺失/冲突片段、状态 | 只查自身；重启/响应丢失后恢复 |
| POST /device/uploads/{upload_id}/complete | manifest_bytes或清单引用、摘要、结束原因 | 校验和归档异步时202＋查询入口，完成后稳定收据 |
| GET /device/uploads/{upload_id}/receipt | 原会议ID、manifest_hash、完整性、接收时间 | 仅RECEIVED_VERIFIED返回最终收据 |

分片大小由服务端配置协商、写入上传会话，不能中途无版本变更自行改变。清单包含原音频资产列表，每资产有顺序、大小、摘要、编码、实际时长以及暂停/缺口映射。建议摘要为SHA-256。manifest_hash针对实际上传的UTF-8清单字节计算，各端不独立重序列化后比较；清单schema版本固定并明确最大条目数。

同设备同client_session_id重复创建返回同upload_id/meeting_id；同身份但清单摘要不同返回CONTENT_CONFLICT。上传百分比100%仅表示字节已传输，界面继续显示校验中；不得先收到202就清理本地唯一原件。

示例：下列字段与值为合成建议，展示收到稳定收据后的结构，不表示已有服务器。

```json
{
  "data": {
    "receipt_id": "receipt_demo_001",
    "meeting_id": "meeting_demo_001",
    "client_session_id": "0ed840be-028c-4b99-91e8-9862c8407d40",
    "status": "RECEIVED_VERIFIED",
    "integrity_status": "COMPLETE",
    "manifest_hash": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "received_at": "2026-09-20T10:00:00Z"
  },
  "request_id": "request_demo_001"
}
```

## 9. 会议与分发接口草案

| 方法与路径 | 关键语义 | 约束 |
| --- | --- | --- |
| GET /meetings | 时间/room/状态/关键词、分页与稳定排序 | 授权过滤后再分页/计数；游标不能扩大范围 |
| GET /meetings/{id} | 元数据、四类资料引用、独立状态和版本 | 当前对象权限；无权和不存在一致反馈 |
| GET /meetings/{id}/transcripts/{version}/segments | 分页片段、时间轴、下一游标 | 绑定来源版本；中文搜索不泄露其他对象 |
| GET /assets/{id}/content | 受控流/Range | 每次授权；返回媒体字节，非普通JSON包裹 |
| POST /meetings/{id}/revisions | base_version、正文/事项、理由 | 返回新版本；不自动发布 |
| POST /meetings/{id}/processing-runs | 指定输入版本、模板/服务、原因 | 当前数据策略和预算；显式重跑新generation |
| POST /meetings/{id}/distribution-preview | 内容版本、目标、规则、访问版本 | 只预演，给出阻断原因 |
| 内部事件 content.initial-ready | 冻结首次内容/目标/策略/访问版本 | 自动创建发布；不是给员工调用的审批端点 |
| POST /meetings/{id}/publications | 有效自动策略与冻结快照、publish_id、动作幂等键 | 排队不代表渠道成功；执行前重查 |
| GET /meetings/{id}/distributions | 各目标状态、快照版本、尝试摘要 | 不返回完整Webhook或敏感日志 |
| POST /distributions/{id}/resolve | 人工核对结果/依据、期望版本 | UNKNOWN专用处理，不伪造渠道回执 |

会议归属确认、删除/保留锁、单场导出、配置/恢复等接口按其PRD在切片前补齐；不允许用通用PATCH任意改状态绕过专门用例。自动发布必须固定内容/目标/策略/访问版本；后续编辑不能悄悄改旧发送快照。

## 10. 契约冻结与验证

T-05完成前产出版本化OpenAPI或等价机器可读契约、类型生成方式、请求/响应与错误样例、上传边界参数、老版本兼容策略。当前Markdown草案用于设计对齐，不冒充可执行OpenAPI。

至少用合成样本验证：同会话重复上传、同键不同内容冲突、响应丢失查回原收据、未知/越权ID、过期会话、409版本冲突、范围/字节单位错误、部分接收、超限、手机登录回跳。业务状态枚举引用STATE-01，不能因实现方便删掉UNKNOWN/INCOMPLETE等语义。

## 11. v1.3 本系统扫码绑定契约草案

设备请求创建本系统scan_challenge（绑定device、有效期、随机nonce）；手机通过已验证的企业微信身份确认该挑战；服务端一次性消费后，设备取得仅本场使用的employee_control_session和允许部门列表。开始时冻结采集绑定，结束保存后撤销控制会话。员工注销不撤销设备补传原场数据的资格。

本系统建议端点：POST /device/scan-challenges、GET /device/scan-challenges/{id}、POST /scan-challenges/{id}/confirm、POST /device/recording-bindings、DELETE /device/employee-session。所有调用核对身份、设备、有效期和消费状态；外部企业微信认证接口由官方能力核实后接入，这些路径不是企业微信现有API。
