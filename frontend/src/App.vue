<script setup>
import { computed, onMounted, provide, ref } from "vue"
import { useRoute } from "vue-router"

import { clearToken, getToken } from "./auth"
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
  if (!getToken()) {
    userPoints.value = null
    return
  }
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

        <RouterLink
          v-if="getToken()"
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

<style scoped>
.points-badge {
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 4px 8px;
  background: var(--green);
  color: white;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 600;
}
.points-badge strong {
  font-size: 14px;
}
</style>