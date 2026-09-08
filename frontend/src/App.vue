<script setup>
import { computed } from "vue"
import { useRoute, useRouter } from "vue-router"

import { clearToken } from "./auth"

const route = useRoute()
const router = useRouter()

const showHeaderActions = computed(
  () => route.name !== "login" && route.name !== "register"
)

const showMainNav = computed(
  () => route.name !== "home"
)

function logout() {
  clearToken()
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

        <button
          class="account-button"
          type="button"
          aria-label="Account"
          title="Account"
          @click="logout"
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
        </button>
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
