#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const db = require('./db');

// Read tags from SQLite
const tags = db.prepare('SELECT id, name, description FROM tags').all();

// Generate markdown
let markdown = '# Tags\n\n';
markdown += 'This document lists all available tags in the repository for classifying projects.\n\n';
markdown += 'Tags are used to indicate the type of interface or use case for a project.\n\n';
markdown += '---\n\n';

// Sort tags alphabetically
const sortedTags = tags.sort((a, b) => a.name.localeCompare(b.name));

// Render each tag
sortedTags.forEach(tag => {
  markdown += `## ${tag.name}\n\n`;
  markdown += `**ID:** \`${tag.id}\`\n\n`;
  markdown += `${tag.description}\n\n`;
});

// Write to tags.md
const outputPath = path.join(__dirname, '../tags.md');
fs.writeFileSync(outputPath, markdown, 'utf8');

console.log(`✅ Generated tags.md with ${tags.length} tags`);
