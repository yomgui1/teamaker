<template>
  <div>
    <div v-if="api.loading" class="empty-state">
      <div class="empty-state-icon">⏳</div>
      <p>Loading status...</p>
    </div>

    <div v-else class="tea-brewing-section">
      <div class="card">
        <h2>Tea Production Status</h2>

        <div v-if="!auth.isAdmin" class="status-display">
          <div class="status-icon">{{ statusIcon }}</div>
          <div class="status-text">{{ statusText }}</div>
          <div class="status-detail" v-if="api.status?.type && api.status.type !== 'unknown'">
            Tea: {{ api.status.type }}
          </div>
          <div class="status-detail" v-if="api.status?.timestamp">
            Last update: {{ formatDate(api.status.timestamp) }}
          </div>
        </div>

       <div v-else>
          <div class="tea-image-default" @click="handleTeaClick" v-if="!selectedTeaImage && !isBrewing">
            🍵
          </div>

          <img
            v-else-if="selectedTeaImage"
            :src="selectedTeaImage"
            alt="Tea"
            class="tea-image"
            @click="handleTeaClick"
          />

          <h3 v-if="selectedTeaType">
            {{ selectedTeaType }}
          </h3>

          <div class="status-text" :style="{ color: isBrewing ? 'var(--warning)' : 'var(--accent)' }">
            {{ isBrewing ? 'Brewing in progress...' : 'No active brewing' }}
          </div>

          <div class="form-group" style="max-width: 300px; margin: 20px auto;">
            <label for="tea-select">Select Tea Type</label>
            <select id="tea-select" v-model="selectedTeaType" :disabled="isBrewing">
              <option value="" disabled>Choose a tea type</option>
              <option v-for="tt in api.teaTypes" :key="tt.id" :value="tt.name">
                {{ tt.name }}
              </option>
            </select>
          </div>

          <div class="brewing-actions">
            <button
              v-if="!isBrewing"
              class="btn btn-primary"
              :disabled="!selectedTeaType"
              @click="handleStartBrewing"
            >
              🍵 Tea Brewing
            </button>
            <button
              v-else
              class="btn btn-primary"
              @click="handleCompleteBrewing"
            >
              ✅ Complete Brewing
            </button>
            <button
              v-if="isBrewing"
              class="btn btn-warning"
              @click="handleCancelBrewing"
            >
              ❌ Cancel Brewing
            </button>
          </div>

          <div v-if="message" class="alert" :class="messageType" style="max-width: 400px; margin: 16px auto;">
            {{ message }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useApiStore } from '../stores/api'
import { imageUrl } from '../utils/url'

const auth = useAuthStore()
const api = useApiStore()

const selectedTeaType = ref('')
const selectedTeaImage = ref('')
const message = ref('')
const messageType = ref('alert-success')

const isBrewing = computed(() => {
  if (!api.status) return false
  return api.status.status === 'on-going'
})

const statusIcon = computed(() => {
  if (!api.status) return '❓'
  switch (api.status.status) {
    case 'done': return '✅'
    case 'on-going': return '🍵'
    default: return '❓'
  }
})

const statusText = computed(() => {
  if (!api.status) return 'Unknown'
  switch (api.status.status) {
    case 'done': return 'Brewing Complete'
    case 'on-going': return 'Brewing in Progress'
    default: return 'No Data Available'
  }
})

onMounted(async () => {
  if (auth.isAdmin) {
    await api.getTeaTypes()
  }
})

function formatDate(ts) {
  if (!ts) return ''
  try {
    return new Date(ts).toLocaleString()
  } catch {
    return ts
  }
}

async function handleTeaClick() {
  if (!auth.isAdmin) return
  if (api.teaTypes.length > 0 && !selectedTeaType.value) {
    selectedTeaType.value = api.teaTypes[0].name
  }
  if (selectedTeaType.value) {
    const tea = api.teaTypes.find(t => t.name === selectedTeaType.value)
    selectedTeaImage.value = tea?.image ? imageUrl(tea.image) : ''
  }
}

async function handleStartBrewing() {
  if (!selectedTeaType.value) return
  try {
    await api.startBrewing(selectedTeaType.value)
    message.value = 'Brewing started!'
    messageType.value = 'alert-success'
    setTimeout(() => message.value = '', 3000)
  } catch (err) {
    message.value = 'Failed to start brewing'
    messageType.value = 'alert-error'
  }
}

async function handleCompleteBrewing() {
  try {
    await api.completeBrewing(selectedTeaType.value)
    message.value = 'Brewing completed!'
    messageType.value = 'alert-success'
    setTimeout(() => message.value = '', 3000)
  } catch (err) {
    message.value = 'Failed to complete brewing'
    messageType.value = 'alert-error'
  }
}

async function handleCancelBrewing() {
  try {
    await api.cancelBrewing(selectedTeaType.value)
    message.value = 'Brewing cancelled!'
    messageType.value = 'alert-success'
    setTimeout(() => message.value = '', 3000)
  } catch (err) {
    message.value = 'Failed to cancel brewing'
    messageType.value = 'alert-error'
  }
}
</script>
