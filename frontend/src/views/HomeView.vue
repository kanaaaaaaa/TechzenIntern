<script setup>
import { onMounted, ref } from "vue"
import { useRouter } from "vue-router"

import { listStores } from "../api"

const router = useRouter()
const query = ref("")
const storeCount = ref(null)

onMounted(async () => {
  try {
    const stores = await listStores()
    storeCount.value = stores.length
  } catch {
    storeCount.value = null
  }
})

function search() {
  router.push({ name: "stores", query: query.value.trim() ? { q: query.value.trim() } : {} })
}
</script>

<template>
  <section class="hero">
    <div class="hero-copy">
      <h1><span style="white-space: nowrap">Search payment methods</span><br>by store name.</h1>
      <form class="search-panel" @submit.prevent="search">
        <label class="visually-hidden" for="home-store-search">Store name or address</label>
        <div class="search-row">
          <input id="home-store-search" v-model="query" placeholder="Store name or address">
          <button class="button primary" type="submit">Search</button>
        </div>
      </form>
      <p class="lead">Please add store information for everyone.</p>
      <div class="hero-actions">
        <RouterLink class="button secondary" to="/stores/new">Add a new store</RouterLink>
      </div>
      <p v-if="storeCount !== null" class="record-count"><strong>{{ storeCount }}</strong> stores listed</p>
    </div>
  </section>
</template>

