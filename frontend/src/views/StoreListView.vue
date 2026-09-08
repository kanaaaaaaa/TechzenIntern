<script setup>
import { computed, onMounted, ref } from "vue"
import { useRoute, useRouter } from "vue-router"

import { apiErrorMessage, deleteStore, listStores, submitStoreFeedback } from "../api"

const route = useRoute()
const router = useRouter()
const query = ref(String(route.query.q || ""))
const stores = ref([])
const loading = ref(true)
const deletingId = ref(null)
const votingId = ref(null)
const error = ref("")

const resultLabel = computed(() =>
  loading.value ? "Searching" : `${stores.value.length} store hits`,
)

const statusSymbols = {
  accepted: "〇",
  not_accepted: "×",
  unknown: "？",
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

async function vote(store, voteType) {
  const nextVote = store.my_feedback === voteType ? null : voteType

  votingId.value = store.id
  error.value = ""

  try {
    const result = await submitStoreFeedback(store.id, nextVote)
    store.helpful_count = result.helpful_count
    store.not_helpful_count = result.not_helpful_count
    store.my_feedback = result.my_feedback
  } catch (err) {
    error.value = apiErrorMessage(err)
  } finally {
    votingId.value = null
  }
}

async function removeStore(store) {
  const confirmed = window.confirm(`Delete "${store.name}"?\n\nThis action cannot be undone.`)
  if (!confirmed) return

  deletingId.value = store.id
  error.value = ""
  try {
    await deleteStore(store.id)
    stores.value = stores.value.filter((item) => item.id !== store.id)
  } catch (err) {
    error.value = apiErrorMessage(err)
  } finally {
    deletingId.value = null
  }
}

onMounted(search)
</script>

<template>
  <form class="search-panel" @submit.prevent="search">
    <label class="visually-hidden" for="store-search">Store name or address</label>
    <div class="search-row">
      <input id="store-search" v-model="query" placeholder="Store name or address" autofocus>
      <button class="button primary" type="submit">Search</button>
    </div>
  </form>

  <div class="result-head"><strong>{{ resultLabel }}</strong></div>
  <p v-if="error" class="alert error">{{ error }}</p>
  <div v-if="loading" class="empty-state">Loading stores…</div>
  <div v-else-if="stores.length" class="store-grid">
    <article
      v-for="store in stores"
      :key="store.id"
      class="store-card"
    >
      <RouterLink
        class="store-card-link"
        :to="{ name: 'store-detail', params: { id: store.id }, query: query.trim() ? { q: query.trim() } : {} }"
      >
        <div class="store-card-top">
          <div>
            <h2>{{ store.name }}</h2>
            <p>{{ store.address || "No address yet" }}</p>
            <p v-if="store.latitude !== null && store.longitude !== null">{{ store.latitude }}, {{ store.longitude }}</p>
          </div>
          <span class="arrow" aria-label="Edit">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d="M12 20h9" />
              <path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L8 18l-4 1 1-4Z" />
              </svg>
            <span class="edit-label">Edit</span>
        </span>
        </div>
        <div v-if="store.payment_methods.length" class="method-tags">
          <span v-for="item in store.payment_methods" :key="item.payment_method.id" :class="item.status">{{ statusSymbols[item.status] }}｜{{ item.payment_method.name }}</span>
        </div>
        <p v-else class="no-methods">No accepted payment methods confirmed yet</p>
      </RouterLink>
      <div class="store-card-foot">
        <div class="store-card-meta">
          <span>Updated {{ new Date(store.updated_at).toLocaleDateString("en-US") }}</span>

          <button
            class="store-delete-button"
            type="button"
            :disabled="deletingId !== null"
            @click="removeStore(store)"
          >
            {{ deletingId === store.id ? "Deleting…" : "Delete" }}
          </button>
        </div>

        <div class="store-feedback">
          <span class="feedback-question">Did this information help?</span>

          <div class="feedback-buttons">
            <button
              type="button"
              class="feedback-button"
              :class="{ active: store.my_feedback === 'helpful' }"
              :disabled="votingId === store.id"
              aria-label="Helpful"
              @click="vote(store, 'helpful')"
            >
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <path d="M7 10v12H3V10h4Z" />
                <path d="M7 20h10.5a2 2 0 0 0 2-1.6l1.4-7A2 2 0 0 0 19 9h-5l1-4a2 2 0 0 0-3.8-1.2L7 10" />
              </svg>
              <span>{{ store.helpful_count }}</span>
            </button>

            <button
              type="button"
              class="feedback-button"
              :class="{ active: store.my_feedback === 'not_helpful' }"
              :disabled="votingId === store.id"
              aria-label="Not helpful"
              @click="vote(store, 'not_helpful')"
            >
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <path d="M7 14V2H3v12h4Z" />
                <path d="M7 4h10.5a2 2 0 0 1 2 1.6l1.4 7A2 2 0 0 1 19 15h-5l1 4a2 2 0 0 1-3.8 1.2L7 14" />
              </svg>
              <span>{{ store.not_helpful_count }}</span>
            </button>
          </div>
        </div>
      </div>
    </article>
  </div>
  <div v-else class="empty-state">
    <h2>No stores match your search</h2>
    <p>Try different keywords, or add a new store.</p>
    <RouterLink class="button secondary" to="/stores/new">Add a new store</RouterLink>
  </div>
</template>
