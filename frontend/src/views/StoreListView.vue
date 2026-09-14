<script setup>
import { computed, onMounted, ref } from "vue"
import { useRoute, useRouter } from "vue-router"

import CategoryFilterBox from "../components/CategoryFilterBox.vue"
import {
  api,
  apiErrorMessage,
  createStoreComment,
  deleteStore,
  listPaymentMethods,
  listStoreComments,
  listStores,
  submitStoreFeedback,
  updateStoreComment,
} from "../api"
import { isUnlocked } from "../auth"

const route = useRoute()
const router = useRouter()

const query = ref(String(route.query.q || ""))
const paymentMethods = ref([])
const selectedMethods = ref(new Set())
const selectedCategories = ref([])
const stores = ref([])
const totalCount = ref(0)
const nextPageUrl = ref(null)
const loading = ref(true)
const loadingMore = ref(false)
const deletingId = ref(null)
const votingId = ref(null)

const openVotePrompt = ref(null)
const openCommentId = ref(null)
const loadingCommentsId = ref(null)
const postingCommentId = ref(null)
const commentsByStore = ref({})
const commentDrafts = ref({})
const editingCommentId = ref(null)
const editCommentDraft = ref("")
const error = ref("")


const resultLabel = computed(() =>
  loading.value ? "Searching" : `${totalCount.value} store hits`,
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
    const params = {
      search: query.value.trim(),
      ordering: "-updated_at",
    }

    if (selectedMethods.value.size > 0) {
      params.payment_methods = Array.from(selectedMethods.value).join(",")
      params.payment_method_status = "accepted"
    }

    if (selectedCategories.value.length > 0) {
      params.categories = selectedCategories.value.join(",")
    }

    const data = await listStores(params)

    stores.value = data.results
    totalCount.value = data.count
    nextPageUrl.value = data.next

    const newQuery = {}
    if (query.value.trim()) newQuery.q = query.value.trim()
    if (selectedMethods.value.size > 0) newQuery.methods = Array.from(selectedMethods.value).join(",")
    if (selectedCategories.value.length > 0) newQuery.categories = selectedCategories.value.join(",")

    await router.replace({
      name: "stores",
      query: newQuery,
    })
  } catch (err) {
    error.value = apiErrorMessage(err)
  } finally {
    loading.value = false
  }
}

async function loadMore() {
  if (!nextPageUrl.value || loadingMore.value) return

  loadingMore.value = true
  error.value = ""

  try {
    const url = new URL(nextPageUrl.value, window.location.origin)
    if (selectedMethods.value.size > 0) {
      url.searchParams.set("payment_methods", Array.from(selectedMethods.value).join(","))
      url.searchParams.set("payment_method_status", "accepted")
    }
    if (selectedCategories.value.length > 0) {
      url.searchParams.set("categories", selectedCategories.value.join(","))
    }
    const response = await api.get(url.toString())
    stores.value = [...stores.value, ...response.data.results]
    nextPageUrl.value = response.data.next
  } catch (err) {
    error.value = apiErrorMessage(err)
  } finally {
    loadingMore.value = false
  }
}

async function loadPaymentMethods() {
  try {
    const data = await listPaymentMethods()
    paymentMethods.value = data
  } catch (err) {
    console.error("Failed to load payment methods:", err)
  }
}

function toggleMethod(methodId) {
  const newSet = new Set(selectedMethods.value)
  if (newSet.has(methodId)) {
    newSet.delete(methodId)
  } else {
    newSet.add(methodId)
  }
  selectedMethods.value = newSet
  search()
}

function clearFilters() {
  selectedMethods.value.clear()
  search()
}

function requireLogin() {
  router.push({ name: "login", query: { next: route.fullPath } })
}

