<template>
  <div class="app-container" :class="{ 'dark-mode': auth.darkMode }">
    <nav v-if="currentRoute !== 'Login'">
      <div class="nav-brand">Tea Production Manager</div>
      <div class="nav-links">
        <router-link to="/status" class="nav-link" :class="{ active: currentRoute === 'Status' }">
          Status
        </router-link>
        <router-link to="/statistics" class="nav-link" :class="{ active: currentRoute === 'Statistics' }">
          Statistics
        </router-link>
        <router-link v-if="auth.isAdmin" to="/events" class="nav-link" :class="{ active: currentRoute === 'Events' }">
          Events
        </router-link>
        <router-link v-if="auth.isAdmin" to="/tea-types" class="nav-link" :class="{ active: currentRoute === 'TeaTypes' }">
          Tea Types
        </router-link>
        <router-link v-if="auth.isAdmin" to="/database" class="nav-link" :class="{ active: currentRoute === 'Database' }">
          Database
        </router-link>
        <button v-if="auth.isAdmin" class="nav-link" @click="handleLogout">Logout</button>
        <button v-else class="nav-link" @click="$router.push('/login')">Login</button>
      </div>
      <div class="nav-controls">
        <span class="mode-indicator" :class="auth.role">{{ auth.role }}</span>
        <button class="dark-toggle" @click="auth.toggleDarkMode()" :title="auth.darkMode ? 'Light mode' : 'Night mode'">
          {{ auth.darkMode ? '☀️' : '🌙' }}
        </button>
      </div>
    </nav>
    <main>
      <router-view />
    </main>
    <footer class="app-footer">
      <div class="footer-content">
        <span>Brewed with 🍵 by <strong>RogDesign</strong></span>
        <span>© {{ currentYear }} RogDesign</span>
        <a href="https://github.com/yomgui1/teamaker" target="_blank" rel="noopener" class="footer-link">
          GitHub
        </a>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from './stores/auth'
import { useApiStore } from './stores/api'

const auth = useAuthStore()
const api = useApiStore()
const route = useRoute()
const router = useRouter()

const currentRoute = computed(() => route.name)
const currentYear = new Date().getFullYear()

onMounted(async () => {
   document.body.classList.toggle('dark-mode', auth.darkMode)
   await auth.checkAuth()
  await Promise.all([
    api.getStatus(),
    api.getTeaTypes(),
    api.getEvents(),
    api.getStatistics()
  ])
})

async function handleLogout() {
  await auth.logout()
  const redirect = route.query.redirect || '/status'
  router.push(redirect)
}
</script>
