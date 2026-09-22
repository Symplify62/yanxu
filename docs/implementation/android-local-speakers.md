# Android：本机参会者与本人声音

状态：2026-09-22 已实现并构建0.2.0本机功能测试包，设备验证证据见下文和本轮验收记录。用户已明确选择先交付可安装的真实App：头像选人、全选、本人声音录制与本机保存，保留现有转写；本轮不同时接账号/云后台。

## 功能边界

- 安卓原生录音页显示本机人员头像，可独立选入本场；常用前7人全选、更多人员搜索/部门筛选及范围全选，未选中也可录声音。
- 首次没有示例人员或示例声音。通过添加表单建立本机成员或本场来宾，姓名必填，部门/备注可选，同名同部门需区分。
- 每个人有录制声音/重新录制入口，使用真实AudioRecord采样，停止后试听本人WAV；确认姓名、本人声音和长期保存同意后才保存。改名清除旧确认。取消/保存失败保留原样本。
- 声音状态仅表示“声音已保存，仅本机”。未做特征生成、质量模型或会议说话人匹配；最终云端逐字稿仍按现有服务能力提供，不能承诺带实名归属。
- 主会议录音期间名单和登记操作锁定，本轮不做迟到追加；结束后可修改。选人的动作不等于账号登录。
- 可以不选人直接录音，保留原第一阶段便捷入口；如已选择，则开始前将名单快照与本地录音meta可靠保存。
- 本机声音在people/voices，未确认草稿在people/staging，与只扫描recordings的会议上传队列分开。登记声音不上传或公开。
- “准备下一场”明确清除临时来宾及其声音与当前选择，保留长期成员及声音；已保存会议的本机名单快照不被改写。

## 生命周期与互斥

会议AudioRecord前台服务保持现有可靠采集、暂停/继续、保存与上传。声音登记只在前台弹窗内录制，启动时占用声音登记互斥；退出/退后台/旋转会取消未确认草稿，确认保存已开始时允许原子提交完成。

声音登记与会议采集、App自动安装共用GATE；已完成麦克风释放后才解除busy/active，避免两个采集源重叠或安装中断保存。试听播放器在重录、取消和后台释放。

声音样本限制为最长5分钟（仅登记样本，不是会议时长上限），16kHz/mono/PCM16；空字节、读取失败或全零信号拒绝保存。非零信号检查不代表真实人声、单说话人或声纹质量已通过。

## 持久化与兼容

[PeopleStore](../../android/app/src/main/java/cn/jiajian/yanxu/PeopleStore.java)以稳定UUID管理人员、选择和样本，进程内共享锁且每次重新读盘，AtomicFile提交元信息。新音频使用独立UUID文件，完成写入和sync后才切元信息；只有提交成功才清旧文件。恢复清理遗留草稿/孤立样本，不删除已登记音频或同进程活动草稿。

[RecordingService](../../android/app/src/main/java/cn/jiajian/yanxu/RecordingService.java)接收participantsSnapshot并存入本地meta。它不进入旧公网创建录音请求，避免未认证的旧API接收人员/声纹字段；公开上传和转写协议保持原样。[后端完整方案](../phases/speaker-backend-design.md)以后再落实云端身份与声音任务。

允许覆盖安装保留已有录音与服务地址，不清空应用数据。默认服务仍为https://yanxu.qjl666.xyz，测试使用独立本地服务，不公布测试录音。

## 验证入口与证据

- 正式模块：[PeoplePanel](../../android/app/src/main/java/cn/jiajian/yanxu/PeoplePanel.java)、[VoiceEnrollmentDialog](../../android/app/src/main/java/cn/jiajian/yanxu/VoiceEnrollmentDialog.java)、[VoiceSampleRecorder](../../android/app/src/main/java/cn/jiajian/yanxu/VoiceSampleRecorder.java)。
- test APK内的[SpeakersInstrumentation](../../android/app/src/androidTest/java/cn/jiajian/yanxu/SpeakersInstrumentation.java)聚合独立目录存储检查、确定性PCM采集检查、真实弹层控件检查。生产没有测试Intent或全局假麦克风开关。
- 构建：在android执行 `./gradlew assembleDebug assembleDebugAndroidTest -PyanxuTestRunner=cn.jiajian.yanxu.SpeakersInstrumentation --offline`。常规默认仍为原UpdateInstrumentation。
- 证据：`.local-data/evidence/android-speakers/`，包含安装前私有数据备份、构建、仪器结果、实际模拟器截图、独立API及文件核验。测试只使用专门的emulator-5560；未修改另一模拟器或实体手机。

测试音源注入仅存在包内依赖构造与test APK实现。它用于验证采集/保存/UI状态，不得称作真人麦克风识别效果。真实设备拾音、背景噪音、锁屏长录音与同事测试另行验收。

本轮APK输出：项目根目录下 `.local-data/artifacts/yanxu-0.2.0-local-speakers-debug.apk`。仅本机交付，未修改公网自动更新清单。


本轮验收结果：私有存储专项、7项采集检查、9项原生声音弹层检查、5项原生人员布局/交互检查通过；真实会议录音12秒完成保存并上传到隔离API，文件校验一致且进入既有ASR队列。覆盖安装前后的2条旧录音共4个文件保持一致；恢复公网连接后公共记录列表可见。模拟器的确定性音源测试不替代同事真机拾音和识别效果验收。详细日志、截图及限制见本机 `.local-data/evidence/android-speakers/verification.md`。
