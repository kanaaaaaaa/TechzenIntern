<script setup>
import { ref } from "vue"
import { RouterLink, useRouter } from "vue-router"

import { apiErrorMessage, register } from "../api"
import { clearToken, setToken } from "../auth"

const router = useRouter()

const username = ref("")
const error = ref("")
const checking = ref(false)

async function submit() {
  checking.value = true
  error.value = ""

  try {
    clearToken()
    const data = await register(username.value)
    setToken(data.token)
    await router.replace("/")
  } catch (err) {
    error.value = apiErrorMessage(err)
  } finally {
    checking.value = false
  }
}
</script>

<template>
  <section class="login-panel">
    <p class="eyebrow">REGISTER</p>
    <h1>Create account</h1>

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
        {{ checking ? "Creating…" : "Create account" }}
      </button>
    </form>

    <p>
      Already have an account?
      <RouterLink to="/login">Login</RouterLink>
    </p>
  </section>
</template>