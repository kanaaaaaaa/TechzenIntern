<template>
  <div class="app-shell">
    <header class="site-header">
      <RouterLink class="brand" to="/">
        <span class="brand-mark">PM</span>
        <span>PayMethodFinder</span>
      </RouterLink>
    </header>

    <main class="page-shell">
      <RouterView />
    </main>

    <footer v-if="route.name === 'stores'" class="site-footer">
      <RouterLink class="button secondary" to="/stores/new">Add a new store</RouterLink>
    </footer>
  </div>
</template>

<script setup>
import { useRoute } from "vue-router"

const route = useRoute()
</script>
