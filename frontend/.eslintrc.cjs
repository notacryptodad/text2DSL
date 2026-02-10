module.exports = {
  root: true,
  env: { browser: true, es2020: true },
  extends: [
    'eslint:recommended',
    'plugin:react/recommended',
    'plugin:react/jsx-runtime',
    'plugin:react-hooks/recommended',
  ],
  ignorePatterns: ['dist', '.eslintrc.cjs'],
  parserOptions: { ecmaVersion: 'latest', sourceType: 'module' },
  settings: { react: { version: '18.2' } },
  plugins: ['react-refresh'],
  rules: {
    'react-refresh/only-export-components': [
      'warn',
      { allowConstantExport: true },
    ],
    'react/prop-types': 'off',
    'no-restricted-syntax': [
      'warn',  // start with warn, not error
      {
        selector: 'Literal[value=/^(p|m|gap)-(1|2|3|5|6|7|9|10|11)/]',
        message: 'Use semantic spacing: p-sm, p-base, p-lg, p-xl',
      },
    ],
  },
}
