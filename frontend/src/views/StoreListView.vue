<script setup>
import { computed, onMounted, ref } from "vue"
import { useRoute, useRouter } from "vue-router"

import { apiErrorMessage, listStores } from "../api"

const route = useRoute()
const router = useRouter()
const query = ref(String(route.query.q || ""))
const stores = ref([])
const loading = ref(true)
const error = ref("")

const resultLabel = computed(() =>
  loading.value ? "Searching" : `${stores.value.length} ${stores.value.length === 1 ? "store" : "stores"}`,
)

function acceptedMethods(store) {
  return store.payment_methods.filter((item) => item.status === "accepted")
}

async function search() {
  loading.value = true
  error.value = ""
  try {
    stores.value = await listStores({ search: query.value.trim(), ordering: "-updated_at" })
    await router.replace({ name: "stores", query: query.value.trim() ? { q: query.value.trim() } : {} })
  } catch (err) {
    error.value = apiErrorMessage(err)
  } finally {
    loading.value = false
  }
}

onMounted(search)
</script>

<template>
  <section class="page-heading split-heading">
    <div><p class="eyebrow">STORE DIRECTORY</p><h1>Find stores</h1></div>
    <RouterLink class="button primary small" to="/stores/new">＋ Add a store</RouterLink>
  </section>

  <form class="search-panel" @submit.prevent="search">
    <label for="store-search">Store name or address</label>
    <div class="search-row">
      <input id="store-search" v-model="query" placeholder="e.g. Shibuya, Station Market" autofocus>
      <button class="button primary" type="submit">Search</button>
    </div>
  </form>

  <div class="result-head"><span>Results</span><strong>{{ resultLabel }}</strong></div>
  <p v-if="error" class="alert error">{{ error }}</p>
  <div v-else-if="loading" class="empty-state">Loading stores…</div>
  <div v-else-if="stores.length" class="store-grid">
    <RouterLink
      v-for="store in stores"
      :key="store.id"
      class="store-card"
      :to="{ name: 'store-detail', params: { id: store.id }, query: query.trim() ? { q: query.trim() } : {} }"
    >
      <div class="store-card-top">
        <div><h2>{{ store.name }}</h2><p>{{ store.address || "No address yet" }}</p></div>
        <span class="arrow">↗</span>
      </div>
      <div v-if="acceptedMethods(store).length" class="method-tags">
        <span v-for="item in acceptedMethods(store).slice(0, 5)" :key="item.payment_method.id">{{ item.payment_method.name }}</span>
        <span v-if="acceptedMethods(store).length > 5">+{{ acceptedMethods(store).length - 5 }}</span>
      </div>
      <p v-else class="no-methods">No accepted payment methods confirmed yet</p>
      <div class="store-card-foot">Updated {{ new Date(store.updated_at).toLocaleDateString("en-US") }}</div>
    </RouterLink>
  </div>
  <div v-else class="empty-state">
    <h2>No stores match your search</h2>
    <p>Try different keywords, or add a new store.</p>
  </div>
</template>
