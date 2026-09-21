import type { Employee, Department, Meeting, TaskItem } from "../domain/types";
export const people = (): Employee[] => [
  {
    id: "lin",
    name: "林同事",
    department: "sales",
    allowedDepartments: ["sales", "finance"],
    active: true,
    internal: true,
    registered: true,
    admin: false,
  },
  {
    id: "chen",
    name: "陈同事",
    department: "finance",
    allowedDepartments: ["finance"],
    active: true,
    internal: true,
    registered: true,
    admin: false,
  },
  {
    id: "zhou",
    name: "周同事",
    department: "sales",
    allowedDepartments: ["sales"],
    active: true,
    internal: true,
    registered: false,
    admin: false,
  },
  {
    id: "left",
    name: "已停用员工",
    department: "sales",
    allowedDepartments: ["sales"],
    active: false,
    internal: true,
    registered: true,
    admin: false,
  },
  {
    id: "outside",
    name: "其他企业用户",
    department: "sales",
    allowedDepartments: [],
    active: true,
    internal: false,
    registered: false,
    admin: false,
  },
  {
    id: "admin",
    name: "系统管理员",
    department: "ops",
    allowedDepartments: [],
    active: true,
    internal: true,
    registered: true,
    admin: true,
  },
];
export const departments: Department[] = [
  { id: "sales", name: "销售部" },
  { id: "finance", name: "财务部" },
  { id: "ops", name: "信息技术部" },
];
export const tasks = (): TaskItem[] => [
  {
    id: "t1",
    text: "修正并提交报价表",
    owner: "王工",
    due: "2026-09-24",
    evidence: "seg-004",
  },
  { id: "t2", text: "核对客户资料", owner: "", due: "", evidence: "seg-007" },
];
export const sampleSummary =
  "确认客户报价为 125,000 元，不批准额外采购。P-208 的交付日期仍待客户确认；报价修订、资料核对与进展反馈列为行动事项。";
export const transcript = [
  {
    id: "seg-002",
    time: "00:10",
    speaker: "说话人 1",
    text: "客户报价是十二万五千元，不是十五万元。",
  },
  {
    id: "seg-004",
    time: "00:30",
    speaker: "说话人 2",
    text: "决定报价仍按十二万五千元，不批准额外采购。请王工在9月24日前提交修正报价表。",
  },
  {
    id: "seg-007",
    time: "01:00",
    speaker: "说话人 3",
    text: "客户资料需要有人再核对一遍，负责人还没有定，时间也先不定。",
  },
];
export function meeting(
  id: string,
  owner: string,
  department: string,
): Meeting {
  const summary = sampleSummary,
    list = tasks(),
    target =
      department === "sales" ? "销售管理群（模拟）" : "财务管理群（模拟）";
  return {
    id,
    title: id === "m1" ? "报价与交付协调" : "财务例会",
    owner,
    department,
    duration: 99,
    createdAt: "2026-09-20T09:00:00+08:00",
    progress: 4,
    state: "ACCEPTED",
    summary,
    tasks: list,
    version: 1,
    versions: [
      {
        version: 1,
        summary,
        tasks: structuredClone(list),
        reason: "AI 原始版本",
      },
    ],
    publication: { version: 1, summary, tasks: structuredClone(list), target },
    grants: [],
    target,
    attempts: 0,
    sendCount: 1,
    scenario: "normal",
    nextAt: 0,
    resolvedManually: false,
  };
}
