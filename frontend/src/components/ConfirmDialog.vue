<template>
  <Transition name="modal">
    <div v-if="open" class="modal-backdrop" @click.self="cancel" @keydown.esc="cancel">
      <div class="modal-card" :class="{ 'modal-danger': variant === 'danger' }">
        <h3 class="modal-title text-display">{{ title }}</h3>
        <p class="modal-message">{{ message }}</p>
        <div class="modal-actions">
          <button v-if="cancelText" class="btn btn-ghost" @click="cancel">
            {{ cancelText }}
          </button>
          <button class="btn btn-danger" @click="confirm">{{ confirmText }}</button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    open: boolean
    title: string
    message: string
    confirmText?: string
    cancelText?: string
    variant?: 'default' | 'danger'
  }>(),
  {
    confirmText: 'Confirmer',
    cancelText: 'Annuler',
    variant: 'default',
  },
)

const emit = defineEmits<{
  confirm: []
  cancel: []
}>()

function confirm() {
  emit('confirm')
}
function cancel() {
  emit('cancel')
}
</script>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(var(--color-bg-rgb), 0.72);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: var(--space-md);
}
.modal-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-lg);
  max-width: 420px;
  width: 100%;
  box-shadow: 0 10px 50px rgba(var(--color-black-rgb), 0.5);
  animation: pop-in 0.25s var(--ease-bounce);
}
.modal-danger {
  border-color: rgba(var(--color-error-rgb), 0.4);
  box-shadow:
    0 10px 50px rgba(var(--color-black-rgb), 0.5),
    0 0 30px rgba(var(--color-error-rgb), 0.15);
}
.modal-title {
  font-size: var(--text-xl);
  margin-bottom: var(--space-sm);
  background: linear-gradient(135deg, var(--color-primary), var(--color-accent));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.modal-danger .modal-title {
  background: linear-gradient(135deg, var(--color-error), var(--color-warning));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.modal-message {
  color: var(--color-text-muted);
  font-size: var(--text-base);
  margin-bottom: var(--space-lg);
  line-height: 1.4;
}
.modal-actions {
  display: flex;
  gap: var(--space-sm);
  justify-content: flex-end;
}

@keyframes pop-in {
  from {
    opacity: 0;
    transform: scale(0.92) translateY(10px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s ease;
}
.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

@media (prefers-reduced-motion: reduce) {
  .modal-card {
    animation: none;
  }
}
</style>
