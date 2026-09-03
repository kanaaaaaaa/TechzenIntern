<script setup>
import { computed, onMounted, reactive, ref } from "vue"
import { useRoute, useRouter } from "vue-router"

import PaymentMethodEditor from "../components/PaymentMethodEditor.vue"
import { apiErrorMessage, getStore, listPaymentMethods, updateStore } from "../api"

const props = defineProps({ id: { type: String, required: true } })
const route = useRoute()
const router = useRouter()
const store = ref(null)
const methods = ref([])
const statuses = reactive({})
const form = reactive({ name: "", address: "" })
const loading = ref(true)
const saving = ref(false)
const error = ref("")
const notice = ref(route.query.created ? "The store has been added." : "")

const confirmedCount = computed(() => Object.values(statuses).filter((status) => status !== "unknown").length)
const listRoute = computed(() => ({
  name: "stores",
  query: route.query.q ? { q: String(route.query.q) } : {},
}))

function updateStatus(id, status) {
  statuses[id] = status
  notice.value = ""
}

async function load() {
  try {
    const [storeData, methodData] = await Promise.all([getStore(props.id), listPaymentMethods()])
    store.value = storeData
    methods.value = methodData
    form.name = storeData.name
    form.address = storeData.address
    methodData.forEach((method) => { statuses[method.id] = "unknown" })
    storeData.payment_methods.forEach((item) => { statuses[item.payment_method.id] = item.status })
  } catch (err) {
    error.value = apiErrorMessage(err)
  } finally {
    loading.value = false
  }
}

async function save() {
  saving.value = true
  error.value = ""
  notice.value = ""
  try {
    store.value = await updateStore(props.id, {
      name: form.name.trim(),
      address: form.address.trim(),
      payment_statuses: methods.value.map((method) => ({ payment_method_id: method.id, status: statuses[method.id] })),
    })
    await router.push(listRoute.value)
  } catch (err) {
    error.value = apiErrorMessage(err)
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <div v-if="loading" class="empty-state">Loading store details…</div>
  <div v-else-if="!store" class="empty-state"><h1>This store cannot be shown</h1><p>{{ error }}</p><RouterLink class="button primary" :to="listRoute">Back to the list</RouterLink></div>
  <template v-else>
    <div class="breadcrumb"><RouterLink :to="listRoute">Stores</RouterLink><span>/</span><span>{{ store.name }}</span></div>
    <section class="detail-heading">
      <div><p class="eyebrow">STORE #{{ store.id }}</p><h1>{{ store.name }}</h1><p>{{ store.address || "No address yet" }}</p></div>
      <div class="confirm-stat"><strong>{{ confirmedCount }}</strong><span>/ {{ methods.length }} confirmed</span></div>
    </section>

    <form class="editor-form" @submit.prevent="save">
      <section class="form-section compact">
        <div class="section-number">01</div>
        <div class="section-content">
          <h2>Store details</h2>
          <div class="field-grid">
            <label>Store name <span>Required</span><input v-model="form.name" required maxlength="160"></label>
            <label>Address <small>Optional</small><input v-model="form.address" maxlength="255"></label>
          </div>
        </div>
      </section>

      <section class="form-section compact">
        <div class="section-number">02</div>
        <div class="section-content">
          <h2>Payment methods</h2>
          <p class="section-note">Pick the current status for each method and save.</p>
          <PaymentMethodEditor :methods="methods" :statuses="statuses" @update-status="updateStatus" />
        </div>
      </section>

      <p v-if="notice" class="alert success">{{ notice }}</p>
      <p v-if="error" class="alert error">{{ error }}</p>
      <div class="form-actions sticky-actions">
        <span>Last updated {{ new Date(store.updated_at).toLocaleString("en-US") }}</span>
        <button class="button primary" type="submit" :disabled="saving || !form.name.trim()">{{ saving ? "Saving…" : "Save changes" }}</button>
      </div>
    </form>
  </template>
</template>
