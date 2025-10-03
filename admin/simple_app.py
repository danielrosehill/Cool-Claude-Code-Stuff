from flask import Flask, render_template_string, request, jsonify, redirect
import sqlite3
import os
from datetime import date

app = Flask(__name__)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB_PATH = os.path.join(BASE_DIR, 'data', 'awesome_claude_code.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_hierarchical_categories():
    """Get categories with hierarchy information"""
    conn = get_db()
    cats = conn.execute('SELECT * FROM categories').fetchall()
    conn.close()

    # Convert to list of dicts
    cat_dict = {cat['id']: dict(cat) for cat in cats}

    # Build hierarchy info
    for cat_id, cat_data in cat_dict.items():
        cat_data['level'] = 0
        cat_data['parent_name'] = None
        cat_data['children'] = []

        # Calculate level and parent name
        parent_id = cat_data.get('parent_id')
        level = 0
        while parent_id and parent_id in cat_dict:
            level += 1
            if level == 1:
                cat_data['parent_name'] = cat_dict[parent_id]['name']
            parent_id = cat_dict[parent_id].get('parent_id')

        cat_data['level'] = min(level, 2)

    # Build children lists
    for cat_id, cat_data in cat_dict.items():
        parent_id = cat_data.get('parent_id')
        if parent_id and parent_id in cat_dict:
            cat_dict[parent_id]['children'].append(cat_id)

    # Sort children by name
    for cat_data in cat_dict.values():
        cat_data['children'].sort(key=lambda cid: cat_dict[cid]['name'])

    # Build flat list with hierarchy: parents followed by their children
    result = []

    # Get top-level categories (no parent)
    top_level = sorted([c for c in cat_dict.values() if not c.get('parent_id')],
                      key=lambda x: x['name'])

    # Add each top-level category and its children
    for parent in top_level:
        result.append(parent)
        # Add direct children
        for child_id in parent['children']:
            result.append(cat_dict[child_id])

    return result

def extract_repo_name(url):
    """Extract repository name from GitHub URL"""
    import re
    match = re.search(r'github\.com/[^/]+/([^/]+?)(\.git)?$', url)
    if match:
        return match.group(1)
    return None

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Awesome Claude Code Manager</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }
        h1 { color: #333; }
        .nav { margin: 20px 0; }
        .nav a { margin-right: 15px; padding: 10px 15px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; }
        .nav a:hover { background: #0056b3; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #f8f9fa; font-weight: bold; }
        tr:hover { background: #f5f5f5; }
        .form-group { margin: 15px 0; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        input, textarea, select { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; }
        textarea { min-height: 100px; }
        button { padding: 10px 20px; background: #28a745; color: white; border: none; border-radius: 4px; cursor: pointer; }
        button:hover { background: #218838; }
        .delete-btn { background: #dc3545; padding: 5px 10px; }
        .delete-btn:hover { background: #c82333; }
        .small-text { font-size: 0.9em; color: #666; }
        .search-box { margin-bottom: 10px; }
        .indent-1 { padding-left: 20px; }
        .indent-2 { padding-left: 40px; }
    </style>
</head>
<body>
    <h1>Awesome Claude Code Manager</h1>
    <div class="nav">
        <a href="/">Home</a>
        <a href="/repositories">Repositories</a>
        <a href="/categories">Categories</a>
        <a href="/tags">Tags</a>
    </div>
    {% block content %}{% endblock %}
</body>
</html>
'''

HOME_TEMPLATE = HTML_TEMPLATE.replace('{% block content %}{% endblock %}', '''
    <h2>Welcome to Awesome Claude Code Manager</h2>
    <p>Manage your awesome list of Claude Code resources.</p>
    <ul>
        <li><a href="/repositories">Manage Repositories</a></li>
        <li><a href="/categories">Manage Categories</a></li>
        <li><a href="/tags">Manage Tags</a></li>
    </ul>
''')

REPOSITORIES_TEMPLATE = HTML_TEMPLATE.replace('{% block content %}{% endblock %}', '''
    <h2>Repositories</h2>
    <a href="/repositories/add" style="display: inline-block; margin-bottom: 20px; padding: 10px 20px; background: #28a745; color: white; text-decoration: none; border-radius: 4px;">Add New Repository</a>
    <table>
        <tr>
            <th>Name</th>
            <th>URL</th>
            <th>Description</th>
            <th>Added</th>
            <th>Actions</th>
        </tr>
        {% for repo in repositories %}
        <tr>
            <td><strong>{{ repo.name }}</strong></td>
            <td><a href="{{ repo.url }}" target="_blank" class="small-text">{{ repo.url }}</a></td>
            <td>{{ repo.description or '' }}</td>
            <td>{{ repo.added }}</td>
            <td>
                <a href="/repositories/edit?url={{ repo.url }}" style="padding: 5px 10px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; margin-right: 5px;">Edit</a>
                <form method="POST" action="/repositories/delete" style="display: inline;">
                    <input type="hidden" name="url" value="{{ repo.url }}">
                    <button type="submit" class="delete-btn" onclick="return confirm('Delete this repository?')">Delete</button>
                </form>
            </td>
        </tr>
        {% endfor %}
    </table>
''')

ADD_REPOSITORY_TEMPLATE = HTML_TEMPLATE.replace('{% block content %}{% endblock %}', '''
    <h2>Add New Repository</h2>
    <form method="POST">
        <div class="form-group">
            <label>Repository URL *</label>
            <input type="text" name="url" id="repo-url" required placeholder="https://github.com/user/repo" oninput="updateRepoName()">
        </div>
        <div class="form-group">
            <label>Name (optional - defaults to repo name from URL)</label>
            <input type="text" name="name" id="repo-name" placeholder="Will be extracted from URL">
        </div>
        <div class="form-group">
            <label>Description (optional)</label>
            <textarea name="description"></textarea>
        </div>
        <div class="form-group">
            <label>Categories</label>
            <input type="text" id="category-search" class="search-box" placeholder="Search categories..." onkeyup="filterCategories()">
            <div id="category-list" style="max-height: 200px; overflow-y: auto; border: 1px solid #ddd; padding: 10px; border-radius: 4px;">
                {% for cat in categories %}
                <div style="margin: 5px 0;" class="category-item {% if cat.parent_id %}indent-{{ cat.level }}{% endif %}">
                    <label style="font-weight: normal; display: inline;">
                        <input type="checkbox" name="categories" value="{{ cat.id }}" style="width: auto; margin-right: 5px;">
                        {{ cat.name }}{% if cat.parent_id %} <span style="color: #999;">({{ cat.parent_name }})</span>{% endif %}
                    </label>
                </div>
                {% endfor %}
            </div>
        </div>
        <div class="form-group">
            <label>Tags</label>
            <input type="text" id="tag-search" class="search-box" placeholder="Search tags..." onkeyup="filterTags()">
            <div id="tag-list" style="max-height: 200px; overflow-y: auto; border: 1px solid #ddd; padding: 10px; border-radius: 4px;">
                {% for tag in tags %}
                <div style="margin: 5px 0;" class="tag-item">
                    <label style="font-weight: normal; display: inline;">
                        <input type="checkbox" name="tags" value="{{ tag.id }}" style="width: auto; margin-right: 5px;">
                        {{ tag.name }}
                    </label>
                </div>
                {% endfor %}
            </div>
        </div>
        <div class="form-group">
            <label>Date Added</label>
            <input type="date" name="added" value="{{ today }}">
        </div>
        <div class="form-group">
            <label>Notes (optional)</label>
            <textarea name="notes"></textarea>
        </div>
        <button type="submit">Add Repository</button>
        <a href="/repositories" style="margin-left: 10px;">Cancel</a>
    </form>
    <script>
        function updateRepoName() {
            const url = document.getElementById('repo-url').value;
            const nameInput = document.getElementById('repo-name');
            if (!nameInput.value || nameInput.placeholder.includes('extracted')) {
                const match = url.match(/github\\.com\\/([^\\/]+)\\/([^\\/]+?)(\\.git)?$/);
                if (match) {
                    nameInput.placeholder = match[2];
                }
            }
        }
        function filterCategories() {
            const search = document.getElementById('category-search').value.toLowerCase();
            const items = document.querySelectorAll('.category-item');
            items.forEach(item => {
                const text = item.textContent.toLowerCase();
                item.style.display = text.includes(search) ? '' : 'none';
            });
        }
        function filterTags() {
            const search = document.getElementById('tag-search').value.toLowerCase();
            const items = document.querySelectorAll('.tag-item');
            items.forEach(item => {
                const text = item.textContent.toLowerCase();
                item.style.display = text.includes(search) ? '' : 'none';
            });
        }
    </script>
''')

EDIT_REPOSITORY_TEMPLATE = HTML_TEMPLATE.replace('{% block content %}{% endblock %}', '''
    <h2>Edit Repository</h2>
    <form method="POST">
        <div class="form-group">
            <label>Repository URL *</label>
            <input type="text" name="url" required value="{{ repo.url }}" readonly style="background: #f5f5f5;">
        </div>
        <div class="form-group">
            <label>Name</label>
            <input type="text" name="name" value="{{ repo.name }}">
        </div>
        <div class="form-group">
            <label>Description (optional)</label>
            <textarea name="description">{{ repo.description or '' }}</textarea>
        </div>
        <div class="form-group">
            <label>Categories</label>
            <input type="text" id="category-search" class="search-box" placeholder="Search categories..." onkeyup="filterCategories()">
            <div id="category-list" style="max-height: 200px; overflow-y: auto; border: 1px solid #ddd; padding: 10px; border-radius: 4px;">
                {% for cat in categories %}
                <div style="margin: 5px 0;" class="category-item {% if cat.parent_id %}indent-{{ cat.level }}{% endif %}">
                    <label style="font-weight: normal; display: inline;">
                        <input type="checkbox" name="categories" value="{{ cat.id }}" style="width: auto; margin-right: 5px;" {% if cat.id in selected_categories %}checked{% endif %}>
                        {{ cat.name }}{% if cat.parent_id %} <span style="color: #999;">({{ cat.parent_name }})</span>{% endif %}
                    </label>
                </div>
                {% endfor %}
            </div>
        </div>
        <div class="form-group">
            <label>Tags</label>
            <input type="text" id="tag-search" class="search-box" placeholder="Search tags..." onkeyup="filterTags()">
            <div id="tag-list" style="max-height: 200px; overflow-y: auto; border: 1px solid #ddd; padding: 10px; border-radius: 4px;">
                {% for tag in tags %}
                <div style="margin: 5px 0;" class="tag-item">
                    <label style="font-weight: normal; display: inline;">
                        <input type="checkbox" name="tags" value="{{ tag.id }}" style="width: auto; margin-right: 5px;" {% if tag.id in selected_tags %}checked{% endif %}>
                        {{ tag.name }}
                    </label>
                </div>
                {% endfor %}
            </div>
        </div>
        <div class="form-group">
            <label>Date Added</label>
            <input type="date" name="added" value="{{ repo.added }}">
        </div>
        <div class="form-group">
            <label>Notes (optional)</label>
            <textarea name="notes">{{ repo.notes or '' }}</textarea>
        </div>
        <button type="submit">Update Repository</button>
        <a href="/repositories" style="margin-left: 10px;">Cancel</a>
    </form>
    <script>
        function filterCategories() {
            const search = document.getElementById('category-search').value.toLowerCase();
            const items = document.querySelectorAll('.category-item');
            items.forEach(item => {
                const text = item.textContent.toLowerCase();
                item.style.display = text.includes(search) ? '' : 'none';
            });
        }
        function filterTags() {
            const search = document.getElementById('tag-search').value.toLowerCase();
            const items = document.querySelectorAll('.tag-item');
            items.forEach(item => {
                const text = item.textContent.toLowerCase();
                item.style.display = text.includes(search) ? '' : 'none';
            });
        }
    </script>
''')

CATEGORIES_TEMPLATE = HTML_TEMPLATE.replace('{% block content %}{% endblock %}', '''
    <h2>Categories</h2>
    <a href="/categories/add" style="display: inline-block; margin-bottom: 20px; padding: 10px 20px; background: #28a745; color: white; text-decoration: none; border-radius: 4px;">Add New Category</a>
    <table>
        <tr>
            <th>ID</th>
            <th>Name</th>
            <th>Description</th>
            <th>Parent</th>
            <th>Actions</th>
        </tr>
        {% for cat in categories %}
        <tr>
            <td>{{ cat.id }}</td>
            <td><strong>{{ cat.name }}</strong></td>
            <td>{{ cat.description }}</td>
            <td>{{ cat.parent_id or '-' }}</td>
            <td>
                <a href="/categories/edit?id={{ cat.id }}" style="padding: 5px 10px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; margin-right: 5px;">Edit</a>
                <form method="POST" action="/categories/delete" style="display: inline;">
                    <input type="hidden" name="id" value="{{ cat.id }}">
                    <button type="submit" class="delete-btn" onclick="return confirm('Delete this category?')">Delete</button>
                </form>
            </td>
        </tr>
        {% endfor %}
    </table>
''')

ADD_CATEGORY_TEMPLATE = HTML_TEMPLATE.replace('{% block content %}{% endblock %}', '''
    <h2>Add New Category</h2>
    <form method="POST">
        <div class="form-group">
            <label>Category ID *</label>
            <input type="text" name="id" required placeholder="my-category">
        </div>
        <div class="form-group">
            <label>Name *</label>
            <input type="text" name="name" required>
        </div>
        <div class="form-group">
            <label>Description *</label>
            <textarea name="description" required></textarea>
        </div>
        <div class="form-group">
            <label>Parent Category</label>
            <select name="parent_id">
                <option value="">None</option>
                {% for cat in categories %}
                <option value="{{ cat.id }}">{{ cat.name }}</option>
                {% endfor %}
            </select>
        </div>
        <button type="submit">Add Category</button>
        <a href="/categories" style="margin-left: 10px;">Cancel</a>
    </form>
''')

EDIT_CATEGORY_TEMPLATE = HTML_TEMPLATE.replace('{% block content %}{% endblock %}', '''
    <h2>Edit Category</h2>
    <form method="POST">
        <div class="form-group">
            <label>Category ID *</label>
            <input type="text" name="id" required value="{{ category.id }}" readonly style="background: #f5f5f5;">
        </div>
        <div class="form-group">
            <label>Name *</label>
            <input type="text" name="name" required value="{{ category.name }}">
        </div>
        <div class="form-group">
            <label>Description *</label>
            <textarea name="description" required>{{ category.description }}</textarea>
        </div>
        <div class="form-group">
            <label>Parent Category</label>
            <select name="parent_id">
                <option value="">None</option>
                {% for cat in categories %}
                {% if cat.id != category.id %}
                <option value="{{ cat.id }}" {% if cat.id == category.parent_id %}selected{% endif %}>{{ cat.name }}</option>
                {% endif %}
                {% endfor %}
            </select>
        </div>
        <button type="submit">Update Category</button>
        <a href="/categories" style="margin-left: 10px;">Cancel</a>
    </form>
''')

TAGS_TEMPLATE = HTML_TEMPLATE.replace('{% block content %}{% endblock %}', '''
    <h2>Tags</h2>
    <a href="/tags/add" style="display: inline-block; margin-bottom: 20px; padding: 10px 20px; background: #28a745; color: white; text-decoration: none; border-radius: 4px;">Add New Tag</a>
    <table>
        <tr>
            <th>ID</th>
            <th>Name</th>
            <th>Description</th>
            <th>Actions</th>
        </tr>
        {% for tag in tags %}
        <tr>
            <td>{{ tag.id }}</td>
            <td><strong>{{ tag.name }}</strong></td>
            <td>{{ tag.description }}</td>
            <td>
                <a href="/tags/edit?id={{ tag.id }}" style="padding: 5px 10px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; margin-right: 5px;">Edit</a>
                <form method="POST" action="/tags/delete" style="display: inline;">
                    <input type="hidden" name="id" value="{{ tag.id }}">
                    <button type="submit" class="delete-btn" onclick="return confirm('Delete this tag?')">Delete</button>
                </form>
            </td>
        </tr>
        {% endfor %}
    </table>
''')

ADD_TAG_TEMPLATE = HTML_TEMPLATE.replace('{% block content %}{% endblock %}', '''
    <h2>Add New Tag</h2>
    <form method="POST">
        <div class="form-group">
            <label>Tag ID *</label>
            <input type="text" name="id" required placeholder="my-tag">
        </div>
        <div class="form-group">
            <label>Name *</label>
            <input type="text" name="name" required>
        </div>
        <div class="form-group">
            <label>Description *</label>
            <textarea name="description" required></textarea>
        </div>
        <button type="submit">Add Tag</button>
        <a href="/tags" style="margin-left: 10px;">Cancel</a>
    </form>
''')

EDIT_TAG_TEMPLATE = HTML_TEMPLATE.replace('{% block content %}{% endblock %}', '''
    <h2>Edit Tag</h2>
    <form method="POST">
        <div class="form-group">
            <label>Tag ID *</label>
            <input type="text" name="id" required value="{{ tag.id }}" readonly style="background: #f5f5f5;">
        </div>
        <div class="form-group">
            <label>Name *</label>
            <input type="text" name="name" required value="{{ tag.name }}">
        </div>
        <div class="form-group">
            <label>Description *</label>
            <textarea name="description" required>{{ tag.description }}</textarea>
        </div>
        <button type="submit">Update Tag</button>
        <a href="/tags" style="margin-left: 10px;">Cancel</a>
    </form>
''')

@app.route('/')
def index():
    return render_template_string(HOME_TEMPLATE)

@app.route('/repositories')
def repositories():
    conn = get_db()
    repos = conn.execute('SELECT * FROM repositories ORDER BY added DESC').fetchall()
    conn.close()
    return render_template_string(REPOSITORIES_TEMPLATE, repositories=repos)

@app.route('/repositories/add', methods=['GET', 'POST'])
def add_repository():
    conn = get_db()
    if request.method == 'POST':
        url = request.form['url']
        name = request.form.get('name', '').strip()

        # If name is empty, extract from URL
        if not name:
            name = extract_repo_name(url) or 'Unknown Repository'

        # Insert repository
        conn.execute(
            'INSERT INTO repositories (url, name, description, added, notes) VALUES (?, ?, ?, ?, ?)',
            (url, name, request.form.get('description'),
             request.form.get('added', str(date.today())), request.form.get('notes'))
        )

        # Insert categories
        categories = request.form.getlist('categories')
        for cat_id in categories:
            conn.execute(
                'INSERT INTO repository_categories (repository_url, category_id) VALUES (?, ?)',
                (url, cat_id)
            )

        # Insert tags
        tags = request.form.getlist('tags')
        for tag_id in tags:
            conn.execute(
                'INSERT INTO repository_tags (repository_url, tag_id) VALUES (?, ?)',
                (url, tag_id)
            )

        conn.commit()
        conn.close()
        return redirect('/repositories')

    # GET request - load categories and tags
    categories = get_hierarchical_categories()
    tags = conn.execute('SELECT * FROM tags ORDER BY name').fetchall()
    conn.close()
    return render_template_string(ADD_REPOSITORY_TEMPLATE, today=str(date.today()),
                                   categories=categories, tags=tags)

@app.route('/repositories/edit', methods=['GET', 'POST'])
def edit_repository():
    conn = get_db()
    url = request.args.get('url') if request.method == 'GET' else request.form['url']

    if request.method == 'POST':
        name = request.form.get('name', '').strip()

        # If name is empty, extract from URL
        if not name:
            name = extract_repo_name(url) or 'Unknown Repository'

        # Update repository
        conn.execute(
            'UPDATE repositories SET name = ?, description = ?, added = ?, notes = ? WHERE url = ?',
            (name, request.form.get('description'),
             request.form.get('added'), request.form.get('notes'), url)
        )

        # Delete existing categories and tags
        conn.execute('DELETE FROM repository_categories WHERE repository_url = ?', (url,))
        conn.execute('DELETE FROM repository_tags WHERE repository_url = ?', (url,))

        # Insert new categories
        categories = request.form.getlist('categories')
        for cat_id in categories:
            conn.execute(
                'INSERT INTO repository_categories (repository_url, category_id) VALUES (?, ?)',
                (url, cat_id)
            )

        # Insert new tags
        tags = request.form.getlist('tags')
        for tag_id in tags:
            conn.execute(
                'INSERT INTO repository_tags (repository_url, tag_id) VALUES (?, ?)',
                (url, tag_id)
            )

        conn.commit()
        conn.close()
        return redirect('/repositories')

    # GET request - load repository data
    repo = conn.execute('SELECT * FROM repositories WHERE url = ?', (url,)).fetchone()
    categories = get_hierarchical_categories()
    tags = conn.execute('SELECT * FROM tags ORDER BY name').fetchall()

    # Get selected categories and tags
    selected_categories = [row['category_id'] for row in
                          conn.execute('SELECT category_id FROM repository_categories WHERE repository_url = ?', (url,)).fetchall()]
    selected_tags = [row['tag_id'] for row in
                    conn.execute('SELECT tag_id FROM repository_tags WHERE repository_url = ?', (url,)).fetchall()]

    conn.close()
    return render_template_string(EDIT_REPOSITORY_TEMPLATE, repo=repo, categories=categories,
                                 tags=tags, selected_categories=selected_categories,
                                 selected_tags=selected_tags)

@app.route('/repositories/delete', methods=['POST'])
def delete_repository():
    conn = get_db()
    conn.execute('DELETE FROM repositories WHERE url = ?', (request.form['url'],))
    conn.commit()
    conn.close()
    return redirect('/repositories')

@app.route('/categories')
def categories():
    conn = get_db()
    cats = conn.execute('SELECT * FROM categories ORDER BY name').fetchall()
    conn.close()
    return render_template_string(CATEGORIES_TEMPLATE, categories=cats)

@app.route('/categories/add', methods=['GET', 'POST'])
def add_category():
    conn = get_db()
    if request.method == 'POST':
        parent = request.form.get('parent_id')
        conn.execute(
            'INSERT INTO categories (id, name, description, parent_id) VALUES (?, ?, ?, ?)',
            (request.form['id'], request.form['name'], request.form['description'],
             parent if parent else None)
        )
        conn.commit()
        conn.close()
        return redirect('/categories')
    cats = conn.execute('SELECT * FROM categories ORDER BY name').fetchall()
    conn.close()
    return render_template_string(ADD_CATEGORY_TEMPLATE, categories=cats)

@app.route('/categories/edit', methods=['GET', 'POST'])
def edit_category():
    conn = get_db()
    cat_id = request.args.get('id') if request.method == 'GET' else request.form['id']

    if request.method == 'POST':
        parent = request.form.get('parent_id')
        conn.execute(
            'UPDATE categories SET name = ?, description = ?, parent_id = ? WHERE id = ?',
            (request.form['name'], request.form['description'],
             parent if parent else None, cat_id)
        )
        conn.commit()
        conn.close()
        return redirect('/categories')

    category = conn.execute('SELECT * FROM categories WHERE id = ?', (cat_id,)).fetchone()
    cats = conn.execute('SELECT * FROM categories ORDER BY name').fetchall()
    conn.close()
    return render_template_string(EDIT_CATEGORY_TEMPLATE, category=category, categories=cats)

@app.route('/categories/delete', methods=['POST'])
def delete_category():
    conn = get_db()
    conn.execute('DELETE FROM categories WHERE id = ?', (request.form['id'],))
    conn.commit()
    conn.close()
    return redirect('/categories')

@app.route('/tags')
def tags():
    conn = get_db()
    tag_list = conn.execute('SELECT * FROM tags ORDER BY name').fetchall()
    conn.close()
    return render_template_string(TAGS_TEMPLATE, tags=tag_list)

@app.route('/tags/add', methods=['GET', 'POST'])
def add_tag():
    if request.method == 'POST':
        conn = get_db()
        conn.execute(
            'INSERT INTO tags (id, name, description) VALUES (?, ?, ?)',
            (request.form['id'], request.form['name'], request.form['description'])
        )
        conn.commit()
        conn.close()
        return redirect('/tags')
    return render_template_string(ADD_TAG_TEMPLATE)

@app.route('/tags/edit', methods=['GET', 'POST'])
def edit_tag():
    conn = get_db()
    tag_id = request.args.get('id') if request.method == 'GET' else request.form['id']

    if request.method == 'POST':
        conn.execute(
            'UPDATE tags SET name = ?, description = ? WHERE id = ?',
            (request.form['name'], request.form['description'], tag_id)
        )
        conn.commit()
        conn.close()
        return redirect('/tags')

    tag = conn.execute('SELECT * FROM tags WHERE id = ?', (tag_id,)).fetchone()
    conn.close()
    return render_template_string(EDIT_TAG_TEMPLATE, tag=tag)

@app.route('/tags/delete', methods=['POST'])
def delete_tag():
    conn = get_db()
    conn.execute('DELETE FROM tags WHERE id = ?', (request.form['id'],))
    conn.commit()
    conn.close()
    return redirect('/tags')

if __name__ == '__main__':
    app.run(debug=True, port=5001)
