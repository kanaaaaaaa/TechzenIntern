<script setup>
import { onMounted, ref } from "vue"

import { listStores } from "../api"

const storeCount = ref(null)

onMounted(async () => {
  try {
    const stores = await listStores()
    storeCount.value = stores.length
  } catch {
    storeCount.value = null
  }
})
</script>

<template>
  <section class="hero">
    <div class="hero-copy">
      <p class="eyebrow">PAYMENT METHOD DIRECTORY</p>
      <h1>At that store,<br>
        <em>what can you pay with?</em>
      </h1>
      <p class="lead">Search the payment methods each store accepts, and keep the information up to date together.</p>
      <div class="hero-actions">
        <RouterLink class="button primary" to="/stores">Search stores</RouterLink>
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

