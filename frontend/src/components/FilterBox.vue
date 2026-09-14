<script setup>
import { computed, ref } from "vue"
import { STORE_CATEGORIES } from "../categories"

const props = defineProps({
  paymentMethods: { type: Array, default: () => [] },
  selectedPaymentMethods: { type: Array, required: true },
  selectedCategories: { type: Array, required: true },
})

const emit = defineEmits([
  "update:selectedPaymentMethods",
  "update:selectedCategories",
  "apply",
])

const detailsRef = ref(null)

const activeCount = computed(
  () => props.selectedPaymentMethods.length + props.selectedCategories.length
)

function togglePaymentMethod(id) {
  const next = new Set(props.selectedPaymentMethods)
  if (next.has(id)) {
    next.delete(id)
  } else {
    next.add(id)
  }
  emit("update:selectedPaymentMethods", Array.from(next))
}

function toggleCategory(value) {
  const next = new Set(props.selectedCategories)
  if (next.has(value)) {
    next.delete(value)
  } else {
    next.add(value)
  }
  emit("update:selectedCategories", Array.from(next))
}

function close() {
  if (detailsRef.value) detailsRef.value.open = false
}

function apply() {
  emit("apply")
  close()
}

function clear() {
  emit("update:selectedPaymentMethods", [])
  emit("update:selectedCategories", [])
  emit("apply")
  close()
}
</script>

<template>
  <details ref="detailsRef" class="filter-box">
    <summary class="filter-box-summary">
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
      >
        <path d="M4 5h16l-6 8v6l-4-2v-4Z" />
      </svg>

      Filter

      <span v-if="activeCount" class="filter-box-count">{{ activeCount }}</span>
    </summary>

    <div class="filter-box-panel">
      <div v-if="paymentMethods.length" class="filter-section">
        <div class="filter-section-title">Payment method</div>
        <div class="filter-checkbox-grid">
          <label
            v-for="method in paymentMethods"
            :key="method.id"
            class="filter-checkbox-option"
          >
            <input
              type="checkbox"
              :checked="selectedPaymentMethods.includes(method.id)"
              @change="togglePaymentMethod(method.id)"
            >
            <span>{{ method.name }}</span>
          </label>
        </div>
      </div>

      <div class="filter-section">
        <div class="filter-section-title">Category</div>
        <div class="filter-checkbox-grid">
          <label
            v-for="cat in STORE_CATEGORIES"
            :key="cat.value"
            class="filter-checkbox-option"
          >
            <input
              type="checkbox"
              :checked="selectedCategories.includes(cat.value)"
              @change="toggleCategory(cat.value)"
            >
            <span>{{ cat.label }}</span>
          </label>
        </div>
      </div>

      <div class="filter-box-actions">
        <button type="button" class="button primary small" @click="apply">
          Apply
        </button>
        <button type="button" class="button secondary small" @click="clear">
          Clear
        </button>
      </div>
    </div>
  </details>
</template>