async function vote(store, voteType) {
  if (!isUnlocked()) {
    const isSameButton =
      openVotePrompt.value?.storeId === store.id &&
      openVotePrompt.value?.voteType === voteType

    openVotePrompt.value = isSameButton
      ? null
      : { storeId: store.id, voteType }
    return
  }

  const nextVote =
    store.my_feedback === voteType ? null : voteType

  votingId.value = store.id
  error.value = ""

  try {
    const result = await submitStoreFeedback(
      store.id,
      nextVote,
    )

    store.helpful_count = result.helpful_count
    store.not_helpful_count = result.not_helpful_count
    store.my_feedback = result.my_feedback
  } catch (err) {
    error.value = apiErrorMessage(err)
  } finally {
    votingId.value = null
  }
}

async function toggleComments(store) {
  if (openCommentId.value === store.id) {
    openCommentId.value = null
    return
  }

  openCommentId.value = store.id

  if (commentsByStore.value[store.id]) {
    return
  }

  loadingCommentsId.value = store.id
  error.value = ""

  try {
    commentsByStore.value[store.id] =
      await listStoreComments(store.id)
  } catch (err) {
    error.value = apiErrorMessage(err)
  } finally {
    loadingCommentsId.value = null
  }
}

async function postComment(store) {
  if (!isUnlocked()) {
    requireLogin()
    return
  }

  const text = String(
    commentDrafts.value[store.id] || "",
  ).trim()

  if (!text) return

  postingCommentId.value = store.id
  error.value = ""

  try {
    const comment = await createStoreComment(
      store.id,
      text,
    )

    commentsByStore.value[store.id] = [
      comment,
      ...(commentsByStore.value[store.id] || []),
    ]

    store.comment_count += 1
    commentDrafts.value[store.id] = ""
  } catch (err) {
    error.value = apiErrorMessage(err)
  } finally {
    postingCommentId.value = null
  }
}

function startEditComment(comment) {
  editingCommentId.value = comment.id
  editCommentDraft.value = comment.text
}

function cancelEditComment() {
  editingCommentId.value = null
  editCommentDraft.value = ""
}

async function saveComment(store) {
  const text = editCommentDraft.value.trim()

  if (!text) return

  postingCommentId.value = store.id
  error.value = ""

  try {
    const updated = await updateStoreComment(store.id, text)

    commentsByStore.value[store.id] =
      commentsByStore.value[store.id].map((comment) =>
        comment.id === updated.id ? updated : comment
      )

    editingCommentId.value = null
    editCommentDraft.value = ""
  } catch (err) {
    error.value = apiErrorMessage(err)
  } finally {
    postingCommentId.value = null
  }
}

async function removeStore(store) {
  const confirmed = window.confirm(
    `Delete "${store.name}"?\n\nThis action cannot be undone.`,
  )

  if (!confirmed) return

  deletingId.value = store.id
  error.value = ""

  try {
    await deleteStore(store.id)

    stores.value = stores.value.filter(
      (item) => item.id !== store.id,
    )
  } catch (err) {
    error.value = apiErrorMessage(err)
  } finally {
    deletingId.value = null
  }
}

