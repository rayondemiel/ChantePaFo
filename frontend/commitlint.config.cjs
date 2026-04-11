// commitlint.config.js
module.exports = {
  extends: ['@commitlint/config-conventional'],
  rules: {
    'type-enum': [2, 'always', [
      'feat',     // Nouvelle feature → minor bump
      'fix',      // Bug fix → patch bump
      'docs',     // Documentation only
      'style',    // Formatting, no code change
      'refactor', // Refactoring, no feature/fix
      'test',     // Adding/updating tests
      'chore',    // Build, CI, tooling
      'perf',     // Performance improvement
    ]],
    'subject-max-length': [2, 'always', 100],
    'body-max-line-length': [2, 'always', 200],
    'footer-max-line-length': [2, 'always', 200],
  },
};
