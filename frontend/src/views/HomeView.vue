<script setup>
import { onMounted, ref } from "vue"
import { useRouter } from "vue-router"

import { listStores, ocrImage } from "../api"

const router = useRouter()
const query = ref("")
const storeCount = ref(null)
const cameraInput = ref(null)
const ocrLoading = ref(false)
const ocrError = ref("")

onMounted(async () => {
  try {
    const data = await listStores()
    storeCount.value = data.count
  } catch {
    storeCount.value = null
  }
})

function search() {
  router.push({ name: "stores", query: query.value.trim() ? { q: query.value.trim() } : {} })
}

function openCamera() {
  ocrError.value = ""
  cameraInput.value?.click()
}

async function handlePhoto(event) {
  const file = event.target.files?.[0]
  event.target.value = ""
  if (!file) return

  ocrLoading.value = true
  ocrError.value = ""
  try {
    const { text } = await ocrImage(file)
    // Fill the search box only; the user still has to press Search themselves.
    query.value = (text || "").replace(/\s+/g, " ").trim()
  } catch {
    ocrError.value = "Could not read text from that photo."
  } finally {
    ocrLoading.value = false
  }
}
</script>

<template>
  <section class="hero">
    <div class="hero-copy">
      <h1><span style="white-space: nowrap">Search payment methods</span><br>by store name</h1>
      <form class="search-panel" @submit.prevent="search">
        <label class="visually-hidden" for="home-store-search">Store name or address</label>
        <div class="search-row">
          <button
            type="button"
            class="search-outer-icon"
            :disabled="ocrLoading"
            :aria-label="ocrLoading ? 'Reading photo…' : 'Scan a photo to fill the search box'"
            @click="openCamera"
          >
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M4 8a2 2 0 0 1 2-2h1.5l1-1.5A2 2 0 0 1 10.2 3.5h3.6a2 2 0 0 1 1.7 1L16.5 6H18a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2Z" />
              <circle cx="12" cy="13" r="3.5" />
            </svg>
          </button>
          <input
            ref="cameraInput"
            type="file"
            accept="image/*"
            capture="environment"
            class="visually-hidden"
            @change="handlePhoto"
          >
          <input id="home-store-search" v-model="query" placeholder="Store name or address">
          <button class="button primary" type="submit">Search</button>
        </div>
      </form>
      <p v-if="ocrLoading" class="ocr-status">Reading text from photo…</p>
      <p v-else-if="ocrError" class="ocr-status ocr-status-error">{{ ocrError }}</p>
      <RouterLink class="button secondary nearby-link" to="/stores/nearby">Find nearby registered stores</RouterLink>
      <p class="lead">Please add store information <br class="mobile-break">for everyone</p>
      <div class="hero-actions">
        <RouterLink class="button secondary" to="/stores/new">Add a new store</RouterLink>
      </div>
      <p v-if="storeCount !== null" class="record-count"><strong>{{ storeCount }}</strong> stores listed</p>
    </div>
  </section>
</template>

<style scoped>
.search-row { grid-template-columns: auto 1fr auto; align-items: center; }
.search-outer-icon {
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  padding: 0;
  border: 1px solid var(--line);
  border-radius: 5px;
  background: transparent;
  color: var(--ink);
  cursor: pointer;
}
.search-outer-icon:hover { border-color: var(--green); color: var(--green); }
.search-outer-icon:disabled { opacity: .5; cursor: not-allowed; }
.ocr-status { margin: 6px 0 0; font-size: 13px; color: var(--muted); }
.ocr-status-error { color: var(--red); }
.nearby-link { margin-top: 8px; margin-bottom: 26px; }
</style>

