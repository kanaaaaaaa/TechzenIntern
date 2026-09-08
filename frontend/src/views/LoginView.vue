<script setup>
import { ref } from "vue"
import { RouterLink, useRoute, useRouter } from "vue-router"

import { apiErrorMessage, login } from "../api"
import { clearToken, setToken } from "../auth"

const route = useRoute()
const router = useRouter()

const username = ref("")
const error = ref("")
const checking = ref(false)

async function submit() {
  checking.value = true
  error.value = ""

  try {
    clearToken()
    const data = await login(username.value)
    setToken(data.token)
    await router.replace(String(route.query.next || "/"))
  } catch (err) {
    error.value = apiErrorMessage(err)
  } finally {
    checking.value = false
  }
}
</script>

<template>
  <section class="login-panel">
    <p class="eyebrow">LOGIN</p>
    <h1>Login</h1>

    <form @submit.prevent="submit">
      <label for="username">Username</label>
      <input
        id="username"
        v-model="username"
        type="text"
        autocomplete="username"
        autofocus
      >

      <p v-if="error" class="alert error">{{ error }}</p>

      <button
        class="button primary"
        type="submit"
        :disabled="checking || !username"
      >
        {{ checking ? "Logging in…" : "Login" }}
      </button>
    </form>

    <p>
      Don't have an account?
      <RouterLink to="/register">Create account</RouterLink>
    </p>
  </section>
</template>