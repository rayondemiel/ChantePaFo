<template>
  <dialog
    v-if="open"
    ref="dialogEl"
    class="modal-dialog"
    :class="{ 'modal-danger': variant === 'danger' }"
    @click="onBackdropClick"
    @close.prevent="cancel"
    @cancel.prevent="cancel"
  >
    <div class="modal-card">
      <h3 class="modal-title text-display">{{ title }}</h3>
      <p class="modal-message">{{ message }}</p>
      <div class="modal-actions">
        <button v-if="cancelText" class="btn btn-ghost" @click="cancel">
          {{ cancelText }}
        </button>
        <button class="btn btn-danger" @click="confirm">{{ confirmText }}</button>
      </div>
    </div>
  </dialog>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

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

const dialogEl = ref<HTMLDialogElement | null>(null)

// Promote the freshly-mounted dialog to a real modal: showModal() puts it
// in the top layer (above every stacking context), traps focus inside,
// handles the Escape key and paints the ::backdrop pseudo — all for free.
// Falls back to the plain `open` attribute in jsdom or older browsers so
// the component stays testable and degrades to a non-modal dialog.
onMounted(() => {
  const el = dialogEl.value
  if (!el) return
  try {
    el.showModal()
  } catch {
    el.setAttribute('open', '')
  }
})

function confirm() {
  emit('confirm')
}
function cancel() {
  emit('cancel')
}

// With showModal() the dim backdrop is the ::backdrop pseudo; any click on
// it lands on the <dialog> element itself, so target === dialogEl means
// "backdrop click" — click on the modal card has a different target.
function onBackdropClick(e: MouseEvent) {
  if (e.target === dialogEl.value) cancel()
}
</script>

<style scoped>
/* ===== Native <dialog> with showModal() =====
   The dialog lives in the top layer when showModal() runs; we reset the
   UA defaults and draw our own neon card inside. The ::backdrop pseudo
   handles the dim overlay — no extra DOM needed. */
.modal-dialog {
  padding: 0;
  border: none;
  background: transparent;
  color: inherit;
  max-width: min(420px, calc(100vw - 2 * var(--space-md)));
  max-height: calc(100vh - 2 * var(--space-md));
  overflow: visible;
  animation: dialog-pop 0.25s var(--ease-bounce);
}
.modal-dialog::backdrop {
  background: rgba(10, 10, 26, 0.72);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  animation: backdrop-fade 0.2s ease-out;
}

.modal-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-lg);
  box-shadow: 0 10px 50px rgba(var(--color-black-rgb), 0.5);
}
.modal-danger .modal-card {
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

@keyframes dialog-pop {
  from {
    opacity: 0;
    transform: scale(0.92) translateY(10px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}
@keyframes backdrop-fade {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

@media (prefers-reduced-motion: reduce) {
  .modal-dialog,
  .modal-dialog::backdrop {
    animation: none;
  }
}
</style>
