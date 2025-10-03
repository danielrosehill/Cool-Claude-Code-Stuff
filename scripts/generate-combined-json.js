#!/usr/bin/env node

require('dotenv').config();

const fs = require('fs');
const path = require('path');
const https = require('https');

// File paths
const CATEGORIES_FILE = path.join(__dirname, '../../data/categories.json');
const RESOURCES_FILE = path.join(__dirname, '../../data/resources.json');
const CACHE_FILE = path.join(__dirname, '../../data/repo-cache.json');
const OUTPUT_FILE = path.join(__dirname, '../../data/combined.json');

// Load data
function loadData() {
    try {
        const categoriesData = JSON.parse(fs.readFileSync(CATEGORIES_FILE, 'utf8'));
        const resourcesData = JSON.parse(fs.readFileSync(RESOURCES_FILE, 'utf8'));
        return { categories: categoriesData.categories, resources: resourcesData };
    } catch (error) {
        console.error('Error loading data files:', error.message);
        process.exit(1);
    }
}

// Load cache
function loadCache() {
    try {
        if (fs.existsSync(CACHE_FILE)) {
            return JSON.parse(fs.readFileSync(CACHE_FILE, 'utf8'));
        }
    } catch (error) {
        console.warn('Warning: Could not load cache:', error.message);
    }
    return {};
}

// Save cache
function saveCache(cache) {
    try {
        fs.writeFileSync(CACHE_FILE, JSON.stringify(cache, null, 2), 'utf8');
    } catch (error) {
        console.warn('Warning: Could not save cache:', error.message);
    }
}

// Extract owner and repo name from GitHub URL
function parseGitHubUrl(url) {
    const match = url.match(/github\.com\/([^\/]+)\/([^\/]+)/);
    if (match) {
        return { owner: match[1], repo: match[2] };
    }
    return null;
}

// Fetch GitHub repo info
function fetchGitHubInfo(owner, repo) {
    return new Promise((resolve, reject) => {
        const options = {
            hostname: 'api.github.com',
            path: `/repos/${owner}/${repo}`,
            method: 'GET',
            headers: {
                'User-Agent': 'Awesome-Claude-Code-Build-Script',
                'Accept': 'application/vnd.github.v3+json'
            }
        };

        // Add GitHub token if available
        const token = process.env.GITHUB_TOKEN;
        if (token) {
            options.headers['Authorization'] = `token ${token}`;
        }

        const req = https.request(options, (res) => {
            let data = '';

            res.on('data', (chunk) => {
                data += chunk;
            });

            res.on('end', () => {
                if (res.statusCode === 200) {
                    try {
                        const repoData = JSON.parse(data);
                        resolve({
                            description: repoData.description || '',
                            stars: repoData.stargazers_count,
                            lastUpdated: repoData.updated_at
                        });
                    } catch (error) {
                        reject(new Error(`Failed to parse GitHub response: ${error.message}`));
                    }
                } else {
                    reject(new Error(`GitHub API returned status ${res.statusCode}`));
                }
            });
        });

        req.on('error', (error) => {
            reject(error);
        });

        req.setTimeout(5000, () => {
            req.destroy();
            reject(new Error('Request timeout'));
        });

        req.end();
    });
}

