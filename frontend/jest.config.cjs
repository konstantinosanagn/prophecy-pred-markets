/** @type {import("jest").Config} */
module.exports = {
  testEnvironment: "jsdom",
  roots: ["<rootDir>/tests"],
  moduleFileExtensions: ["ts", "tsx", "js", "jsx"],
  transform: {
    "^.+\\.(ts|tsx)$": "ts-jest",
  },
  setupFilesAfterEnv: ["<rootDir>/tests/setupTests.ts"],
  moduleNameMapper: {
    "\\.(jpg|jpeg|png|gif|svg|webp)$": "<rootDir>/tests/__mocks__/fileMock.js",
    "^next/image$": "<rootDir>/tests/__mocks__/nextImage.js",
    "^next/font/google$": "<rootDir>/tests/__mocks__/nextFont.js",
  },
};


