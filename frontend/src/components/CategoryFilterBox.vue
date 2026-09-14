<script setup>
import { STORE_CATEGORIES } from "../categories"

const props = defineProps({
  modelValue: { type: Array, required: true },
})
const emit = defineEmits(["update:modelValue"])

function toggle(value) {
  const next = new Set(props.modelValue)
  if (next.has(value)) {
    next.delete(value)
  } else {
    next.add(value)
  }
  emit("update:modelValue", Array.from(next))
}

function clear() {
  emit("update:modelValue", [])
}
</script>

<template>
  <details class="category-filter">
    <summary class="category-filter-summary">
      Filter by category
      <span v-if="modelValue.length" class="category-filter-count">{{ modelValue.length }}</span>
    </summary>

    <div class="category-filter-box">
      <label
        v-for="cat in STORE_CATEGORIES"
        :key="cat.value"
        class="category-filter-option"
      >
        <input
          type="checkbox"
          :checked="modelValue.includes(cat.value)"
          @change="toggle(cat.value)"
        >
        <span>{{ cat.label }}</span>
      </label>

      <button
        v-if="modelValue.length"
        type="button"
        class="category-filter-clear"
        @click="clear"
      >
        Clear categories
      </button>
    </div>
  </details>
</template>
