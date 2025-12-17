module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  roots: ['<rootDir>/test'],
  testMatch: ['**/*.spec.ts', '**/*.test.ts'],
  moduleNameMapper: {
    '^@common/(.*)$': '<rootDir>/common/$1',
    '^@api/(.*)$': '<rootDir>/api/$1',
    '^@modules/(.*)$': '<rootDir>/modules/$1'
  },
  collectCoverageFrom: [
    'api/**/*.ts',
    'common/**/*.ts',
    'modules/**/*.ts',
    '!**/*.d.ts',
    '!**/*.spec.ts',
    '!**/*.test.ts'
  ],
  coverageDirectory: 'coverage',
  verbose: true
};
