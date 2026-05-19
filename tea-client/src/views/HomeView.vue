<template>
  <div class="empty-state">
    <div class="empty-state-icon">🍵</div>
    <h2>Welcome to Tea Production Manager</h2>
    <p style="color: var(--text-secondary); margin-top: 12px;">
      {{ auth.isAdmin ? 'You are logged in as Admin' : 'You are viewing as Guest' }}
    </p>
    <router-link to="/status" class="btn btn-primary" style="margin-top: 20px; display: inline-block; text-decoration: none;">
      View Status
    </router-link>
  </div>
</template>

<script setup>
import { useAuthStore } from '../stores/auth'
const auth = useAuthStore()
</script>
