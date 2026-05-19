<template>
  <div>
    <div class="card">
      <h2>🗄️ Database Management</h2>
      <p style="color: var(--text-secondary); margin-bottom: 20px;">
        Export, import, or delete the entire tea production database
      </p>

      <div style="display: flex; gap: 12px; flex-wrap: wrap;">
        <button class="btn btn-primary" @click="handleExport">
          📤 Export Database
        </button>
        <button class="btn btn-secondary" @click="$refs.importInput.click()">
          📥 Import Database
        </button>
        <button class="btn btn-danger" @click="confirmDeleteDb">
          🗑️ Delete All Data
        </button>
      </div>

      <input
        ref="importInput"
        type="file"
        accept=".json"
        style="display: none"
        @change="handleImport"
      />
    </div>

    <div class="card">
      <h3>Database Info</h3>
      <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 16px;">
        <div>
          <div style="color: var(--text-secondary); font-size: 0.85rem;">Tea Types</div>
          <div style="font-size: 1.5rem; font-weight: 700;">{{ api.teaTypes.length }}</div>
        </div>
        <div>
          <div style="color: var(--text-secondary); font-size: 0.85rem;">Events</div>
          <div style="font-size: 1.5rem; font-weight: 700;">{{ api.events.length }}</div>
        </div>
        <div>
          <div style="color: var(--text-secondary); font-size: 0.85rem;">Current Status</div>
          <div style="font-size: 1.5rem; font-weight: 700;">
            {{ api.status?.status || 'unknown' }}
          </div>
        </div>
      </div>
    </div>

    <div v-if="showMessage" class="alert" :class="messageType">
      {{ message }}
    </div>

    <div v-if="showDeleteModal" class="modal-overlay" @click.self="closeDeleteModal">
      <div class="modal">
        <h2>Delete All Database Data</h2>
        <p style="color: var(--danger); font-weight: 600;">
          WARNING: This will permanently delete all tea types, events, and sessions.
        </p>
        <p>Are you absolutely sure you want to proceed?</p>
        <div class="modal-actions">
          <button class="btn btn-secondary" @click="closeDeleteModal">Cancel</button>
          <button class="btn btn-danger" @click="deleteDatabase">Yes, Delete Everything</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useApiStore } from '../stores/api'

const api = useApiStore()
const showMessage = ref(false)
const message = ref('')
const messageType = ref('alert-success')
const showDeleteModal = ref(false)

function showNotification(msg, type = 'alert-success') {
  message.value = msg
  messageType.value = type
  showMessage.value = true
  setTimeout(() => { showMessage.value = false }, 4000)
}

async function handleExport() {
  try {
    await api.exportDatabase()
    showNotification('Database exported successfully!')
  } catch (err) {
    showNotification('Export failed: ' + err.message, 'alert-error')
  }
}

async function handleImport(event) {
  const file = event.target.files[0]
  if (!file) return
  try {
    await api.importDatabase(file)
    showNotification('Database imported successfully!')
    await Promise.all([
      api.getStatus(),
      api.getTeaTypes(),
      api.getEvents(),
      api.getStatistics()
    ])
  } catch (err) {
    showNotification('Import failed: ' + err.message, 'alert-error')
  }
  event.target.value = ''
}

function confirmDeleteDb() {
  showDeleteModal.value = true
}

function closeDeleteModal() {
  showDeleteModal.value = false
}

async function deleteDatabase() {
  try {
    await api.deleteDatabase()
    showNotification('Database cleared successfully!')
    await Promise.all([
      api.getStatus(),
      api.getTeaTypes(),
      api.getEvents(),
      api.getStatistics()
    ])
    closeDeleteModal()
  } catch (err) {
    showNotification('Failed to clear database: ' + err.message, 'alert-error')
  }
}
</script>
