<template>
  <div class="coffee-view">
    <div class="error-card">
      <div class="teapot-grid">
        <span class="teapot">🫖</span>
        <span class="teapot">🫖</span>
        <span class="teapot">🫖</span>
        <span class="teapot">🫖</span>
        <span class="teapot">🫖</span>
        <span class="teapot">🫖</span>
        <span class="teapot">🫖</span>
        <span class="teapot">🫖</span>
        <span class="teapot">🫖</span>
      </div>
      <h1>418</h1>
      <h2>I'm a teapot</h2>
      <p>This server is a teapot, not a coffee machine.</p>
      <p>Try brewing some tea instead:</p>
      <router-link to="/status" class="btn btn-primary">Back to Tea</router-link>
    </div>
  </div>
</template>

<script setup>
</script>

<style scoped>
.coffee-view {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 60vh;
}

.error-card {
  text-align: center;
  padding: 40px;
}

.teapot-grid {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px;
  margin-bottom: 24px;
}

.teapot {
  font-size: 2rem;
  animation: wobble 1s ease-in-out infinite alternate;
}

.teapot:nth-child(odd) {
  animation-delay: 0.2s;
}

.teapot:nth-child(3n) {
  animation-delay: 0.4s;
}

@keyframes wobble {
  from { transform: rotate(-8deg); }
  to { transform: rotate(8deg); }
}

.error-card h1 {
  font-size: 5rem;
  margin: 0;
  color: var(--accent);
}

.error-card h2 {
  font-size: 1.5rem;
  margin: 8px 0;
  color: var(--text);
}

.error-card p {
  color: var(--text-secondary);
  margin: 4px 0;
}
</style>
