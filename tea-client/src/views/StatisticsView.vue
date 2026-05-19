<template>
  <div>
    <div class="card">
      <h2>📊 Tea Production Statistics</h2>
      <p style="color: var(--text-secondary); margin-bottom: 20px;">
        Overview of tea production by type and month
      </p>

      <div v-if="api.loading" class="empty-state">
        <div class="empty-state-icon">⏳</div>
        <p>Loading statistics...</p>
      </div>

      <div v-else-if="api.statistics.length === 0" class="empty-state">
        <div class="empty-state-icon">📭</div>
        <p>No statistics available yet</p>
      </div>

      <div v-else class="stats-grid">
        <div class="stat-card" v-for="stat in sortedStatistics" :key="`${stat.tea_type}-${stat.month}`">
          <div class="stat-tea">{{ stat.tea_type }}</div>
          <div class="stat-month">{{ formatMonth(stat.month) }}</div>
          <div class="stat-count">{{ stat.count }}</div>
          <div style="margin-top: 12px; font-size: 0.8rem; color: var(--text-secondary);">
            <div>Started: {{ stat.started || 0 }}</div>
            <div>Completed: {{ stat.completed || 0 }}</div>
            <div v-if="stat.cancelled > 0">Cancelled: {{ stat.cancelled }}</div>
          </div>
        </div>
      </div>
    </div>

    <div class="card" v-if="api.statistics.length > 0">
      <h3>Summary by Tea Type</h3>
      <div class="table-container">
        <table>
          <thead>
            <tr>
              <th>Tea Type</th>
              <th>Total Events</th>
              <th>Started</th>
              <th>Completed</th>
              <th>Cancelled</th>
              <th>Completion Rate</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="summary in teaTypeSummary" :key="summary.name">
              <td><strong>{{ summary.name }}</strong></td>
              <td>{{ summary.total }}</td>
              <td>{{ summary.started }}</td>
              <td>{{ summary.completed }}</td>
              <td>{{ summary.cancelled }}</td>
              <td>{{ summary.completionRate }}%</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useApiStore } from '../stores/api'

const api = useApiStore()

const sortedStatistics = computed(() => {
  return [...api.statistics].sort((a, b) => {
    if (b.month !== a.month) return b.month.localeCompare(a.month)
    return a.tea_type.localeCompare(b.tea_type)
  })
})

const teaTypeSummary = computed(() => {
  const map = {}
  for (const stat of api.statistics) {
    if (!map[stat.tea_type]) {
      map[stat.tea_type] = {
        name: stat.tea_type,
        total: 0,
        started: 0,
        completed: 0,
        cancelled: 0
      }
    }
    map[stat.tea_type].total += stat.count
    map[stat.tea_type].started += stat.started || 0
    map[stat.tea_type].completed += stat.completed || 0
    map[stat.tea_type].cancelled += stat.cancelled || 0
  }
  return Object.values(map).map(s => ({
    ...s,
    completionRate: s.started > 0 ? Math.round((s.completed / s.started) * 100) : 0
  })).sort((a, b) => b.total - a.total)
})

function formatMonth(month) {
  if (!month || month === 'unknown') return 'Unknown'
  const [year, mon] = month.split('-')
  const date = new Date(parseInt(year), parseInt(mon) - 1)
  return date.toLocaleDateString('en-US', { year: 'numeric', month: 'long' })
}

onMounted(async () => {
  await api.getStatistics()
})
</script>
