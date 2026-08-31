<script setup>
import { computed } from "vue"
import { useRoute, useRouter } from "vue-router"

import { clearToken } from "./auth"

const route = useRoute()
const router = useRouter()
const showNav = computed(() => route.name !== "login")

function lock() {
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
      <nav v-if="showNav" aria-label="Main navigation">
        <RouterLink to="/stores">Find stores</RouterLink>
        <RouterLink class="nav-primary" to="/stores/new">Add a store</RouterLink>
        <button class="nav-lock" type="button" @click="lock">Lock</button>
      </nav>
    </header>

    <main class="page-shell">
      <RouterView />
    </main>

    <footer class="site-footer">
      <span>PayMethodFinder</span>
      <span>A community-maintained payment method database</span>
    </footer>
  </div>
</template>
