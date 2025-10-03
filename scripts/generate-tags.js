#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

// Read the tags.json file
const tagsPath = path.join(__dirname, '../data/tags.json');
const tagsData = JSON.parse(fs.readFileSync(tagsPath, 'utf8'));

// Generate markdown
let markdown = '# Tags\n\n';
markdown += 'This document lists all available tags in the repository for classifying projects.\n\n';
markdown += 'Tags are used to indicate the type of interface or use case for a project.\n\n';
markdown += '---\n\n';

// Sort tags alphabetically
const sortedTags = tagsData.tags.sort((a, b) => a.name.localeCompare(b.name));

// Render each tag
sortedTags.forEach(tag => {
  markdown += `## ${tag.name}\n\n`;
  markdown += `**ID:** \`${tag.id}\`\n\n`;
  markdown += `${tag.description}\n\n`;
});

// Write to tags.md
const outputPath = path.join(__dirname, '../tags.md');
fs.writeFileSync(outputPath, markdown, 'utf8');

console.log(`✅ Generated tags.md with ${tagsData.tags.length} tags`);
