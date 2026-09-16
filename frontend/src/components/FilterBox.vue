<script setup>
import { computed, ref } from "vue"
import { STORE_CATEGORIES } from "../categories"

const props = defineProps({
  paymentMethods: { type: Array, default: () => [] },
  selectedPaymentMethods: { type: Array, required: true },
  selectedCategories: { type: Array, required: true },
  sortOptions: { type: Array, default: () => [] },
  selectedSort: { type: String, default: "" },
  includePaymentUnknown: { type: Boolean, default: false },
  includeCategoryUnknown: { type: Boolean, default: false },
})

const emit = defineEmits([
  "update:selectedPaymentMethods",
  "update:selectedCategories",
  "update:selectedSort",
  "update:includePaymentUnknown",
  "update:includeCategoryUnknown",
  "apply",
])

const detailsRef = ref(null)

const activeCount = computed(
  () =>
    props.selectedPaymentMethods.length +
    props.selectedCategories.length +
    (props.selectedSort ? 1 : 0) +
    (props.includePaymentUnknown ? 1 : 0) +
    (props.includeCategoryUnknown ? 1 : 0)
)

function togglePaymentMethod(id) {
  const next = new Set(props.selectedPaymentMethods)
  if (next.has(id)) {
    next.delete(id)
  } else {
    next.add(id)
  }
  emit("update:selectedPaymentMethods", Array.from(next))
  if (next.size === 0) emit("update:includePaymentUnknown", false)
}

function toggleCategory(value) {
  const next = new Set(props.selectedCategories)
  if (next.has(value)) {
    next.delete(value)
  } else {
    next.add(value)
  }
  emit("update:selectedCategories", Array.from(next))
  if (next.size === 0) emit("update:includeCategoryUnknown", false)
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
  emit("update:selectedSort", "")
  emit("update:includePaymentUnknown", false)
  emit("update:includeCategoryUnknown", false)
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

      <div v-if="selectedPaymentMethods.length" class="filter-section">
        <div class="filter-section-title">Include unknown? (Payment method)</div>
        <div class="filter-checkbox-grid">
          <label class="filter-checkbox-option">
            <input
              type="radio"
              name="filter-include-payment-unknown"
              :checked="!includePaymentUnknown"
              @change="emit('update:includePaymentUnknown', false)"
            >
            <span>No</span>
          </label>
          <label class="filter-checkbox-option">
            <input
              type="radio"
              name="filter-include-payment-unknown"
              :checked="includePaymentUnknown"
              @change="emit('update:includePaymentUnknown', true)"
            >
            <span>Yes</span>
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

      <div v-if="selectedCategories.length" class="filter-section">
        <div class="filter-section-title">Include unknown? (Category)</div>
        <div class="filter-checkbox-grid">
          <label class="filter-checkbox-option">
            <input
              type="radio"
              name="filter-include-category-unknown"
              :checked="!includeCategoryUnknown"
              @change="emit('update:includeCategoryUnknown', false)"
            >
            <span>No</span>
          </label>
          <label class="filter-checkbox-option">
            <input
              type="radio"
              name="filter-include-category-unknown"
              :checked="includeCategoryUnknown"
              @change="emit('update:includeCategoryUnknown', true)"
            >
            <span>Yes</span>
          </label>
        </div>
      </div>

      <div v-if="sortOptions.length" class="filter-section">
        <div class="filter-section-title">Sort</div>
        <div class="filter-checkbox-grid">
          <label
            v-for="opt in sortOptions"
            :key="opt.value"
            class="filter-checkbox-option"
          >
            <input
              type="radio"
              name="filter-sort"
              :checked="selectedSort === opt.value"
              @change="emit('update:selectedSort', opt.value)"
            >
            <span>{{ opt.label }}</span>
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
