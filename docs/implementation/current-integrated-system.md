# 当前整合版本说明

日期：2026-10-11

本地目录 `D:\yanxu` 当前作为整合后的工作版本使用。它保留了第一阶段原始系统中的 Android 录音、上传、后端转写队列、DeepSeek 分析、公共记录页和音频回听下载能力，并在公共记录链路上新增了会议纪要相关能力。

## 已保留的原始系统能力

- Android 原生录音、暂停、继续、结束、本地文件保留和分片上传。
- 后端上传协议、SQLite 持久化、任务队列、ASR 阶段、DeepSeek 分析阶段。
- 本地 ASR 入口 `backend/local_asr`，后端 worker 入口 `yanxu.worker`。
- 远程 ASR worker、七牛云录音同步、Android 自动更新分发接口。
- 公共记录列表、详情、逐字稿、AI 分析、行动事项、原始音频回听和下载。

## 新增整合能力

- 文本文档导入：无需音频，可把已有逐字稿或会议文字创建为公共记录。
- DeepSeek 个性化纪要：按用户选择的板块生成纪要。
- 后端纪要模板接口：保存、更新、删除自定义模板。
- 公共页模板管理：在真实公共页管理可复用纪要模板。
- 详情页模板选择：读取后端模板，套用后可临时增删板块和调整顺序。
- 已归档纪要展示：历史归档卡片支持查看、复制和导出。
- 测试样本文档库：内置技术评审、项目周会、客户沟通、研发复盘、风险评审样本。
- Markdown 导出：当前纪要和已归档纪要都可以导出为 `.md` 文件。

## 关键入口

- 公共记录页：`http://127.0.0.1:5189/public.html`
- 模板管理页：`http://127.0.0.1:5189/public.html#/templates`
- 样本文档库：`http://127.0.0.1:5189/public.html#/samples`
- 文本导入页：`http://127.0.0.1:5189/public.html#/import`
- Android 测试包下载：`http://127.0.0.1:5189/app/yanxu-debug.apk`

## 本地运行

先构建前端：

```powershell
Set-Location D:\yanxu\frontend
D:\document\npm.cmd run build
```

启动后端：

```powershell
Set-Location D:\yanxu\backend
uv run uvicorn yanxu.api:create_app --factory --host 127.0.0.1 --port 5189
```

如需真实音频转写，另开终端启动 worker：

```powershell
Set-Location D:\yanxu\backend
uv run python -m yanxu.worker
```

## 验证结果

已验证：

```text
backend: uv run pytest -q
结果：43 passed, 2 warnings

frontend: npm run build
结果：通过
```

Android 构建当前未完成，原因是本机缺少 Android 构建环境变量：

```text
JAVA_HOME is not set and no 'java' command could be found in your PATH.
```

配置 JDK 17 和 Android SDK 后，可在 `D:\yanxu\android` 运行：

```powershell
.\gradlew.bat assembleDebug
```

生成的 APK 应复制到：

```text
D:\yanxu\.local-data\artifacts\yanxu-debug.apk
```

后端会通过 `/app/yanxu-debug.apk` 提供下载。

## 与 GitHub release 分支的关系

本地目录不是 `.git` 工作区，而是代码快照加后续改动。已临时下载 GitHub `Symplify62/yanxu` 的 `release` 分支到 `.local-data/compare` 做对照。

对照发现，GitHub `release` 分支和当前本地目录不是简单的同一版本关系：远端包含账号、身份、声纹和管理工作台相关模块；当前本地目录包含完整公共记录页、纪要模板、样本文档和导出功能。因此不要直接用远端 release 覆盖当前目录。

后续如果要做完整长期合并，建议先建立正式 Git 工作区，再以一个明确底座进行迁移：

1. 以当前本地版本作为公共记录和纪要能力基线。
2. 单独评估远端 `identity`、`voice`、`managed_recordings` 等模块是否需要并入。
3. 分模块迁移并逐项运行后端、前端、Android 测试。
4. 迁移前备份 `.local-data/server` 和 `.local-data/artifacts`。
