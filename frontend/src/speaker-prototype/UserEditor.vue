<script setup lang="ts">
import { ref, watch } from "vue";
import { ElInput, ElSelect, ElOption, ElSwitch } from "element-plus";
import Dialog from "../design-lab/kits/ElementDialog.vue";
import Button from "../design-lab/kits/ElementButton.vue";
import type { Person, PrototypeModel } from "./model";
const props = defineProps<{
  model: PrototypeModel;
  open: boolean;
  person?: Person;
  guest?: boolean;
}>();
const emit = defineEmits<{ close: []; saved: [id: string] }>();
const name = ref(""),
  detail = ref(""),
  departmentId = ref(""),
  roleId = ref("member"),
  active = ref(true),
  error = ref("");
watch(
  () => props.open,
  (open) => {
    if (open) {
      name.value = props.person?.name || "";
      detail.value = props.person?.detail || "";
      departmentId.value = props.person?.departmentId || "product";
      roleId.value = props.person?.roleId || "member";
      active.value = props.person?.active ?? true;
      error.value = "";
    }
  },
);
function save() {
  try {
    const id = props.model.savePerson(
      {
        id: props.person?.id,
        name: name.value,
        detail: detail.value,
        scope: props.guest ? "guest" : "member",
        departmentId: props.guest ? "" : departmentId.value,
        roleId: roleId.value,
        active: active.value,
      },
      props.guest,
    );
    emit("saved", id);
    emit("close");
  } catch (e) {
    error.value = (e as Error).message;
  }
}
</script>
<template>
  <Dialog
    :model-value="open"
    :title="guest ? '添加临时来宾' : person ? '编辑用户' : '添加用户'"
    @update:model-value="$emit('close')"
    ><form class="editor-form" @submit.prevent="save">
      <label
        >姓名 <span>*</span
        ><ElInput
          v-model="name"
          aria-label="用户姓名"
          maxlength="20"
          placeholder="真实姓名" /></label
      ><label
        >{{ guest ? "备注" : "职位 / 备注"
        }}<ElInput
          v-model="detail"
          aria-label="用户备注"
          maxlength="80"
          placeholder="用于区分同名人员" /></label
      ><template v-if="!guest"
        ><label
          >所属部门<ElSelect v-model="departmentId" aria-label="所属部门"
            ><ElOption
              v-for="d in model.departments.value"
              :key="d.id"
              :value="d.id"
              :label="d.name" /></ElSelect></label
        ><label
          >角色<ElSelect v-model="roleId" aria-label="用户角色"
            ><ElOption
              v-for="r in model.roles.value"
              :key="r.id"
              :value="r.id"
              :label="r.name" /></ElSelect
        ></label>
        <div class="setting-row compact">
          <span>启用用户</span
          ><ElSwitch v-model="active" aria-label="启用用户" /></div
      ></template>
      <p v-else class="quiet-note">来宾不创建登录账号，声音仅用于本场。</p>
      <p v-if="error" class="form-error" role="alert">{{ error }}</p>
    </form>
    <template #footer
      ><Button secondary @click="$emit('close')">取消</Button
      ><Button @click="save">{{
        guest ? "添加并选中" : "保存用户"
      }}</Button></template
    ></Dialog
  >
</template>
