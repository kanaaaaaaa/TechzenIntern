<script setup>
import { onBeforeUnmount, onMounted, ref } from "vue"

const props = defineProps({
  points: {
    type: Number,
    required: true,
  },
  duration: {
    type: Number,
    default: 2000,
  },
})

const emit = defineEmits(["finished"])

const secondsLeft = ref(Math.ceil(props.duration / 1000))
let intervalId
let startedAt

function tick() {
  const remaining = Math.max(0, props.duration - (Date.now() - startedAt))
  secondsLeft.value = Math.ceil(remaining / 1000)
  if (remaining <= 0) {
    window.clearInterval(intervalId)
    emit("finished")
  }
}

onMounted(() => {
  startedAt = Date.now()
  intervalId = window.setInterval(tick, 100)
})

onBeforeUnmount(() => {
  if (intervalId) window.clearInterval(intervalId)
})
</script>

<template>
  <div class="points-reward-overlay" role="status" aria-live="polite">
    <div class="points-reward-top">Thank you!!!</div>
    <div class="points-reward-bottom">You earned {{ points }} {{ points === 1 ? "point" : "points" }}</div>
    <div class="points-reward-countdown">Returning in {{ secondsLeft }} {{ secondsLeft === 1 ? "second" : "seconds" }}</div>
  </div>
</template>

<style scoped>
.points-reward-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  flex-direction: column;
  justify-content: center;
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
  margin-top: 16px;
}

.points-reward-countdown {
  width: 100%;
  text-align: center;
  font-size: clamp(14px, 2.5vw, 18px);
  font-weight: 500;
  color: var(--ink-muted, #6b7a72);
  margin-top: 12px;
}
</style>
