#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const db = require('./db');

// Read categories from SQLite
const categories = db.prepare('SELECT id, name, description, parent_id as parentId FROM categories').all();

// Build a map for quick parent lookup
const categoriesMap = new Map();
categories.forEach(cat => {
  categoriesMap.set(cat.id, cat);
});

// Group categories by parent
const rootCategories = [];
const childrenMap = new Map();

categories.forEach(cat => {
  if (cat.parentId === null) {
    rootCategories.push(cat);
  } else {
    if (!childrenMap.has(cat.parentId)) {
      childrenMap.set(cat.parentId, []);
    }
    childrenMap.get(cat.parentId).push(cat);
  }
});

// Generate markdown
let markdown = '# Categories\n\n';
markdown += 'This document lists all available categories in the repository, organized hierarchically.\n\n';
markdown += '---\n\n';

// Function to render a category and its children recursively
function renderCategory(category, level = 2) {
  let output = '';
  const heading = '#'.repeat(level);

  output += `${heading} ${category.name}\n\n`;
  output += `${category.description}\n\n`;

  // Render children if any
  const children = childrenMap.get(category.id);
  if (children && children.length > 0) {
    children.sort((a, b) => a.name.localeCompare(b.name));
    children.forEach(child => {
      output += renderCategory(child, level + 1);
    });
  }

  return output;
}

// Render all root categories
rootCategories.sort((a, b) => a.name.localeCompare(b.name));
rootCategories.forEach(category => {
  markdown += renderCategory(category);
});

// Write to categories.md
const outputPath = path.join(__dirname, '../categories.md');
fs.writeFileSync(outputPath, markdown, 'utf8');

console.log(`✅ Generated categories.md with ${categories.length} categories`);
