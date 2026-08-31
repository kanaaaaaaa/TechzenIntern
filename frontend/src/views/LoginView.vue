<script setup>
import { ref } from "vue"
import { useRoute, useRouter } from "vue-router"

import { apiErrorMessage, unlock } from "../api"
import { setToken } from "../auth"

const route = useRoute()
const router = useRouter()
const password = ref("")
const error = ref("")
const checking = ref(false)

async function submit() {
  checking.value = true
  error.value = ""
  try {
    setToken(await unlock(password.value))
    await router.replace(String(route.query.next || "/"))
  } catch (err) {
    error.value = apiErrorMessage(err)
    password.value = ""
  } finally {
    checking.value = false
  }
}
</script>

<template>
  <section class="login-panel">
    <p class="eyebrow">PROTECTED</p>
    <h1>Enter the password</h1>
    <p>This app is shared with a password. Ask the team if you do not have it.</p>

    <form @submit.prevent="submit">
      <label for="app-password">Password</label>
      <input
        id="app-password"
        v-model="password"
        type="password"
        autocomplete="current-password"
        autofocus
      >
      <p v-if="error" class="alert error">{{ error }}</p>
      <button class="button primary" type="submit" :disabled="checking || !password">
        {{ checking ? "Checking…" : "Unlock" }}
      </button>
    </form>
  </section>
</template>
