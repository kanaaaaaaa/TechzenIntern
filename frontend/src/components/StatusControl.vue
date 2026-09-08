<script setup>
defineProps({
  modelValue: { type: String, required: true },
})

defineEmits(["update:modelValue"])

const options = [
  { value: "accepted", label: "⚪︎" },
  { value: "not_accepted", label: "×" },
  { value: "unknown", label: "？" },
]
</script>

<template>
  <div class="status-control">
    <button
      v-for="option in options"
      :key="option.value"
      type="button"
      :class="[option.value, { selected: modelValue === option.value }]"
      @click="$emit('update:modelValue', option.value)"
    >
      {{ option.label }}
    </button>
  </div>
</template>

