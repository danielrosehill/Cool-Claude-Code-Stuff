const Database = require('better-sqlite3');
const path = require('path');

const dbPath = path.join(__dirname, '../data/awesome_claude_code.db');
const db = new Database(dbPath, { readonly: true });

module.exports = db;
