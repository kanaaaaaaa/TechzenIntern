<script setup>
import StatusControl from "./StatusControl.vue"

defineProps({
  methods: { type: Array, required: true },
  statuses: { type: Object, required: true },
})

defineEmits(["update-status"])
</script>

<template>
  <div class="method-list">
    <div v-for="method in methods" :key="method.id" class="method-edit-row">
      <div>
        <strong>{{ method.name }}</strong>
      </div>
      <StatusControl
        :model-value="statuses[method.id] || 'unknown'"
        @update:model-value="$emit('update-status', method.id, $event)"
      />
    </div>
  </div>
</template>
