<template>
  <div class="genre-selector">
    <div v-for="genre in GENRES" :key="genre.key" class="genre-item" :class="`tone-${genre.color}`">
      <button
        class="chip"
        :class="[`chip-${genre.color}`, { active: isSelected(genre.key) }]"
        @click="toggleGenre(genre.key)"
      >
        {{ genre.label }}
      </button>
      <div
        v-if="isSelected(genre.key)"
        class="difficulty-dots"
        role="radiogroup"
        :aria-label="`Difficulté ${genre.label}`"
      >
        <button
          v-for="level in 4"
          :key="level"
          type="button"
          class="diff-dot"
          :class="{ 'diff-dot-filled': (selected[genre.key] ?? 0) >= level }"
          :aria-label="`Niveau ${level} : ${DIFFICULTY_LABELS[level - 1]}`"
          :aria-pressed="selected[genre.key] === level"
          :title="DIFFICULTY_LABELS[level - 1]"
          @click.stop="setDifficulty(genre.key, level)"
        ></button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, watch } from 'vue'
import { GENRES, DIFFICULTY_LABELS } from '../lib/genres'

const props = defineProps<{
  /** Server-synced selection. Re-syncs the local state on every change
   *  (host reload, return from a game) without emitting an update. */
  modelValue?: Record<string, number>
}>()

const emit = defineEmits<{ update: [genres: Record<string, number>] }>()

const selected = reactive<Record<string, number>>({ all: 2 })

function syncFrom(value: Record<string, number> | undefined) {
  if (!value || Object.keys(value).length === 0) return
  Object.keys(selected).forEach((k) => {
    // eslint-disable-next-line security/detect-object-injection
    delete selected[k]
  })
  for (const [key, level] of Object.entries(value)) {
    // eslint-disable-next-line security/detect-object-injection
    selected[key] = Number(level) || 2
  }
}

watch(() => props.modelValue, syncFrom, { immediate: true, deep: true })

function isSelected(key: string): boolean {
  return key in selected
}

function toggleGenre(key: string) {
  if (key in selected) {
    // eslint-disable-next-line security/detect-object-injection
    delete selected[key]
  } else {
    // eslint-disable-next-line security/detect-object-injection
    selected[key] = 2 // default Normal
  }
  // If "all" is selected alongside others, keep only "all"
  if (key === 'all' && 'all' in selected) {
    Object.keys(selected).forEach((k) => {
      // eslint-disable-next-line security/detect-object-injection
      if (k !== 'all') delete selected[k]
    })
  } else if (key !== 'all' && 'all' in selected) {
    delete selected['all']
  }
  // If nothing selected, default to all
  if (Object.keys(selected).length === 0) {
    selected['all'] = 2
  }
  emit('update', { ...selected })
}

function setDifficulty(key: string, level: number) {
  // eslint-disable-next-line security/detect-object-injection
  selected[key] = level
  emit('update', { ...selected })
}
</script>

<style scoped>
.genre-selector {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-sm);
}
.genre-item {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  /* Default tone fallback — each .tone-* class overrides this */
  --tone: var(--color-accent);
}
/* Map each chip-color to a --tone CSS variable so the dots match
   the genre's hue automatically. These mirror the colors in global.css. */
.tone-pop {
  --tone: var(--tone-pop);
}
.tone-rock {
  --tone: var(--tone-rock);
}
.tone-rap {
  --tone: var(--tone-rap);
}
.tone-electro {
  --tone: var(--tone-electro);
}
.tone-disco {
  --tone: var(--tone-disco);
}
.tone-jazz {
  --tone: var(--tone-jazz);
}

/* Difficulty dots — 4 clickable levels.
   Replaces the native <select> to preserve the retro identity. */
.difficulty-dots {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 0.15rem 0.4rem;
  background: rgba(var(--color-bg-rgb), 0.4);
  border: 1px solid rgba(var(--color-white-rgb), 0.08);
  border-radius: var(--radius-full);
}
.diff-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  border: 1.5px solid var(--tone);
  background: transparent;
  padding: 0;
  cursor: pointer;
  transition:
    background 0.15s,
    transform 0.12s,
    box-shadow 0.2s;
}
.diff-dot:hover {
  transform: scale(1.25);
}
.diff-dot-filled {
  background: var(--tone);
  box-shadow: 0 0 8px var(--tone);
}

/* Phones: chips and difficulty dots must be tappable with a thumb. The dot
   stays a 10px glyph (drawn by ::before) inside a 26×44px hit area. */
@media (max-width: 899px) {
  .genre-selector .chip {
    min-height: 44px;
    padding: 0.5rem 0.95rem;
    font-size: var(--text-sm);
  }
  .difficulty-dots {
    gap: 0;
    padding: 0 0.2rem;
  }
  .diff-dot {
    position: relative;
    width: 26px;
    height: 44px;
    border: none;
    background: transparent;
    box-shadow: none;
  }
  .diff-dot::before {
    content: '';
    position: absolute;
    top: 50%;
    left: 50%;
    width: 10px;
    height: 10px;
    margin: -5px 0 0 -5px;
    border-radius: 50%;
    border: 1.5px solid var(--tone);
  }
  .diff-dot-filled::before {
    background: var(--tone);
    box-shadow: 0 0 8px var(--tone);
  }
}
</style>
