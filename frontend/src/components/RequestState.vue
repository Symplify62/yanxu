<script setup lang="ts">
defineProps<{
  loading?: boolean;
  error?: string;
  empty?: boolean;
  mobile?: boolean;
  message?: string;
}>();
defineEmits<{ retry: [] }>();
</script>
<template>
  <div class="request-state">
    <template v-if="loading"
      ><van-loading v-if="mobile" vertical>正在加载</van-loading
      ><el-skeleton v-else :rows="3" animated /></template
    ><template v-else-if="error"
      ><van-empty v-if="mobile" image="error" :description="error"
        ><van-button size="small" @click="$emit('retry')"
          >重新加载</van-button
        ></van-empty
      ><el-result v-else icon="warning" title="暂时无法加载" :sub-title="error"
        ><template #extra
          ><el-button @click="$emit('retry')">重新加载</el-button></template
        ></el-result
      ></template
    ><template v-else-if="empty"
      ><van-empty v-if="mobile" :description="message || '暂无记录'" /><el-empty
        v-else
        :description="message || '暂无记录'"
    /></template>
  </div>
</template>
