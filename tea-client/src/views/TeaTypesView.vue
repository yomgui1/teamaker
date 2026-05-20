<template>
  <div>
    <div class="card">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
        <h2>🍃 Tea Types Management</h2>
        <button class="btn btn-primary" @click="openAddModal">+ Add Tea Type</button>
      </div>

      <div v-if="api.loading" class="empty-state">
        <div class="empty-state-icon">⏳</div>
        <p>Loading tea types...</p>
      </div>

      <div v-else-if="api.teaTypes.length === 0" class="empty-state">
        <div class="empty-state-icon">🍃</div>
        <p>No tea types defined yet</p>
      </div>

      <div v-else class="tea-type-grid">
        <div class="tea-type-card" v-for="tt in api.teaTypes" :key="tt.id">
          <img :src="tt.image ? imageUrl(tt.image) : DEFAULT_TEA_IMAGE" :alt="tt.name" />
          <div class="tea-type-name">{{ tt.name }}</div>
          <div class="tea-type-actions">
            <button class="btn btn-secondary btn-sm" @click="openEditModal(tt)">Edit</button>
            <button class="btn btn-danger btn-sm" @click="confirmDelete(tt)">Delete</button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal">
        <h2>{{ editingTea ? 'Edit Tea Type' : 'Add Tea Type' }}</h2>

        <div class="form-group">
          <label for="tea-name">Tea Name</label>
          <input
            id="tea-name"
            type="text"
            v-model="form.name"
            placeholder="e.g., Green Tea, Black Tea"
          />
        </div>

        <div class="form-group">
          <label>Tea Image</label>
          <div v-if="form.imagePreview" style="text-align: center; margin-bottom: 12px;">
            <img :src="form.imagePreview" class="image-preview" alt="Preview" />
          </div>
          <div class="image-upload-area" @click="$refs.fileInput.click()">
            <div v-if="!form.imagePreview">
              <div style="font-size: 2rem; margin-bottom: 8px;">📁</div>
              <p>Click to upload image</p>
              <p style="font-size: 0.8rem; color: var(--text-secondary);">PNG, JPG, WEBP supported</p>
            </div>
            <div v-else>
              <p>Click to change image</p>
            </div>
          </div>
          <input
            ref="fileInput"
            type="file"
            accept="image/png,image/jpeg,image/webp,image/gif"
            style="display: none"
            @change="handleFileSelect"
          />
        </div>

        <div class="modal-actions">
          <button class="btn btn-secondary" @click="closeModal">Cancel</button>
          <button class="btn btn-primary" @click="saveTeaType" :disabled="!form.name">
            {{ editingTea ? 'Update' : 'Add' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="showDeleteModal" class="modal-overlay" @click.self="closeDeleteModal">
      <div class="modal">
        <h2>Delete Tea Type</h2>
        <p>Are you sure you want to delete <strong>{{ deletingTea?.name }}</strong>? This action cannot be undone.</p>
        <div class="modal-actions">
          <button class="btn btn-secondary" @click="closeDeleteModal">Cancel</button>
          <button class="btn btn-danger" @click="deleteTeaType">Delete</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useApiStore } from '../stores/api'
import { imageUrl } from '../utils/url'

const api = useApiStore()

const DEFAULT_TEA_IMAGE = 'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjOGM3MDU1IiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCI+PHBhdGggZD0iTTYgMTh2LjVhNCA0IDAgMCAwIDggMHYtLjUiLz48cGF0aCBkPSJNNSA4aDE0Ii8+PHBhdGggZD0iTTE5IDhoLTE0YTQgNCAwIDAgMCAwIDhoMTR6Ii8+PC9zdmc+'

const showModal = ref(false)
const showDeleteModal = ref(false)
const editingTea = ref(null)
const deletingTea = ref(null)

const form = reactive({
  name: '',
  image: '',
  imageFile: null,
  imagePreview: ''
})

onMounted(async () => {
  await api.getTeaTypes()
})

function openAddModal() {
  editingTea.value = null
  form.name = ''
  form.image = ''
  form.imageFile = null
  form.imagePreview = ''
  showModal.value = true
}

function openEditModal(tea) {
  editingTea.value = tea
  form.name = tea.name
  form.image = tea.image || ''
  form.imageFile = null
  form.imagePreview = tea.image ? imageUrl(tea.image) : ''
  showModal.value = true
}

function closeModal() {
  showModal.value = false
  editingTea.value = null
}

function confirmDelete(tea) {
  deletingTea.value = tea
  showDeleteModal.value = true
}

function closeDeleteModal() {
  showDeleteModal.value = false
  deletingTea.value = null
}

function handleFileSelect(event) {
  const file = event.target.files[0]
  if (!file) return
  form.imageFile = file
  form.imagePreview = URL.createObjectURL(file)
}

async function saveTeaType() {
  try {
    let imageUrl = form.image

    if (form.imageFile) {
      const uploadRes = await api.uploadImage(form.imageFile)
      imageUrl = uploadRes.filename
    }

    if (editingTea.value) {
      await api.updateTeaType(editingTea.value.id, {
        name: form.name,
        image: imageUrl
      })
    } else {
      await api.createTeaType(form.name, imageUrl)
    }

    closeModal()
  } catch (err) {
    console.error('Save tea type error:', err)
    console.error('Response:', err.response?.data)
    alert('Failed to save tea type: ' + (err.response?.data?.error || err.message))
  }
}

async function deleteTeaType() {
  try {
    await api.deleteTeaType(deletingTea.value.id)
    closeDeleteModal()
  } catch (err) {
    alert('Failed to delete tea type: ' + err.message)
  }
}
</script>
