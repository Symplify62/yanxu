<script setup lang="ts">
import {
  AudioLines,
  LayoutDashboard,
  Users,
  Network,
  ShieldCheck,
  UsersRound,
  Send,
  TriangleAlert,
  History,
  Tablet,
  LogOut,
  ChevronRight,
  CheckCircle2,
  RefreshCw,
} from "@lucide/vue";
import { useKit } from "./context";
import { accounts, signOut } from "./account";
import AccountLogin from "./AccountLogin.vue";
import { useAdminModel, sections } from "./useAdminModel";
import { api } from "../../services/api";
import { statusLabels, duration } from "../../domain/presentation";
const { Button, Select, Input, Dialog, Checkbox, Table } = useKit();
const icons = [
  LayoutDashboard,
  Users,
  Network,
  ShieldCheck,
  UsersRound,
  Send,
  TriangleAlert,
  History,
  Tablet,
];
const {
  section,
  query,
  department,
  modal,
  busy,
  message,
  mutationError,
  data,
  error,
  loading,
  refresh,
  device,
  deptName,
  metrics,
  columns,
  rows,
  person,
  role,
  job,
  members,
  target,
  reason,
  open,
  mutate,
  save,
  modalTitle,
} = useAdminModel();
const routeOptions = [
  { value: "", label: "未配置" },
  ...["销售管理群（模拟）", "财务管理群（模拟）", "项目协作群（模拟）"].map(
    (n) => ({ value: n, label: n }),
  ),
];
</script>
<template>
  <div class="admin-app">
    <AccountLogin v-if="!accounts.admin" scope="admin" />
    <div v-else class="admin-frame">
      <aside class="admin-rail">
        <div class="admin-brand">
          <AudioLines :size="24" /><strong>言序</strong
          ><small>管理工作台</small>
        </div>
        <p class="rail-caption">工作空间</p>
        <nav aria-label="后台模块">
          <button
            v-for="(s, i) in sections"
            :key="s[0]"
            :class="{ active: section === s[0] }"
            @click="section = s[0]!"
          >
            <component :is="icons[i]" :size="17" /><span>{{ s[1] }}</span
            ><span
              v-if="s[0] === 'exceptions' && metrics[3]!.value"
              class="nav-count"
              >{{ metrics[3]!.value }}</span
            >
          </button>
        </nav>
        <div class="rail-profile">
          <span class="admin-avatar">管</span>
          <div><strong>系统管理员</strong><small>公司工作空间</small></div>
          <button
            aria-label="退出管理登录"
            class="icon-link"
            @click="signOut('admin')"
          >
            <LogOut :size="16" />
          </button>
        </div>
      </aside>
      <div class="admin-content">
        <header class="workspace-bar">
          <span
            >公司工作空间<ChevronRight :size="13" />{{
              sections.find((s) => s[0] === section)?.[1]
            }}</span
          ><span class="status-pill"
            ><span class="status-dot"></span>模拟环境</span
          >
        </header>
        <main class="admin-main">
          <div class="workspace-title">
            <div>
              <p class="overline">
                {{
                  section === "overview" ? "自动运行 · 统一管理" : "组织与运营"
                }}
              </p>
              <h1>{{ sections.find((s) => s[0] === section)?.[1] }}</h1>
              <p class="support-copy">
                {{
                  section === "overview"
                    ? "让正常流程自动完成，把注意力留给异常。"
                    : section === "people"
                      ? "有效公司员工首次登录自动开户，会议访问范围单独授权。"
                      : section === "roles"
                        ? "角色决定可以做什么，会议授权决定可以查看什么。"
                        : section === "routes"
                          ? "按会议归属自动分发，员工无需选群或确认发布。"
                          : section === "exceptions"
                            ? "系统先自动恢复，无法恢复时在这里接管。"
                            : section === "audit"
                              ? "追溯系统处理、员工更正和管理员操作。"
                              : section === "groups"
                                ? "维护共享查看范围，不改变成员的部门和管理资格。"
                                : section === "devices"
                                  ? "查看设备与后台队列，员工退出后处理继续。"
                                  : "组织归属同步，不自动开放部门会议资料。"
                }}
              </p>
            </div>
            <Button
              v-if="section === 'organization'"
              secondary
              :busy="busy"
              @click="
                mutate(api.admin.sync, '已完成模拟组织同步，未访问企业微信')
              "
              ><RefreshCw :size="15" />模拟同步组织</Button
            >
          </div>
          <div v-if="loading" class="empty-content">正在加载工作空间…</div>
          <div v-else-if="error" role="alert" class="error-banner">
            {{ error }}<Button secondary @click="refresh">重试</Button>
          </div>
          <template v-else-if="data"
            ><p
              v-if="mutationError && !modal"
              role="alert"
              class="error-banner"
            >
              {{ mutationError }}
            </p>
            <p v-if="message" role="status" class="success-banner">
              <CheckCircle2 :size="16" />{{ message }}
            </p>
            <div v-if="section === 'overview'" class="metrics-strip">
              <div
                v-for="(m, i) in metrics"
                :key="m.label"
                :class="{ attention: i === 3 && m.value > 0 }"
              >
                <span>{{ m.label }}</span
                ><strong>{{ String(m.value).padStart(2, "0") }}</strong
                ><small>{{
                  i === 3
                    ? "异常由管理员处理"
                    : i === 1
                      ? "渠道已接收"
                      : "本次演示记录"
                }}</small>
              </div>
            </div>
            <p v-if="section === 'roles'" class="notice">
              当前展示预置角色及权限。自定义角色与委派编辑尚未实现。
            </p>
            <p
              v-if="section === 'overview' || section === 'exceptions'"
              class="workspace-note"
            >
              <ShieldCheck
                :size="15"
              />仅展示编号与处理状态，会议正文需独立授权。
            </p>
            <template v-if="section === 'devices'"
              ><div class="device-overview">
                <div class="device-summary">
                  <Tablet :size="40" />
                  <div>
                    <h2>会议室 A</h2>
                    <p>共享录音设备 · 已配对（模拟）</p>
                  </div>
                  <span
                    class="status-pill"
                    :class="{ pending: !device?.online }"
                    >{{ device?.online ? "设备在线" : "设备离线" }}</span
                  >
                </div>
                <dl class="settings-list">
                  <div>
                    <dt>本场员工</dt>
                    <dd>{{ device?.employeeName || "已退出 / 等待扫码" }}</dd>
                  </div>
                  <div>
                    <dt>公司档案</dt>
                    <dd>原录音与文字长期保留，不按期限自动删除</dd>
                  </div>
                  <div>
                    <dt>设备缓存</dt>
                    <dd>归档、独立备份与批准清理条件满足后处理</dd>
                  </div>
                  <div>
                    <dt>录音时长</dt>
                    <dd>不设业务截止，持续能力与资源边界需真机验证</dd>
                  </div>
                </dl>
                <h3>设备处理队列</h3>
                <p v-if="!device?.queue.length" class="small-muted">
                  当前没有待处理录音
                </p>
                <div v-for="j in device?.queue" :key="j.id" class="grant-row">
                  <span>{{ j.id }} · {{ duration(j.duration) }}</span
                  ><span class="status-pill pending">{{
                    statusLabels[j.state]
                  }}</span>
                </div>
              </div></template
            >
            <div
              v-else
              class="admin-table-area"
              :class="{ 'with-org': section === 'organization' }"
            >
              <aside v-if="section === 'organization'" class="org-tree">
                <button
                  :class="{ active: department === 'company' }"
                  @click="department = 'company'"
                >
                  <Network :size="16" />示例公司</button
                ><button
                  v-for="d in data.departments"
                  :key="d.id"
                  :class="{ active: department === d.id }"
                  class="org-child"
                  @click="department = d.id"
                >
                  {{ d.name }}
                </button>
              </aside>
              <section class="table-surface">
                <div class="table-caption">
                  <div>
                    <h2>
                      {{
                        section === "overview"
                          ? "最近处理记录"
                          : section === "organization"
                            ? deptName(department) === "company"
                              ? "全部成员"
                              : deptName(department)
                            : sections.find((s) => s[0] === section)?.[1]
                      }}
                    </h2>
                    <span>{{ rows.length }} 条记录</span>
                  </div>
                  <Input
                    v-if="section === 'people'"
                    v-model="query"
                    label="搜索员工姓名"
                    placeholder="搜索员工姓名"
                    class="admin-search"
                  /><Button
                    v-if="section === 'routes'"
                    secondary
                    @click="open('pause')"
                    >{{
                      data.settings.paused ? "恢复自动发送" : "应急停止发送"
                    }}</Button
                  >
                </div>
                <div v-if="section === 'routes'" class="table-note">
                  <span
                    class="status-pill"
                    :class="{ pending: data.settings.paused }"
                    >{{
                      data.settings.paused ? "已应急停发" : "自动发送已启用"
                    }}</span
                  ><span>新规则只作用后续会议</span>
                </div>
                <Table
                  :rows="rows"
                  :columns="columns"
                  :caption="sections.find((s) => s[0] === section)?.[1]"
                  ><template #status="{ row }"
                    ><span
                      class="status-pill"
                      :class="{
                        pending:
                          row.status !== '正常' && row.status !== '渠道已接收',
                      }"
                      >{{ row.status }}</span
                    ></template
                  ><template #action="{ row }"
                    ><template v-if="section === 'audit'">{{
                      row.action
                    }}</template
                    ><Button
                      v-else-if="
                        section === 'people' || section === 'organization'
                      "
                      secondary
                      :disabled="Boolean(row.admin)"
                      @click="open('person', String(row.id))"
                      >{{ row.active ? "停用" : "启用" }}</Button
                    ><Button
                      v-else-if="section === 'roles'"
                      secondary
                      @click="open('role', String(row.id))"
                      >查看权限</Button
                    ><Button
                      v-else-if="section === 'groups'"
                      secondary
                      @click="open('group', String(row.id))"
                      >维护成员</Button
                    ><Button
                      v-else-if="section === 'routes'"
                      secondary
                      @click="open('route', String(row.id))"
                      >配置接收群</Button
                    ><Button
                      v-else-if="section === 'exceptions'"
                      secondary
                      @click="open('recover', String(row.id))"
                      >{{
                        row.state === "UNKNOWN"
                          ? "记录渠道核查"
                          : "重新检查并恢复"
                      }}</Button
                    ></template
                  ></Table
                >
                <p
                  v-if="section === 'exceptions' && !rows.length"
                  class="empty-content"
                >
                  没有需要人工接管的异常
                </p>
              </section>
            </div>
          </template>
        </main>
      </div>
    </div>
    <Dialog
      :model-value="!!modal && !!accounts.admin"
      :title="modalTitle"
      @update:model-value="!$event && (modal = '')"
      ><div class="dialog-form">
        <template v-if="modal === 'person'"
          ><h3>{{ person?.name }}</h3>
          <p class="notice">
            {{
              person?.active
                ? "停用将撤销现有演示会话，保留原会议和操作记录。"
                : "启用后仍需重新登录，按现有授权判断访问范围。"
            }}
          </p></template
        ><template v-else-if="modal === 'role'"
          ><h2>{{ role?.name }}</h2>
          <span v-if="role?.protected" class="status-pill pending"
            >保护角色</span
          >
          <h3>功能权限</h3>
          <div class="permissions-list">
            <span v-for="p in role?.permissions" :key="p">{{ p }}</span>
          </div>
          <p class="notice">
            会议范围由本人归属或独立授权决定，不因角色名自动开放全公司资料。
          </p></template
        ><template v-else-if="modal === 'group'"
          ><p class="notice">成员变更会影响该组已有共享记录。</p>
          <div class="member-checks">
            <Checkbox
              v-for="p in data?.people.filter((p) => p.active && !p.admin)"
              :key="p.id"
              :model-value="members.includes(p.id)"
              :label="p.name"
              @update:model-value="
                members = $event
                  ? [...members, p.id]
                  : members.filter((id) => id !== p.id)
              "
            /></div></template
        ><template v-else-if="modal === 'route'"
          ><p class="notice">仅使用虚构群连接，不接收真实 Webhook。</p>
          <label class="field-label">群连接</label
          ><Select
            v-model="target"
            :options="routeOptions"
            label="群连接" /></template
        ><template v-else-if="modal === 'pause'"
          ><p class="notice">
            影响尚未提交的外发任务。原件继续保留，已发送的会议不会重复发送，未知结果仍需核查。
          </p></template
        ><template v-else-if="modal === 'recover'"
          ><span class="status-pill pending">{{
            job ? statusLabels[job.state] : ""
          }}</span>
          <p class="notice">
            {{
              job?.state === "UNKNOWN"
                ? "请求可能已送达，不能盲目重发。记录实际查到渠道接收的依据。"
                : "模拟依赖恢复后重新校验，只继续失败阶段。"
            }}
          </p>
          <label class="field-label">处理依据（必填）</label
          ><Input v-model="reason" label="处理依据" multiline
        /></template>
        <p v-if="mutationError" role="alert" class="error-banner">
          {{ mutationError }}
        </p>
      </div>
      <template #footer
        ><div class="dialog-actions">
          <Button secondary :disabled="busy" @click="modal = ''">{{
            modal === "role" ? "关闭" : "取消"
          }}</Button
          ><Button v-if="modal !== 'role'" :busy="busy" @click="save">{{
            modal === "person"
              ? "确认变更"
              : modal === "group"
                ? "确认成员变更"
                : modal === "route"
                  ? "保存新规则"
                  : modal === "pause"
                    ? data?.settings.paused
                      ? "确认恢复"
                      : "确认停发"
                    : job?.state === "UNKNOWN"
                      ? "记录人工已核对接收"
                      : "确认恢复该阶段"
          }}</Button>
        </div></template
      ></Dialog
    >
  </div>
</template>
