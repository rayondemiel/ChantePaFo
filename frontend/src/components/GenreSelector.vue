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
import { reactive } from 'vue'
import { GENRES, DIFFICULTY_LABELS } from '../lib/genres'

const emit = defineEmits<{ update: [genres: Record<string, number>] }>()

const selected = reactive<Record<string, number>>({ all: 2 })

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
  --tone: #ff69b4;
}
.tone-rock {
  --tone: #dc143c;
}
.tone-rap {
  --tone: #b44dff;
}
.tone-electro {
  --tone: #00f0ff;
}
.tone-disco {
  --tone: #ffd700;
}
.tone-jazz {
  --tone: #daa520;
}

/* Difficulty dots — 4 clickable levels.
   Replaces the native <select> to preserve the retro identity. */
.difficulty-dots {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 0.15rem 0.4rem;
  background: rgba(10, 10, 26, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.08);
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
</style>
