# 前端组件选型与迁移记录

当前工程规则统一维护在[前端工程实施](frontend-guides/05-工程实施.md)。下文保留历史迁移选择与问题说明，不能覆盖当前A方案决策。

> 2026-09-21更新：用户已确认A方案，当前正式Web原型三端使用Element Plus，入口为/prototype.html；手机Vant属于下文原v0.4迁移记录。详见[设计决策](design-lab/selection.md)。本次不确定原生Android或后端技术栈。

状态：v0.4本地组件原型已实施；不冻结后端技术栈或原生Android方案。用户先认可使用正式组件实现原型，随后回复“ok”，本轮据此完成前端工程迁移。

## 选择

Vue 3 + TypeScript + Vite + Vue Router：组件/类型/路由分层。Element Plus用于管理后台和本轮平板Web预览；Vant用于员工手机网页。使用同一API类型和请求层、设计语义，分别采用适合桌面密度与手机触控的组件。

没有同时引入两个Web框架。Element Plus与Vant各自解决不同屏端的问题，已通过五种宽度截图检查；原生安卓未来需原生控件与采集实现，不因本轮Web组件而被锁定为Web录音。

MSW只在独立模拟层拦截网络，页面不导入MockDatabase或fixtures。这样可以保持真实表单校验、提交/失败/版本冲突与路由结构，再逐个接入真实接口。不能承诺更换地址就完成联调：当前字段/接口仍需与正式契约对齐。

组件展示采用工程内/components路由，已经复用正式组件；本轮没有安装Storybook。需要更大规模状态文档时可迁入Storybook，不为已有展示页再维护一套重复定义。

## 版本与兼容

依赖版本见package.json、package-lock.json和dependency-inventory.json。最初安装的TypeScript 7与当前vue-tsc存在tsc子路径兼容问题；已固定TypeScript 5.9.3并通过类型检查与构建。其他直接依赖亦精确固定，避免未经验证的自动浮动。

Vite自动发现懒加载组件样式时会触发预构建刷新，重置内存mock。最终使用noDiscovery及明确预构建的组件/路由/MSW/Day.js根依赖，纯ESM样式直接加载；冷启动跨端导航已验证无额外页面刷新。新增CommonJS依赖时应更新optimizeDeps.include并复测开发导航。

依赖清单登记的是所选npm包的声明许可，不代替未来交付方式的完整法律判断。真实服务、商业使用条件和转发数据边界按项目门禁另行核实。

## 官方依据

- [Element Plus接入与按需导入](https://element-plus.org/en-US/guide/quickstart.html)
- [Vant手机组件](https://vant-ui.github.io/vant/)
- [MSW浏览器网络模拟](https://mswjs.io/docs/integrations/browser)
- [Vite依赖优化选项](https://vite.dev/config/dep-optimization-options)
- [Storybook组件与页面状态](https://storybook.js.org/docs)
