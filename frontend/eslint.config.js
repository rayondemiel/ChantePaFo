import js from '@eslint/js'
import tseslint from 'typescript-eslint'
import pluginVue from 'eslint-plugin-vue'
import prettier from 'eslint-config-prettier'
import pluginSecurity from 'eslint-plugin-security'
export default [
  { ignores: ['dist/**', 'node_modules/**', '.husky/**', '**/*.cjs', 'coverage/**'] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  ...pluginVue.configs['flat/recommended'],
  {
    languageOptions: {
      globals: {
        window: 'readonly',
        document: 'readonly',
        localStorage: 'readonly',
        fetch: 'readonly',
        crypto: 'readonly',
        Headers: 'readonly',
        RequestInit: 'readonly',
        Response: 'readonly',
        HTMLSelectElement: 'readonly',
        HTMLInputElement: 'readonly',
        navigator: 'readonly',
        setTimeout: 'readonly',
        clearTimeout: 'readonly',
        MediaQueryList: 'readonly',
        MediaQueryListEvent: 'readonly',
        HTMLDialogElement: 'readonly',
        MouseEvent: 'readonly',
      },
    },
  },
  {
    files: ['**/*.vue'],
    languageOptions: {
      parserOptions: {
        parser: tseslint.parser,
      },
    },
  },
  {
    rules: {
      'vue/multi-word-component-names': 'off',
    },
  },
  pluginSecurity.configs.recommended,
  prettier,
]
