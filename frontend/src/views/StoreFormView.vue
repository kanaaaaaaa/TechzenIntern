<script setup>
import { computed, inject, onMounted, reactive, ref } from "vue"
import { useRouter } from "vue-router"

import PaymentMethodEditor from "../components/PaymentMethodEditor.vue"
import StorePickerMap from "../components/StorePickerMap.vue"
import { STORE_CATEGORIES } from "../categories"
import { apiErrorMessage, createStore, listPaymentMethods } from "../api"

const router = useRouter()
const refreshUserPoints = inject("refreshUserPoints")
const methods = ref([])
const statuses = reactive({})
const form = reactive({ name: "", address: "", latitude: "", longitude: "", category: "" })
const categoryLabel = computed(
  () => STORE_CATEGORIES.find((c) => c.value === form.category)?.label || "No category"
)
const loading = ref(true)
const saving = ref(false)
const confirming = ref(false)
const error = ref("")

const canReview = computed(() => form.name.trim() && !loading.value)
const statusLabels = {
  accepted: "〇",
  not_accepted: "×",
  unknown: "？",
}

function updateStatus(id, status) {
  statuses[id] = status
}

function selectGooglePlace(place) {
  if (place.name) {
    form.name = place.name
  }

  if (place.address) {
    form.address = place.address
  }

  if (
    place.latitude !== null &&
    place.latitude !== undefined
  ) {
    form.latitude =
      Number(place.latitude).toFixed(6)
  }

  if (
    place.longitude !== null &&
    place.longitude !== undefined
  ) {
    form.longitude =
      Number(place.longitude).toFixed(6)
  }
}

function optionalCoordinate(value) {
  const trimmed = String(value).trim()
  return trimmed === "" ? null : trimmed
}

async function load() {
  try {
    methods.value = await listPaymentMethods()
    methods.value.forEach((method) => { statuses[method.id] = "unknown" })
  } catch (err) {
    error.value = apiErrorMessage(err)
  } finally {
    loading.value = false
  }
}

function review() {
  if (!canReview.value) return
  error.value = ""
  confirming.value = true
  window.scrollTo({ top: 0, behavior: "smooth" })
}

function cancel() {
  if (window.history.state && window.history.state.back) {
    router.back()
  } else {
    router.push({ name: "stores" })
  }
}

function cancelReview() {
  error.value = ""
  confirming.value = false
  window.scrollTo({ top: 0, behavior: "smooth" })
}

async function save() {
  saving.value = true
  error.value = ""
  try {
    await createStore({
      name: form.name.trim(),
      address: form.address.trim(),
      latitude: optionalCoordinate(form.latitude),
      longitude: optionalCoordinate(form.longitude),
      category: form.category,
      payment_statuses: methods.value.map((method) => ({
        payment_method_id: method.id,
        status: statuses[method.id],
      })),
    })
    refreshUserPoints?.()
    await router.push({ name: "stores" })
  } catch (err) {
    error.value = apiErrorMessage(err)
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <section v-if="confirming" class="page-heading confirmation-heading">
    <h1>Please confirm the details.</h1>
  </section>

  <form v-if="!confirming" class="editor-form" @submit.prevent="review">
    <section class="form-section">
      <div class="section-number">1</div>
      <div class="section-content">
        <h2>Store details</h2>
        <div class="field-grid">
          <label>Store name <span>Required</span><input v-model="form.name" required maxlength="160" placeholder="e.g. Station Market"></label>
          <label>Address <small>Optional</small><input v-model="form.address" maxlength="255" placeholder="e.g. 1-2-3 Shibuya, Shibuya-ku, Tokyo"></label>
          <label>Latitude <small>Optional</small><input v-model="form.latitude" type="number" min="-90" max="90" step="0.000001" placeholder="e.g. 16.081259"></label>
          <label>Longitude <small>Optional</small><input v-model="form.longitude" type="number" min="-180" max="180" step="0.000001" placeholder="e.g. 108.222577"></label>
          <label>Category <small>Optional</small>
            <select v-model="form.category">
              <option value="">No category</option>
              <option v-for="cat in STORE_CATEGORIES" :key="cat.value" :value="cat.value">{{ cat.label }}</option>
            </select>
          </label>
        </div>
        <StorePickerMap
          @select-place="selectGooglePlace"
        />
      </div>
    </section>

    <section class="form-section">
      <div class="section-number">2</div>
      <div class="section-content">
        <h2>Accepted payment methods</h2>
        <p class="section-note">Leave anything you are unsure about as "?".</p>
        <div v-if="loading" class="loading-box">Loading payment methods…</div>
        <PaymentMethodEditor v-else :methods="methods" :statuses="statuses" @update-status="updateStatus" />
      </div>
    </section>

    <p v-if="error" class="alert error">{{ error }}</p>
    <div class="form-actions">
      <button class="button secondary" type="button" @click="cancel">Cancel</button>
      <button class="button primary" type="submit" :disabled="!canReview">Review this store</button>
    </div>
  </form>

  <form v-else class="editor-form confirmation-form" @submit.prevent="save">
    <section class="form-section">
      <div class="section-number">1</div>
      <div class="section-content">
        <h2>Store details</h2>
        <dl class="review-details">
          <div>
            <dt>Store name</dt>
            <dd>{{ form.name.trim() }}</dd>
          </div>
          <div>
            <dt>Address</dt>
            <dd>{{ form.address.trim() || "No address" }}</dd>
          </div>
          <div>
            <dt>Coordinates</dt>
            <dd>{{ form.latitude !== "" && form.longitude !== "" ? `${form.latitude}, ${form.longitude}` : "No coordinates" }}</dd>
          </div>
          <div>
            <dt>Category</dt>
            <dd>{{ categoryLabel }}</dd>
          </div>
        </dl>
      </div>
    </section>

    <section class="form-section">
      <div class="section-number">2</div>
      <div class="section-content">
        <h2>Payment methods</h2>
        <p class="section-note">These values will be saved with the new store.</p>
        <div class="method-list review-method-list">
          <div v-for="method in methods" :key="method.id" class="method-edit-row">
            <div>
              <strong>{{ method.name }}</strong>
            </div>
            <span :class="['review-status', statuses[method.id]]">{{ statusLabels[statuses[method.id]] }}</span>
          </div>
        </div>
      </div>
    </section>

    <p v-if="error" class="alert error">{{ error }}</p>
    <div class="form-actions confirmation-actions">
      <button class="button secondary" type="button" :disabled="saving" @click="cancelReview">Cancel</button>
      <button class="button primary" type="submit" :disabled="saving">{{ saving ? "Saving…" : "Save Changes" }}</button>
    </div>
  </form>
</template>
