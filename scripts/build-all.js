#!/usr/bin/env node

/**
 * Meta build script that runs all build tasks in sequence:
 * 1. Generates categories.md from categories.json
 * 2. Builds README.md (which loads .env for GitHub PAT)
 */

require('dotenv').config();

const { execSync } = require('child_process');
const path = require('path');

console.log('🚀 Starting full build process...\n');

// Step 1: Generate categories.md
console.log('📋 Step 1: Generating categories.md...');
try {
  execSync('node ' + path.join(__dirname, 'generate-categories.js'), {
    stdio: 'inherit'
  });
  console.log('✅ Categories generated\n');
} catch (error) {
  console.error('❌ Failed to generate categories:', error.message);
  process.exit(1);
}

// Step 2: Generate tags.md
console.log('🏷️  Step 2: Generating tags.md...');
try {
  execSync('node ' + path.join(__dirname, 'generate-tags.js'), {
    stdio: 'inherit'
  });
  console.log('✅ Tags generated\n');
} catch (error) {
  console.error('❌ Failed to generate tags:', error.message);
  process.exit(1);
}

// Step 3: Build README.md
console.log('📖 Step 3: Building README.md...');
try {
  execSync('node ' + path.join(__dirname, 'build-readme.js'), {
    stdio: 'inherit',
    env: process.env // Pass environment variables including .env
  });
  console.log('✅ README built\n');
} catch (error) {
  console.error('❌ Failed to build README:', error.message);
  process.exit(1);
}

console.log('🎉 All build tasks completed successfully!');
