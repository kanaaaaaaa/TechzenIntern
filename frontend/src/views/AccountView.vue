<script setup>
import { onMounted, ref } from "vue"
import { useRouter } from "vue-router"

import { clearToken } from "../auth"
import { apiErrorMessage, getAccount, logout } from "../api"

const router = useRouter()

const account = ref(null)
const loading = ref(true)
const loggingOut = ref(false)
const error = ref("")

async function loadAccount() {
  loading.value = true
  error.value = ""

  try {
    account.value = await getAccount()
  } catch (err) {
    error.value = apiErrorMessage(err)
  } finally {
    loading.value = false
  }
}

async function handleLogout() {
  loggingOut.value = true

  try {
    await logout()
  } catch {
  }

  clearToken()
  await router.push({ name: "login" })
}

onMounted(loadAccount)
</script>

<template>
  <section class="account-panel">
    <p class="eyebrow">ACCOUNT</p>

    <h1>Account</h1>

    <div v-if="loading" class="loading-box">
      Loading account…
    </div>

    <p v-else-if="error" class="alert error">
      {{ error }}
    </p>

    <template v-else-if="account">
      <dl class="account-details">
        <div>
          <dt>Username</dt>
          <dd>{{ account.username }}</dd>
        </div>

        <div>
          <dt>Account created</dt>
          <dd>
            {{ new Date(account.date_joined).toLocaleString("en-US") }}
          </dd>
        </div>
      </dl>

      <button
        class="button account-logout-button"
        type="button"
        :disabled="loggingOut"
        @click="handleLogout"
      >
        {{ loggingOut ? "Logging out…" : "Log out" }}
      </button>
    </template>
  </section>
</template>