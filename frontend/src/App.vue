<script setup>
import { computed, onMounted, provide, ref } from "vue"
import { useRoute, useRouter } from "vue-router"

import { clearToken } from "./auth"
import { getUserPoints } from "./api"

const route = useRoute()

const showHeaderActions = computed(
  () => route.name !== "login" && route.name !== "register"
)

const showMainNav = computed(
  () => route.name !== "home" && route.name !== "store-new" && route.name !== "stores"
)

const userPoints = ref(null)

async function refreshUserPoints() {
  try {
    const data = await getUserPoints()
    userPoints.value = data.total_points
  } catch {
    userPoints.value = null
  }
}

onMounted(refreshUserPoints)

provide("refreshUserPoints", refreshUserPoints)

function logout() {
  clearToken()
  userPoints.value = null
  router.push({ name: "login" })
}
</script>

<template>
  <div class="app-shell">
    <header class="site-header">
      <RouterLink class="brand" to="/">
        <span class="brand-mark">PM</span>
        <span>PayMethodFinder</span>
      </RouterLink>

      <nav v-if="showHeaderActions" aria-label="Main navigation">
        <template v-if="showMainNav">
          <RouterLink to="/stores">Find stores</RouterLink>

          <RouterLink class="nav-primary" to="/stores/new">
            Add a store
          </RouterLink>
        </template>

        <span v-if="userPoints !== null" class="points-badge" title="Your points">
          <strong>{{ userPoints }}</strong>p
        </span>

        <button
          class="account-button"
          to="/account"
          aria-label="Account"
          title="Account"
        >
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <circle cx="12" cy="8" r="4" />
            <path d="M4 21a8 8 0 0 1 16 0" />
          </svg>
        </RouterLink>

        <RouterLink v-else to="/login">
          Login
        </RouterLink>
      </nav>
    </header>

    <main class="page-shell">
      <RouterView />
    </main>

    <footer v-if="route.name === 'stores'" class="site-footer">
      <RouterLink class="button secondary" to="/stores/new">
        Add a new store
      </RouterLink>
    </footer>
  </div>
</template>