<script setup lang="ts">
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "../ui/dialog";
defineProps<{ modelValue: boolean; title?: string }>();
const emit = defineEmits<{ "update:modelValue": [value: boolean] }>();
</script>
<template>
  <Dialog :open="modelValue" @update:open="emit('update:modelValue', $event)"
    ><DialogContent class="lab-dialog-content"
      ><DialogHeader
        ><DialogTitle>{{ title || "模拟企业微信扫码" }}</DialogTitle
        ><DialogDescription>{{
          title
            ? "查看并完成本次操作。"
            : "仅体验本场身份绑定，未连接企业微信。"
        }}</DialogDescription></DialogHeader
      >
      <div class="dialog-scroll-body"><slot /></div>
      <DialogFooter><slot name="footer" /></DialogFooter></DialogContent
  ></Dialog>
</template>
