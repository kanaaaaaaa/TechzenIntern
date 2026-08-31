<script setup>
import { computed, onMounted, reactive, ref } from "vue"
import { useRouter } from "vue-router"

import PaymentMethodEditor from "../components/PaymentMethodEditor.vue"
import { apiErrorMessage, createStore, listPaymentMethods } from "../api"

const router = useRouter()
const methods = ref([])
const statuses = reactive({})
const form = reactive({ name: "", address: "" })
const loading = ref(true)
const saving = ref(false)
const error = ref("")

const canSubmit = computed(() => form.name.trim() && !loading.value && !saving.value)

function updateStatus(id, status) {
  statuses[id] = status
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

async function submit() {
  saving.value = true
  error.value = ""
  try {
    const created = await createStore({
      name: form.name.trim(),
      address: form.address.trim(),
      payment_statuses: methods.value.map((method) => ({
        payment_method_id: method.id,
        status: statuses[method.id],
      })),
    })
    await router.push({ name: "store-detail", params: { id: created.id }, query: { created: "1" } })
  } catch (err) {
    error.value = apiErrorMessage(err)
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <section class="page-heading">
    <p class="eyebrow">NEW STORE</p>
    <h1>Add a store</h1>
    <p>Enter the basic store details and the payment methods you can confirm right now.</p>
  </section>

  <form class="editor-form" @submit.prevent="submit">
    <section class="form-section">
      <div class="section-number">01</div>
      <div class="section-content">
        <h2>Store details</h2>
        <div class="field-grid">
          <label>Store name <span>Required</span><input v-model="form.name" required maxlength="160" placeholder="e.g. Station Market"></label>
          <label>Address <small>Optional</small><input v-model="form.address" maxlength="255" placeholder="e.g. 1-2-3 Shibuya, Shibuya-ku, Tokyo"></label>
        </div>
      </div>
    </section>

    <section class="form-section">
      <div class="section-number">02</div>
      <div class="section-content">
        <h2>Accepted payment methods</h2>
        <p class="section-note">Leave anything you are unsure about as "Unknown".</p>
        <div v-if="loading" class="loading-box">Loading payment methods…</div>
        <PaymentMethodEditor v-else :methods="methods" :statuses="statuses" @update-status="updateStatus" />
      </div>
    </section>

    <p v-if="error" class="alert error">{{ error }}</p>
    <div class="form-actions">
      <RouterLink class="button secondary" to="/stores">Cancel</RouterLink>
      <button class="button primary" type="submit" :disabled="!canSubmit">{{ saving ? "Saving…" : "Add this store" }}</button>
    </div>
  </form>
</template>

