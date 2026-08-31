<template>
  <div class="app-shell">
    <header class="site-header">
      <RouterLink class="brand" to="/">
        <span class="brand-mark">PM</span>
        <span>PayMethodFinder</span>
      </RouterLink>
      <nav aria-label="Main navigation">
        <RouterLink to="/stores">Find stores</RouterLink>
        <RouterLink class="nav-primary" to="/stores/new">Add a store</RouterLink>
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