// Fetch descriptions for all repositories
async function enrichRepositoriesWithDescriptions(repositories) {
    const cache = loadCache();
    const enriched = [];
    let fetchCount = 0;
    let cacheHits = 0;
    let errors = 0;

    console.log(`Fetching descriptions for ${repositories.length} repositories...\n`);

    for (const repo of repositories) {
        const parsed = parseGitHubUrl(repo.url);
        if (!parsed) {
            enriched.push(repo);
            continue;
        }

        const cacheKey = `${parsed.owner}/${parsed.repo}`;

        // Check cache first
        if (cache[cacheKey] && cache[cacheKey].description !== undefined) {
            cacheHits++;
            process.stdout.write('.');
            enriched.push({
                ...repo,
                description: repo.notes || repo.description || cache[cacheKey].description,
                githubData: cache[cacheKey]
            });
            continue;
        }

        // Fetch from GitHub API
        try {
            const info = await fetchGitHubInfo(parsed.owner, parsed.repo);
            cache[cacheKey] = info;
            fetchCount++;
            process.stdout.write('+');
            enriched.push({
                ...repo,
                description: repo.notes || repo.description || info.description,
                githubData: info
            });

            // Rate limiting: GitHub allows 60 requests/hour without auth, 5000 with auth
            // Add a small delay to be respectful
            await new Promise(resolve => setTimeout(resolve, 100));
        } catch (error) {
            errors++;
            process.stdout.write('x');
            console.error(`\nError fetching ${cacheKey}: ${error.message}`);
            enriched.push(repo);
        }
    }

    console.log(`\n\nResults:`);
    console.log(`- Cache hits: ${cacheHits}`);
    console.log(`- Fetched from API: ${fetchCount}`);
    console.log(`- Errors: ${errors}`);

    if (fetchCount > 0 || errors > 0) {
        saveCache(cache);
        console.log('✓ Cache updated\n');
    }

    return enriched;
}

// Build hierarchical category tree
function buildCategoryTree(categories, parentId = null) {
    return categories
        .filter(cat => cat.parentId === parentId)
        .sort((a, b) => a.name.localeCompare(b.name))
        .map(cat => ({
            ...cat,
            subcategories: buildCategoryTree(categories, cat.id)
        }));
}

// Organize repositories by category
function organizeRepositories(repositories, categories) {
    const organized = {};

    // Create a map for quick category lookup
    const categoryMap = {};
    categories.forEach(cat => {
        categoryMap[cat.id] = cat;
    });

    // Group repositories by category
    repositories.forEach(repo => {
        if (!organized[repo.categoryId]) {
            organized[repo.categoryId] = [];
        }
        organized[repo.categoryId].push(repo);
    });

    // Sort repositories within each category
    Object.keys(organized).forEach(categoryId => {
        organized[categoryId].sort((a, b) => a.name.localeCompare(b.name));
    });

    return organized;
}

// Generate combined data structure
function generateCombinedData(data) {
    const { categories, resources } = data;
    const { meta, repositories } = resources;

    // Build category tree
    const categoryTree = buildCategoryTree(categories);

    // Organize repositories by category
    const repositoriesByCategory = organizeRepositories(repositories, categories);

    // Create combined structure
    const combined = {
        meta: {
            ...meta,
            generatedAt: new Date().toISOString(),
            totalCategories: categories.length,
            totalRepositories: repositories.length
        },
        categories: categoryTree,
        repositories: repositoriesByCategory,
        allRepositories: repositories
    };

    return combined;
}

// Write combined JSON file
function writeCombinedJson(content) {
    try {
        fs.writeFileSync(OUTPUT_FILE, JSON.stringify(content, null, 2), 'utf8');
        console.log('✓ combined.json generated successfully');
    } catch (error) {
        console.error('Error writing combined.json file:', error.message);
        process.exit(1);
    }
}

// Main
async function main() {
    console.log('Generating combined.json...\n');

    const data = loadData();

    // Enrich repositories with GitHub descriptions
    data.resources.repositories = await enrichRepositoriesWithDescriptions(data.resources.repositories);

    // Generate combined data
    const combined = generateCombinedData(data);

    // Write to file
    writeCombinedJson(combined);

    // Print stats
    const topLevelCategories = data.categories.filter(cat => !cat.parentId);
    const subcategories = data.categories.filter(cat => cat.parentId);
    console.log(`\nStats:`);
    console.log(`- Top-level categories: ${topLevelCategories.length}`);
    console.log(`- Subcategories: ${subcategories.length}`);
    console.log(`- Total repositories: ${data.resources.repositories.length}`);
    console.log(`\nOutput: ${OUTPUT_FILE}`);
}

// Run
main().catch(error => {
    console.error('Fatal error:', error);
    process.exit(1);
});
