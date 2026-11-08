module.exports = {
  preset: 'jest-expo',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  // Testes ficam FORA de src/app (lá só podem existir rotas e layouts).
  testMatch: ['<rootDir>/__tests__/**/*.test.{ts,tsx}'],
};