onMounted(async () => {
  await loadPaymentMethods()

  const methodsParam = route.query.methods
  if (methodsParam) {
    const methodIds = String(methodsParam).split(",").map(Number).filter(Boolean)
    methodIds.forEach((id) => selectedMethods.value.add(id))
  }

  const categoriesParam = route.query.categories
  if (categoriesParam) {
    selectedCategories.value = String(categoriesParam).split(",").filter(Boolean)
  }

  search()
})
</script>
<template>
  <form class="search-panel" @submit.prevent="search">
    <label class="visually-hidden" for="store-search">
      Store name or address
    </label>

    <div class="search-row">
      <input
        id="store-search"
        v-model="query"
        placeholder="Store name or address"
        autofocus
      >
      <button class="button primary" type="submit">
        Search
      </button>
    </div>
  </form>

  <div v-if="paymentMethods.length" class="method-filter">
    <div class="method-filter-label">Filter by payment method:</div>
    <div class="method-filter-buttons">
      <button
        v-for="method in paymentMethods"
        :key="method.id"
        type="button"
        class="method-filter-button"
        :class="{ active: selectedMethods.has(method.id) }"
        @click="toggleMethod(method.id)"
        :aria-pressed="selectedMethods.has(method.id)"
      >
        {{ method.name }}
      </button>
      <button
        v-if="selectedMethods.size > 0"
        type="button"
        class="method-filter-button clear"
        @click="clearFilters"
      >
        Clear
      </button>
    </div>

    <CategoryFilterBox
      v-model="selectedCategories"
      @update:model-value="search"
    />
  </div>

  <div class="result-head">
    <strong>{{ resultLabel }}</strong>
  </div>

  <p v-if="error" class="alert error">
    {{ error }}
  </p>

  <div v-if="loading" class="empty-state">
    Loading stores…
  </div>

  <div v-else-if="stores.length" class="store-grid">
    <article
      v-for="store in stores"
      :key="store.id"
      class="store-card"
    >
      <RouterLink
        class="store-card-link"
        :to="{
          name: 'store-detail',
          params: { id: store.id },
          query: query.trim() ? { q: query.trim() } : {}
        }"
      >
        <div class="store-card-top">
          <div>
            <h2>{{ store.name }}</h2>

            <div
              v-if="store.payment_methods.length"
              class="method-tags"
            >
              <span
                v-for="item in store.payment_methods"
                :key="item.payment_method.id"
                :class="item.status"
              >
                {{ statusSymbols[item.status] }}｜{{ item.payment_method.name }}
              </span>
            </div>

            <p v-else class="no-methods">
              No accepted payment methods confirmed yet
            </p>

            <span class="store-category-tag">
              {{ store.category_label || "Unknown" }}
            </span>

            <p>
              {{ store.address || "No address yet" }}
            </p>

            <p
              v-if="
                store.latitude !== null &&
                store.longitude !== null
              "
            >
              {{ store.latitude }}, {{ store.longitude }}
            </p>
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
              <path
                d="M16.5 3.5a2.1 2.1 0 0 1 3 3L8 18l-4 1 1-4Z"
              />
            </svg>

            <span class="edit-label">
              Edit
            </span>
          </span>
        </div>
      </RouterLink>

      <div class="store-card-foot">
        <div class="store-card-meta">
          <span>
            Updated
            {{ new Date(store.updated_at).toLocaleDateString("en-US") }}
          </span>

          <button
            class="store-delete-button"
            type="button"
            :disabled="deletingId !== null"
            @click="removeStore(store)"
          >
            {{
              deletingId === store.id
                ? "Deleting…"
                : "Delete"
            }}
          </button>
        </div>

        <div class="store-feedback">
          <span class="feedback-question">
            Did this information help?
          </span>

          <div class="feedback-buttons">
            <!-- Good -->
            <button
              type="button"
              class="feedback-button"
              :class="{
                active: store.my_feedback === 'helpful'
              }"
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
                <path
                  d="M7 20h10.5a2 2 0 0 0 2-1.6l1.4-7A2 2 0 0 0 19 9h-5l1-4a2 2 0 0 0-3.8-1.2L7 10"
                />
              </svg>

              <span>
                {{ store.helpful_count }}
              </span>
            </button>

            <!-- Bad -->
            <button
              type="button"
              class="feedback-button"
              :class="{
                active: store.my_feedback === 'not_helpful'
              }"
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
                <path
                  d="M7 4h10.5a2 2 0 0 1 2 1.6l1.4 7A2 2 0 0 1 19 15h-5l1 4a2 2 0 0 1-3.8 1.2L7 14"
                />
              </svg>

              <span>
                {{ store.not_helpful_count }}
              </span>
            </button>

            <!-- Comment -->
            <button
              type="button"
              class="feedback-button"
              :class="{
                active: openCommentId === store.id
              }"
              :disabled="loadingCommentsId === store.id"
              aria-label="Comments"
              @click="toggleComments(store)"
            >
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <path
                  d="M21 15a4 4 0 0 1-4 4H8l-5 3V7a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4Z"
                />
              </svg>

              <span>
                {{ store.comment_count }}
              </span>
            </button>
          </div>
        </div>

        <!-- Vote login prompt -->
        <div
          v-if="openVotePrompt?.storeId === store.id"
          class="store-comments"
        >
          <p class="comment-login-prompt">
            <RouterLink :to="{ name: 'login', query: { next: route.fullPath } }">Login</RouterLink>
            to vote.
          </p>
        </div>

        <!-- Comment area -->
        <div
          v-if="openCommentId === store.id"
          class="store-comments"
        >
          <p v-if="!isUnlocked()" class="comment-login-prompt">
            <RouterLink :to="{ name: 'login', query: { next: route.fullPath } }">Login</RouterLink>
            to post a comment.
          </p>

          <form
            v-else-if="
              loadingCommentsId !== store.id &&
              !commentsByStore[store.id]?.some(comment => comment.is_mine)
            "
            class="comment-form"
            @submit.prevent="postComment(store)"
          >
            <textarea
              v-model="commentDrafts[store.id]"
              maxlength="500"
              rows="3"
              placeholder="Write a comment..."
            ></textarea>

            <button
              class="button primary comment-post-button"
              type="submit"
              :disabled="
                postingCommentId === store.id ||
                !String(commentDrafts[store.id] || '').trim()
              "
            >
              {{ postingCommentId === store.id ? "Posting…" : "Post" }}
            </button>
          </form>

          <div
            v-if="loadingCommentsId === store.id"
            class="comment-loading"
          >
            Loading comments…
          </div>

          <div
            v-else-if="commentsByStore[store.id]?.length"
            class="comment-list"
          >
            <article
              v-for="comment in commentsByStore[store.id]"
              :key="comment.id"
              class="comment-item"
            >
              <div class="comment-head">
                <strong>{{ comment.username }}</strong>

                <div class="comment-head-right">
                  <span>
                    {{ new Date(comment.updated_at).toLocaleString("en-US") }}
                  </span>

                  <button
                    v-if="comment.is_mine && editingCommentId !== comment.id"
                    type="button"
                    class="comment-edit-button"
                    @click="startEditComment(comment)"
                  >
                    Edit
                  </button>
                </div>
              </div>

              <div v-if="editingCommentId === comment.id">
                <textarea
                  v-model="editCommentDraft"
                  maxlength="500"
                  rows="3"
                  class="comment-edit-textarea"
                ></textarea>

                <div class="comment-edit-actions">
                  <button
                    type="button"
                    class="button secondary small"
                    @click="cancelEditComment"
                  >
                    Cancel
                  </button>

                  <button
                    type="button"
                    class="button primary small"
                    :disabled="
                      postingCommentId === store.id ||
                      !editCommentDraft.trim()
                    "
                    @click="saveComment(store)"
                  >
                    {{ postingCommentId === store.id ? "Saving…" : "Save" }}
                  </button>
                </div>
              </div>

              <p v-else>
                {{ comment.text }}
              </p>
            </article>
          </div>

          <p
            v-else
            class="no-comments"
          >
            No comments yet.
          </p>
        </div>
      </div>
    </article>
  </div>

  <div v-else class="empty-state">
    <h2>
      No stores match your search
    </h2>

    <p>
      Try different keywords, or add a new store.
    </p>

    <RouterLink
      class="button secondary"
      to="/stores/new"
    >
      Add a new store
    </RouterLink>
  </div>

  <div v-if="!loading && stores.length && nextPageUrl" class="load-more-row">
    <button
      type="button"
      class="button secondary"
      :disabled="loadingMore"
      @click="loadMore"
    >
      {{ loadingMore ? "Loading…" : "Load more" }}
    </button>
  </div>
</template>
