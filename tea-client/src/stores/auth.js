import { defineStore } from 'pinia'
import axios from 'axios'

export const useAuthStore = defineStore('auth', {
  state: () => ({
     authenticated: false,
     role: 'guest',
     initialized: false,
     darkMode: false
   }),
  actions: {
  async checkAuth() {
        try {
          const res = await axios.get('/api/v1/auth/me')
          this.authenticated = res.data.authenticated
          this.role = res.data.role
          this.initialized = res.data.initialized
        } catch {
          this.authenticated = false
          this.role = 'guest'
          this.initialized = false
        }
      },
  async login(password, role = 'admin') {
       try {
         const res = await axios.post('/api/v1/auth/login', { password, role })
         this.authenticated = res.data.authenticated
         this.role = res.data.role
         this.initialized = res.data.initialized
         return res.data
       } catch (err) {
         throw err
       }
     },
    async guestLogin() {
       try {
         const res = await axios.post('/api/v1/auth/login', { role: 'guest' })
         this.authenticated = res.data.authenticated
         this.role = res.data.role
         this.initialized = res.data.initialized
         return res.data
       } catch (err) {
         throw err
       }
     },
async logout() {
        this.initialized = true
        try {
          await axios.delete('/api/v1/auth/logout')
        } catch {}
        this.authenticated = false
        this.role = 'guest'
      },
    toggleDarkMode() {
      this.darkMode = !this.darkMode
      document.body.classList.toggle('dark-mode', this.darkMode)
    }
  },
  getters: {
    isAdmin: (state) => state.role === 'admin'
  }
})
