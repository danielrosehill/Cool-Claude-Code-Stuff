#!/usr/bin/env node

require('dotenv').config();

const fs = require('fs');
const path = require('path');
const https = require('https');

// File paths
const CATEGORIES_FILE = path.join(__dirname, '../data/categories.json');
const RESOURCES_FILE = path.join(__dirname, '../data/resources.json');
const README_FILE = path.join(__dirname, '../README.md');
const TOC_FILE = path.join(__dirname, '../toc.md');
const CACHE_FILE = path.join(__dirname, '../data/repo-cache.json');

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

// Generate anchor for links
function generateAnchor(text) {
    return text.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '');
}

// Extract owner and repo name from GitHub URL
function parseGitHubUrl(url) {
    const match = url.match(/github\.com\/([^\/]+)\/([^\/]+)/);
    if (match) {
        return { owner: match[1], repo: match[2] };
    }
    return null;
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
        const token = process.env.GITHUB_TOKEN || process.env.GITHUB_API_KEY;
        if (token) {
            // Use 'Bearer' for fine-grained tokens (github_pat_*), 'token' for classic tokens (ghp_*)
            const authType = token.startsWith('github_pat_') ? 'Bearer' : 'token';
            options.headers['Authorization'] = `${authType} ${token}`;
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
                description: repo.description || cache[cacheKey].description
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
                description: repo.description || info.description
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

// Generate badges for a repository
function generateRepoBadges(url) {
    const parsed = parseGitHubUrl(url);
    if (!parsed) return '';

    const { owner, repo } = parsed;
    const viewRepoBadge = `[![View Repo](https://img.shields.io/badge/View-Repo-blue?style=flat-square&logo=github)](${url})`;
    const starsBadge = `![Stars](https://img.shields.io/github/stars/${owner}/${repo}?style=flat-square&logo=github)`;
    const lastCommitBadge = `![Last Commit](https://img.shields.io/github/last-commit/${owner}/${repo}?style=flat-square&logo=github)`;

    return `${viewRepoBadge} ${starsBadge} ${lastCommitBadge}`;
}

// Generate README content
function generateReadme(data) {
    const { categories, resources } = data;
    const { meta, repositories } = resources;

    let readme = `# ${meta.title}\n\n`;
    readme += `${meta.description}\n\n`;
    readme += `*Last updated: ${meta.lastUpdated}*\n\n`;
    readme += `📑 [View Table of Contents](toc.md)\n\n`;
    readme += `---\n\n`;

    // Get top-level categories and sort alphabetically
    const topLevelCategories = categories
        .filter(cat => !cat.parentId)
        .sort((a, b) => a.name.localeCompare(b.name));

    // Generate separate TOC file
    let toc = `# Table of Contents\n\n`;
    topLevelCategories.forEach(cat => {
        const anchor = generateAnchor(cat.name);
        toc += `- [${cat.name}](README.md#${anchor})\n`;
    });
    toc += `\n`;

    // Write TOC file
    try {
        fs.writeFileSync(TOC_FILE, toc, 'utf8');
    } catch (error) {
        console.error('Error writing TOC file:', error.message);
    }

    // Categories with hierarchical structure
    topLevelCategories.forEach(cat => {
        // Repos in this category, sorted alphabetically by name
        const categoryRepos = repositories
            .filter(r => {
                if (r.categoryId) return r.categoryId === cat.id;
                if (r.categoryIds) return r.categoryIds.includes(cat.id);
                return false;
            })
            .sort((a, b) => a.name.localeCompare(b.name));

        // Subcategories, sorted alphabetically
        const subcategories = categories
            .filter(c => c.parentId === cat.id)
            .sort((a, b) => a.name.localeCompare(b.name));

        // Filter subcategories to only include those with repos
        const subcategoriesWithRepos = subcategories.filter(subcat => {
            const subcatRepos = repositories.filter(r => {
                if (r.categoryId) return r.categoryId === subcat.id;
                if (r.categoryIds) return r.categoryIds.includes(subcat.id);
                return false;
            });
            return subcatRepos.length > 0;
        });

        // Skip category if it has no repos and no subcategories with repos
        if (categoryRepos.length === 0 && subcategoriesWithRepos.length === 0) {
            return;
        }

        readme += `# ${cat.name}\n\n`;
        readme += `${cat.description}\n\n`;
        readme += `---\n\n`;

        if (categoryRepos.length > 0) {
            categoryRepos.forEach(repo => {
                readme += `### ${repo.name}\n\n`;
                const description = repo.description || '';
                if (description) {
                    readme += `${description}\n\n`;
                }
                readme += `${generateRepoBadges(repo.url)}\n\n`;
                readme += `---\n\n`;
            });
        }

        subcategoriesWithRepos.forEach(subcat => {
            readme += `### ${subcat.name}\n\n`;
            readme += `${subcat.description}\n\n`;

            const subcatRepos = repositories
                .filter(r => {
                    if (r.categoryId) return r.categoryId === subcat.id;
                    if (r.categoryIds) return r.categoryIds.includes(subcat.id);
                    return false;
                })
                .sort((a, b) => a.name.localeCompare(b.name));

            subcatRepos.forEach(repo => {
                readme += `#### ${repo.name}\n\n`;
                const description = repo.description || '';
                if (description) {
                    readme += `${description}\n\n`;
                }
                readme += `${generateRepoBadges(repo.url)}\n\n`;
                readme += `---\n\n`;
            });
        });
    });

    // Footer
    readme += `---\n\n`;
    readme += `## License\n\n`;
    readme += `This list is available under the MIT License.\n\n`;
    readme += `---\n\n`;
    readme += `## Private\n\n`;
    readme += `### Repository Count Tracker\n`;
    const today = new Date().toISOString().split('T')[0];
    readme += `- **${today}**: ${repositories.length} repositories\n`;

    return readme;
}

// Write README file
function writeReadme(content) {
    try {
        fs.writeFileSync(README_FILE, content, 'utf8');
        console.log('✓ README.md generated successfully');
    } catch (error) {
        console.error('Error writing README file:', error.message);
        process.exit(1);
    }
}

// Main
async function main() {
    console.log('Building README.md from categories.json and resources.json...\n');

    const data = loadData();

    // Enrich repositories with GitHub descriptions
    data.resources.repositories = await enrichRepositoriesWithDescriptions(data.resources.repositories);

    const readme = generateReadme(data);
    writeReadme(readme);

    // Print stats
    const topLevelCategories = data.categories.filter(cat => !cat.parentId);
    const subcategories = data.categories.filter(cat => cat.parentId);
    console.log(`\nStats:`);
    console.log(`- Top-level categories: ${topLevelCategories.length}`);
    console.log(`- Subcategories: ${subcategories.length}`);
    console.log(`- Total repositories: ${data.resources.repositories.length}`);
}

// Run
main().catch(error => {
    console.error('Fatal error:', error);
    process.exit(1);
});
