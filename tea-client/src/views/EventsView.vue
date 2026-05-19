<template>
  <div>
    <div class="card">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; flex-wrap: wrap; gap: 12px;">
        <h2>📋 Events Log</h2>
        <div style="display: flex; gap: 12px; align-items: center;">
          <label for="event-limit" style="font-size: 0.85rem; color: var(--text-secondary);">
            Show:
          </label>
          <select id="event-limit" v-model="eventLimit" @change="loadEvents" style="width: auto; min-width: 80px;">
            <option :value="10">10</option>
            <option :value="25">25</option>
            <option :value="50">50</option>
            <option :value="100">100</option>
            <option :value="500">All</option>
          </select>
          <button v-if="auth.isAdmin" class="btn btn-danger btn-sm" @click="confirmClearAll">Clear All</button>
        </div>
      </div>

      <div v-if="api.loading" class="empty-state">
        <div class="empty-state-icon">⏳</div>
        <p>Loading events...</p>
      </div>

      <div v-else-if="api.events.length === 0" class="empty-state">
        <div class="empty-state-icon">📭</div>
        <p>No events recorded yet</p>
      </div>

      <div v-else class="event-list">
        <div class="event-item" v-for="event in api.events" :key="event.id">
          <div class="event-info">
            <div class="event-type">{{ getEventLabel(event) }}</div>
            <div class="event-meta">
              {{ event.tea_type }} · {{ formatDate(event.created_at) }}
            </div>
          </div>
          <div class="event-actions" v-if="auth.isAdmin">
            <button class="btn btn-danger btn-sm" @click="confirmDelete(event)">Delete</button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="showDeleteModal" class="modal-overlay" @click.self="closeDeleteModal">
      <div class="modal">
        <h2>Delete Event</h2>
        <p>Are you sure you want to delete this event?</p>
        <div class="modal-actions">
          <button class="btn btn-secondary" @click="closeDeleteModal">Cancel</button>
          <button class="btn btn-danger" @click="deleteEvent">Delete</button>
        </div>
      </div>
    </div>

    <div v-if="showClearModal" class="modal-overlay" @click.self="closeClearModal">
      <div class="modal">
        <h2>Clear All Events</h2>
        <p>Are you sure you want to delete ALL events? This action cannot be undone.</p>
        <div class="modal-actions">
          <button class="btn btn-secondary" @click="closeClearModal">Cancel</button>
          <button class="btn btn-danger" @click="clearAllEvents">Clear All</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useApiStore } from '../stores/api'

const auth = useAuthStore()
const api = useApiStore()

const eventLimit = ref(50)
const showDeleteModal = ref(false)
const showClearModal = ref(false)
const deletingEvent = ref(null)

onMounted(async () => {
  await loadEvents()
})

async function loadEvents() {
  await api.getEvents(parseInt(eventLimit.value))
}

function getEventLabel(event) {
  const labels = {
    brewing_started: '🍵 Brewing Started',
    brewing_completed: '✅ Brewing Completed',
    brewing_cancelled: '❌ Brewing Cancelled',
    status_update: '📝 Status Updated',
    manual: '📋 Manual Event'
  }
  return labels[event.type] || event.type
}

function formatDate(ts) {
  if (!ts) return ''
  try {
    const d = new Date(ts)
    return d.toLocaleDateString() + ' ' + d.toLocaleTimeString()
  } catch {
    return ts
  }
}

function confirmDelete(event) {
  deletingEvent.value = event
  showDeleteModal.value = true
}

function closeDeleteModal() {
  showDeleteModal.value = false
  deletingEvent.value = null
}

async function deleteEvent() {
  try {
    await api.deleteEvent(deletingEvent.value.id)
    closeDeleteModal()
  } catch (err) {
    alert('Failed to delete event: ' + err.message)
  }
}

function confirmClearAll() {
  showClearModal.value = true
}

function closeClearModal() {
  showClearModal.value = false
}

async function clearAllEvents() {
  try {
    await api.clearEvents()
    closeClearModal()
  } catch (err) {
    alert('Failed to clear events: ' + err.message)
  }
}
</script>
