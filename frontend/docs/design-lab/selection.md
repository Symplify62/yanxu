# A方案确认（2026-09-21）

用户在完整A/B原型对比后确认「用A吧」。现将A作为言序后续前端视觉和组件原型基线。

- 视觉：暖白底、柔和绿色、适度圆角。平板聚焦扫码/录音，手机聚焦资料阅读，后台以固定导航和表格工作区为主。
- 组件：当前确认版的三个端使用Element Plus实际组件与业务布局。手机端是响应式Web原型；正式端技术实施仍需依据目标设备能力验证。
- 正式原型入口：/prototype.html，固定A，不提供A/B切换；开发站点根地址现进入第一阶段演示。可用surface=tablet/employee/admin/components进入对应端。
- 原A/B比较及C实现已从当前分支移除，历史见[清理记录](../../../docs/repository/cleanup.md)。历史v0.4 /tablet、/employee、/admin仍可访问供回归参考，不再是当前设计入口。
- 用户只确认了设计方案，本次不扩大到真实认证、录音/持久队列、AI、企业微信或生产发布；业务规则继续沿用U-11。

实现位置：src/styles/a-theme.css、a-layout.css及src/design-lab/kits/Element*；正式入口直接复用已验收A方案，无独立复制的业务实现。
