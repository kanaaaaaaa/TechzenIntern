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
const confirming = ref(false)
const error = ref("")

const canReview = computed(() => form.name.trim() && !loading.value)
const statusLabels = {
  accepted: "⚪︎",
  not_accepted: "×",
  unknown: "？",
}

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

function review() {
  if (!canReview.value) return
  error.value = ""
  confirming.value = true
  window.scrollTo({ top: 0, behavior: "smooth" })
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
      payment_statuses: methods.value.map((method) => ({
        payment_method_id: method.id,
        status: statuses[method.id],
      })),
    })
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
  <section v-if="!confirming" class="page-heading">
    <p class="eyebrow">NEW STORE</p>
    <h1>Add a store</h1>
    <p>Enter the basic store details and the payment methods you can confirm right now.</p>
  </section>

  <section v-else class="page-heading confirmation-heading">
    <p class="eyebrow">CONFIRM NEW STORE</p>
    <h1>Please confirm the details.</h1>
    <p>Check the information below. To make a change, select Cancel and return to the previous step.</p>
  </section>

  <form v-if="!confirming" class="editor-form" @submit.prevent="review">
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
      <button class="button primary" type="submit" :disabled="!canReview">Review this store</button>
    </div>
  </form>

  <form v-else class="editor-form confirmation-form" @submit.prevent="save">
    <section class="form-section">
      <div class="section-number">01</div>
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
        </dl>
      </div>
    </section>

    <section class="form-section">
      <div class="section-number">02</div>
      <div class="section-content">
        <h2>Payment methods</h2>
        <p class="section-note">These values will be saved with the new store.</p>
        <div class="method-list review-method-list">
          <div v-for="method in methods" :key="method.id" class="method-edit-row">
            <div>
              <strong>{{ method.name }}</strong>
              <small>{{ method.code }}</small>
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
