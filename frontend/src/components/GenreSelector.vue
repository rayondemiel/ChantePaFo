<template>
  <div class="genre-selector">
    <div v-for="genre in availableGenres" :key="genre.key" class="genre-item">
      <button
        class="chip"
        :class="[`chip-${genre.color}`, { active: isSelected(genre.key) }]"
        @click="toggleGenre(genre.key)"
      >
        {{ genre.label }}
      </button>
      <select
        v-if="isSelected(genre.key)"
        :value="selected[genre.key]"
        class="difficulty-select"
        @change="setDifficulty(genre.key, Number(($event.target as HTMLSelectElement).value))"
      >
        <option :value="1">Facile</option>
        <option :value="2">Normal</option>
        <option :value="3">Difficile</option>
        <option :value="4">Expert</option>
      </select>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive } from 'vue'

const emit = defineEmits<{ update: [genres: Record<string, number>] }>()

const availableGenres = [
  { key: 'all', label: 'Tout', color: 'pop' },
  { key: 'pop', label: 'Pop', color: 'pop' },
  { key: 'rock', label: 'Rock', color: 'rock' },
  { key: 'rap', label: 'Rap FR', color: 'rap' },
  { key: 'electro', label: 'Electro', color: 'electro' },
  { key: 'disco', label: 'Disco', color: 'disco' },
  { key: 'jazz', label: 'Jazz', color: 'jazz' },
  { key: 'soul', label: 'Soul/Funk', color: 'disco' },
  { key: 'metal', label: 'Metal', color: 'rock' },
  { key: 'kpop', label: 'K-pop', color: 'pop' },
  { key: 'annees80', label: '80s', color: 'electro' },
  { key: 'annees90', label: '90s', color: 'electro' },
  { key: 'classique', label: 'Classique', color: 'jazz' },
  { key: 'rnb', label: 'R&B', color: 'rap' },
  { key: 'reggae', label: 'Reggae', color: 'disco' },
  { key: 'latino', label: 'Latino', color: 'disco' },
  { key: 'bo_films', label: 'BO Films', color: 'jazz' },
]

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
  display: flex;
  align-items: center;
  gap: var(--space-xs);
}
.difficulty-select {
  padding: 0.15rem 0.3rem;
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  color: var(--color-text);
  border: 1px solid var(--color-border);
  font-family: var(--font-body);
  font-size: var(--text-xs);
}
</style>
