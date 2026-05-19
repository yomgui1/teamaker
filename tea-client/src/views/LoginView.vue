<template>
  <div class="login-container">
    <div class="login-card">
      <h1>🍵 Tea Production</h1>
      <p>Manage and monitor tea production</p>

      <div v-if="!auth.initialized" class="setup-form">
        <p class="setup-hint">Admin password not set. Please choose a secure password (minimum 8 characters).</p>
        <div v-if="error" class="alert alert-error">{{ error }}</div>

        <div class="form-group">
          <label for="setup-password">Set Admin Password</label>
          <input
            id="setup-password"
            type="password"
            v-model="setupPassword"
            placeholder="Minimum 8 characters"
            @keyup.enter="handleSetup"
          />
        </div>

        <div class="form-group">
          <label for="setup-confirm">Confirm Password</label>
          <input
            id="setup-confirm"
            type="password"
            v-model="setupConfirm"
            placeholder="Re-enter password"
            @keyup.enter="handleSetup"
          />
        </div>

        <button class="btn btn-primary" style="width: 100%" @click="handleSetup">
          Initialize
        </button>
      </div>

      <template v-else>
        <div v-if="error" class="alert alert-error">{{ error }}</div>

        <div class="form-group">
          <label for="password">Admin Password</label>
          <input
            id="password"
            type="password"
            v-model="password"
            placeholder="Enter admin password"
            @keyup.enter="handleLogin"
          />
        </div>

        <div class="login-buttons">
          <button class="btn btn-primary" style="width: 100%" @click="handleLogin">
            Login as Admin
          </button>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useApiStore } from '../stores/api'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const api = useApiStore()

const password = ref('')
const error = ref('')

const setupPassword = ref('')
const setupConfirm = ref('')

onMounted(() => {
  if (auth.authenticated) {
    const redirect = route.query.redirect || '/status'
    router.push(redirect)
  }
})

async function handleSetup() {
  error.value = ''
  if (setupPassword.value.length < 8) {
    error.value = 'Password must be at least 8 characters'
    return
  }
  if (setupPassword.value !== setupConfirm.value) {
    error.value = 'Passwords do not match'
    return
  }
  try {
    await api.setupPassword(setupPassword.value)
    auth.initialized = true
    setupPassword.value = ''
    setupConfirm.value = ''
  } catch (err) {
    error.value = err.response?.data?.error || 'Setup failed'
  }
}

async function handleLogin() {
  error.value = ''
  try {
    await auth.login(password.value, 'admin')
    await Promise.all([
      api.getStatus(),
      api.getTeaTypes(),
      api.getEvents(),
      api.getStatistics()
    ])
    password.value = ''
    const redirect = route.query.redirect || '/status'
    router.push(redirect)
  } catch (err) {
    error.value = err.response?.data?.error || 'Login failed'
    password.value = ''
  }
}


</script>
