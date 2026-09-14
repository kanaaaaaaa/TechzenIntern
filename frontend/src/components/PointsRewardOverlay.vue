<script setup>
defineProps({
  points: {
    type: Number,
    required: true,
  },
})
</script>

<template>
  <div class="points-reward-overlay" role="status" aria-live="polite">
    <div class="points-reward-top">thank you</div>
    <div class="points-reward-bottom">You earned {{ points }} {{ points === 1 ? "point" : "points" }}</div>
  </div>
</template>

<style scoped>
.points-reward-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  align-items: center;
  padding: max(40px, env(safe-area-inset-top)) max(24px, env(safe-area-inset-right)) max(48px, env(safe-area-inset-bottom)) max(24px, env(safe-area-inset-left));
  background: #ffffff;
  color: var(--ink, #17221d);
}

.points-reward-top {
  width: 100%;
  text-align: center;
  font-size: clamp(36px, 7vw, 72px);
  font-weight: 800;
  letter-spacing: -.04em;
  line-height: 1;
}

.points-reward-bottom {
  width: 100%;
  text-align: center;
  font-size: clamp(18px, 4vw, 28px);
  font-weight: 700;
  line-height: 1.6;
}
</style>
