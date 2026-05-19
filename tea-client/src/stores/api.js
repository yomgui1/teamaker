import { defineStore } from 'pinia'
import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE_URL || ''

axios.defaults.baseURL = API_BASE

axios.interceptors.request.use(config => {
  const csrf = document.cookie
    .split('; ')
    .find(row => row.startsWith('csrf_token='))
    ?.split('=')[1]
  if (csrf) config.headers['X-CSRF-Token'] = csrf
  return config
})

export const useApiStore = defineStore('api', {
  state: () => ({
    status: null,
    teaTypes: [],
    events: [],
    statistics: [],
    loading: false,
    error: null
  }),
  actions: {
    async getStatus() {
      try {
        this.loading = true
        const res = await axios.get('/api/v1/status')
        this.status = res.data
        return res.data
      } catch (err) {
        this.error = err.message
        throw err
      } finally {
        this.loading = false
      }
    },
    async getTeaTypes() {
      try {
        this.loading = true
        const res = await axios.get('/api/v1/tea-types')
        this.teaTypes = res.data.tea_types || []
        return res.data.tea_types
      } catch (err) {
        this.error = err.message
        throw err
      } finally {
        this.loading = false
      }
    },
    async getEvents(limit = 50) {
      try {
        this.loading = true
        const res = await axios.get('/api/v1/events', { params: { limit } })
        this.events = res.data.events || []
        return res.data.events
      } catch (err) {
        this.error = err.message
        throw err
      } finally {
        this.loading = false
      }
    },
    async getStatistics() {
      try {
        this.loading = true
        const res = await axios.get('/api/v1/statistics')
        this.statistics = res.data.statistics || []
        return res.data.statistics
      } catch (err) {
        this.error = err.message
        throw err
      } finally {
        this.loading = false
      }
    },
    async startBrewing(teaType) {
      try {
        const res = await axios.post('/api/v1/events/brewing/start', { tea_type: teaType })
        await this.getStatus()
        return res.data
      } catch (err) {
        this.error = err.message
        throw err
      }
    },
    async completeBrewing(teaType) {
      try {
        const res = await axios.post('/api/v1/events/brewing/complete', { tea_type: teaType })
        await this.getStatus()
        return res.data
      } catch (err) {
        this.error = err.message
        throw err
      }
    },
    async cancelBrewing(teaType) {
      try {
        const res = await axios.post('/api/v1/events/brewing/cancel', { tea_type: teaType })
        await this.getStatus()
        return res.data
      } catch (err) {
        this.error = err.message
        throw err
      }
    },
    async createTeaType(name, image) {
      try {
        const res = await axios.post('/api/v1/tea-types', { name, image })
        await this.getTeaTypes()
        return res.data
      } catch (err) {
        this.error = err.message
        throw err
      }
    },
    async updateTeaType(id, data) {
      try {
        const res = await axios.put(`/api/v1/tea-types?id=${id}`, data)
        await this.getTeaTypes()
        return res.data
      } catch (err) {
        this.error = err.message
        throw err
      }
    },
    async deleteTeaType(id) {
      try {
        const res = await axios.delete(`/api/v1/tea-types?id=${id}`)
        await this.getTeaTypes()
        return res.data
      } catch (err) {
        this.error = err.message
        throw err
      }
    },
    async deleteEvent(id) {
      try {
        const res = await axios.delete(`/api/v1/events?id=${id}`)
        await this.getEvents()
        return res.data
      } catch (err) {
        this.error = err.message
        throw err
      }
    },
    async clearEvents() {
      try {
        const res = await axios.post('/api/v1/events/clear')
        this.events = []
        return res.data
      } catch (err) {
        this.error = err.message
        throw err
      }
    },
async uploadImage(file) {
       try {
         const base64 = await new Promise((resolve, reject) => {
           const reader = new FileReader()
           reader.onload = () => resolve(reader.result.split(',')[1])
           reader.onerror = reject
           reader.readAsDataURL(file)
         })
         const res = await axios.post('/api/v1/upload-image', {
           filename: file.name,
           data: base64
         })
         return res.data
       } catch (err) {
         this.error = err.message
         throw err
       }
     },
    async importDatabase(file) {
      try {
        const text = await file.text()
        await axios.post('/api/v1/database/import', text, {
          headers: { 'Content-Type': 'application/json' }
        })
        return { status: 'imported' }
      } catch (err) {
        this.error = err.message
        throw err
      }
    },
  async exportDatabase() {
      try {
        const res = await axios.get('/api/v1/database/export', {
          responseType: 'blob'
        })
        const url = URL.createObjectURL(res.data)
        const a = document.createElement('a')
        a.href = url
        const disposition = res.headers['content-disposition']
        if (disposition && disposition.includes('filename=')) {
          const filenameMatch = disposition.match(/filename="(.+?)"/)
          if (filenameMatch) {
            a.download = filenameMatch[1]
          } else {
            a.download = `tea-database-${new Date().toISOString().split('T')[0]}.json`
          }
        } else {
          a.download = `tea-database-${new Date().toISOString().split('T')[0]}.json`
        }
     a.click()
        URL.revokeObjectURL(url)
        return { status: 'exported' }
      } catch (err) {
        this.error = err.message
        throw err
      }
    },
 async deleteDatabase() {
       try {
         const res = await axios.delete('/api/v1/database')
         return res.data
       } catch (err) {
         this.error = err.message
         throw err
       }
     },
    async setupPassword(password) {
       try {
         const res = await axios.post('/api/v1/auth/setup-password', { password })
         return res.data
       } catch (err) {
         this.error = err.message
         throw err
       }
     }
   }
})
