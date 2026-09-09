<script setup>
import { onMounted, ref } from "vue"
import { useRouter } from "vue-router"

import { listStores, getUserPoints } from "../api"

const router = useRouter()
const query = ref("")
const storeCount = ref(null)
//追加
const userPoints = ref(null) // ポイントを保持する変数

onMounted(async () => {
  try {
    const stores = await listStores()
    storeCount.value = stores.length
  } catch {
    storeCount.value = null
  }

  // ポイント情報の取得を追加
  try {
    const data = await getUserPoints()
    userPoints.value = data.total_points
  } catch {
    userPoints.value = null
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
      <p class="lead">Please add store information <br class="mobile-break">for everyone.</p>
      <div class="hero-actions">
        <RouterLink class="button secondary" to="/stores/new">Add a new store</RouterLink>
      </div>
      <p v-if="storeCount !== null" class="record-count"><strong>{{ storeCount }}</strong> stores listed</p>
      <p v-if="userPoints !== null" class="user-points"><strong>{{ userPoints }}</strong>p</p>
    </div>
  </section>
</template>

