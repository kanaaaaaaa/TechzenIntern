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
      <p class="lead">Add store information.</p>
      <div class="hero-actions">
        <RouterLink class="button secondary" to="/stores/new">Add a new store</RouterLink>
      </div>
      <p v-if="storeCount !== null" class="record-count"><strong>{{ storeCount }}</strong> stores listed</p>
    </div>

    <div class="finder-card" aria-hidden="true">
      <div class="finder-top"><span>SEARCH RESULT</span><span class="live-dot">LIVE</span></div>
      <h2>Station Market</h2>
      <p>Shibuya, Tokyo</p>
      <div class="mock-method accepted"><span>Cash</span><strong>Accepted</strong></div>
      <div class="mock-method accepted"><span>Credit card</span><strong>Accepted</strong></div>
      <div class="mock-method unknown"><span>E-money</span><strong>Unknown</strong></div>
      <div class="finder-foot">LAST UPDATED · TODAY</div>
    </div>
  </section>

  <section class="feature-grid">
    <article><span>01</span><h2>Find a store</h2><p>Search quickly by store name or address.</p></article>
    <article><span>02</span><h2>Check payment methods</h2><p>Accepted, not accepted and unknown are shown separately.</p></article>
    <article><span>03</span><h2>Update the details</h2><p>Anything that changed can be edited from the store page.</p></article>
  </section>
</template>

