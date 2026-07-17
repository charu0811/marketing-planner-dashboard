import sqlite3
import os
import hashlib
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "tasks.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_connection()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY,
        content TEXT NOT NULL,
        type TEXT DEFAULT '',
        date TEXT DEFAULT '',
        owner TEXT DEFAULT '',
        status TEXT DEFAULT 'To Do',
        approval TEXT DEFAULT 'Draft',
        comment TEXT DEFAULT '',
        link TEXT DEFAULT '',
        priority TEXT DEFAULT '',
        source TEXT DEFAULT '',
        created_at TEXT DEFAULT '',
        updated_at TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS task_platforms (
        task_id TEXT NOT NULL,
        platform TEXT NOT NULL,
        FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
        PRIMARY KEY (task_id, platform)
    );

    CREATE TABLE IF NOT EXISTS platforms (
        name TEXT PRIMARY KEY
    );

    CREATE TABLE IF NOT EXISTS owners (
        name TEXT PRIMARY KEY
    );

    CREATE TABLE IF NOT EXISTS import_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT,
        imported_at TEXT,
        row_count INTEGER
    );
    """)
    conn.commit()

    # Seed default platforms
    default_platforms = [
        'Instagram', 'LinkedIn', 'YouTube', 'WhatsApp', 'Blog',
        'Customer.io', 'Instantly', 'Twitter/X', 'Facebook', 'Loom'
    ]
    for p in default_platforms:
        conn.execute("INSERT OR IGNORE INTO platforms (name) VALUES (?)", (p,))

    # Seed default owners
    default_owners = ['Mahek', 'Charu', 'Samriddhi', 'Aamir', 'Winston', 'Akshit']
    for o in default_owners:
        conn.execute("INSERT OR IGNORE INTO owners (name) VALUES (?)", (o,))

    conn.commit()
    conn.close()


# --- Platform normalization ---
PLATFORM_MAP = {
    'instagram': 'Instagram',
    'linkedin': 'LinkedIn',
    'youtube': 'YouTube',
    'yt': 'YouTube',
    'whatsapp': 'WhatsApp',
    'whtsapp': 'WhatsApp',
    'wa': 'WhatsApp',
    'blog': 'Blog',
    'customer.io': 'Customer.io',
    'instantly': 'Instantly',
    'twitter/x': 'Twitter/X',
    'twitter': 'Twitter/X',
    'facebook': 'Facebook',
    'loom': 'Loom',
    'update': 'WhatsApp',
    'updates': 'WhatsApp',
    'update grp': 'WhatsApp',
}


def normalize_platforms(raw_platform_str):
    """Parse a messy platform string like 'whatsapp update group/youtube' into clean platform list."""
    if not raw_platform_str or raw_platform_str.strip() == '':
        return []

    raw = raw_platform_str.lower().strip()
    # Split on /, comma, &
    parts = []
    for sep in ['/', ',', '&']:
        if sep in raw:
            parts = [p.strip() for p in raw.split(sep) if p.strip()]
            break
    if not parts:
        parts = [raw]

    result = set()
    for part in parts:
        part = part.strip()
        # Remove common noise words
        for noise in ['update group', 'update grp', 'vid', 'video']:
            part = part.replace(noise, '').strip()
        # Direct match
        if part in PLATFORM_MAP:
            result.add(PLATFORM_MAP[part])
        else:
            # Fuzzy: check if any key is substring of part or vice versa
            matched = False
            for key, val in PLATFORM_MAP.items():
                if key in part or part in key:
                    result.add(val)
                    matched = True
                    break
            if not matched and part:
                # Capitalize as-is
                result.add(part.title())

    return sorted(result)


def normalize_status(raw):
    """Normalize status to canonical values."""
    if not raw:
        return 'To Do'
    s = raw.strip()
    mapping = {
        'done': 'Done',
        'in progress': 'In Progress',
        'to do': 'To Do',
        'carryforward': 'Carryforward',
        'carryfoward': 'Carryforward',
        'blocked': 'Blocked',
        'completed': 'Done',
        '-': 'To Do',
    }
    return mapping.get(s.lower(), s)


def normalize_approval(raw):
    """Normalize approval status."""
    if not raw:
        return 'Draft'
    s = raw.strip()
    mapping = {
        'approved': 'Approved',
        'to be approved': 'To be approved',
        'in progress': 'In Progress',
        'rejected': 'Rejected',
        'draft': 'Draft',
    }
    return mapping.get(s.lower(), s)


def normalize_type(raw):
    """Normalize content type."""
    if not raw:
        return ''
    s = raw.strip()
    mapping = {
        'content': 'Content',
        'campaign': 'Campaign',
        'camoaign': 'Campaign',
        'carousel': 'Carousel',
        'reel': 'REEL',
        'teaser video': 'Teaser Video',
        'internal prep': 'Internal Prep',
        'email campaign': 'Email Campaign',
        'kite': 'Content',
        'linkedin': 'Content',
        'customer.io': 'Campaign',
        'research': 'Research',
        'creatives': 'Creatives',
        'documentation': 'Documentation',
    }
    return mapping.get(s.lower(), s.title())


def make_task_id(content, date, owner):
    """Generate a deterministic ID from task content+date+owner."""
    raw = f"{content}|{date}|{owner}"
    return "xl_" + hashlib.md5(raw.encode()).hexdigest()[:12]


def import_from_excel(filepath):
    """Import all data from the Marketing Planner Excel file."""
    import openpyxl

    wb = openpyxl.load_workbook(filepath, data_only=True)
    conn = get_connection()
    now = datetime.now().isoformat()
    imported_count = 0

    # --- 1. Marketing Calendar sheet (primary data source) ---
    if 'Marketing Calendar' in wb.sheetnames:
        ws = wb['Marketing Calendar']
        for row in ws.iter_rows(min_row=3, max_row=ws.max_row, values_only=True):
            if not row[0] or not isinstance(row[0], datetime):
                continue
            date_str = row[0].strftime('%Y-%m-%d')
            content = str(row[2] or '').strip()
            if not content:
                continue

            task_type = normalize_type(str(row[3] or ''))
            platforms = normalize_platforms(str(row[4] or ''))
            status = normalize_status(str(row[5] or ''))
            owner = str(row[6] or '').strip()
            approval = normalize_approval(str(row[7] or ''))
            comment = str(row[8] or '').strip()
            link = str(row[9] or '').strip()
            if link == 'None':
                link = ''

            task_id = make_task_id(content, date_str, owner)

            conn.execute("""
                INSERT OR REPLACE INTO tasks (id, content, type, date, owner, status, approval, comment, link, priority, source, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (task_id, content, task_type, date_str, owner, status, approval, comment, link, '', 'Marketing Calendar', now, now))

            conn.execute("DELETE FROM task_platforms WHERE task_id = ?", (task_id,))
            for p in platforms:
                conn.execute("INSERT OR IGNORE INTO task_platforms (task_id, platform) VALUES (?, ?)", (task_id, p))
                conn.execute("INSERT OR IGNORE INTO platforms (name) VALUES (?)", (p,))

            if owner:
                conn.execute("INSERT OR IGNORE INTO owners (name) VALUES (?)", (owner,))
            imported_count += 1

    # Log the import
    conn.execute("INSERT INTO import_log (filename, imported_at, row_count) VALUES (?, ?, ?)",
                 (os.path.basename(filepath), now, imported_count))
    conn.commit()
    conn.close()
    return imported_count


def is_imported():
    """Check if Excel data has already been imported."""
    conn = get_connection()
    row = conn.execute("SELECT COUNT(*) as c FROM import_log").fetchone()
    conn.close()
    return row['c'] > 0


# --- CRUD Operations ---

def get_all_tasks():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM tasks ORDER BY date ASC").fetchall()
    tasks = []
    for row in rows:
        t = dict(row)
        plats = conn.execute("SELECT platform FROM task_platforms WHERE task_id = ?", (t['id'],)).fetchall()
        t['platforms'] = [p['platform'] for p in plats]
        tasks.append(t)
    conn.close()
    return tasks


def get_task(task_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if not row:
        conn.close()
        return None
    t = dict(row)
    plats = conn.execute("SELECT platform FROM task_platforms WHERE task_id = ?", (task_id,)).fetchall()
    t['platforms'] = [p['platform'] for p in plats]
    conn.close()
    return t


def create_task(task_data):
    conn = get_connection()
    now = datetime.now().isoformat()
    conn.execute("""
        INSERT INTO tasks (id, content, type, date, owner, status, approval, comment, link, priority, source, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        task_data['id'], task_data['content'], task_data.get('type', ''),
        task_data.get('date', ''), task_data.get('owner', ''),
        task_data.get('status', 'To Do'), task_data.get('approval', 'Draft'),
        task_data.get('comment', ''), task_data.get('link', ''),
        task_data.get('priority', ''), 'Manual', now, now
    ))
    for p in task_data.get('platforms', []):
        conn.execute("INSERT OR IGNORE INTO task_platforms (task_id, platform) VALUES (?, ?)", (task_data['id'], p))
        conn.execute("INSERT OR IGNORE INTO platforms (name) VALUES (?)", (p,))
    if task_data.get('owner'):
        conn.execute("INSERT OR IGNORE INTO owners (name) VALUES (?)", (task_data['owner'],))
    conn.commit()
    conn.close()


def update_task(task_id, task_data):
    conn = get_connection()
    now = datetime.now().isoformat()
    conn.execute("""
        UPDATE tasks SET content=?, type=?, date=?, owner=?, status=?, approval=?, comment=?, link=?, priority=?, updated_at=?
        WHERE id=?
    """, (
        task_data['content'], task_data.get('type', ''),
        task_data.get('date', ''), task_data.get('owner', ''),
        task_data.get('status', 'To Do'), task_data.get('approval', 'Draft'),
        task_data.get('comment', ''), task_data.get('link', ''),
        task_data.get('priority', ''), now, task_id
    ))
    conn.execute("DELETE FROM task_platforms WHERE task_id = ?", (task_id,))
    for p in task_data.get('platforms', []):
        conn.execute("INSERT OR IGNORE INTO task_platforms (task_id, platform) VALUES (?, ?)", (task_id, p))
        conn.execute("INSERT OR IGNORE INTO platforms (name) VALUES (?)", (p,))
    if task_data.get('owner'):
        conn.execute("INSERT OR IGNORE INTO owners (name) VALUES (?)", (task_data['owner'],))
    conn.commit()
    conn.close()


def delete_task(task_id):
    conn = get_connection()
    conn.execute("DELETE FROM task_platforms WHERE task_id = ?", (task_id,))
    conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()


def update_task_status(task_id, new_status):
    conn = get_connection()
    now = datetime.now().isoformat()
    conn.execute("UPDATE tasks SET status=?, updated_at=? WHERE id=?", (new_status, now, task_id))
    conn.commit()
    conn.close()


def get_all_platforms():
    conn = get_connection()
    rows = conn.execute("SELECT name FROM platforms ORDER BY name").fetchall()
    conn.close()
    return [r['name'] for r in rows]


def get_all_owners():
    conn = get_connection()
    rows = conn.execute("SELECT name FROM owners ORDER BY name").fetchall()
    conn.close()
    return [r['name'] for r in rows]


def add_platform(name):
    conn = get_connection()
    conn.execute("INSERT OR IGNORE INTO platforms (name) VALUES (?)", (name,))
    conn.commit()
    conn.close()


def add_owner(name):
    conn = get_connection()
    conn.execute("INSERT OR IGNORE INTO owners (name) VALUES (?)", (name,))
    conn.commit()
    conn.close()


def get_stats():
    """Get dashboard statistics."""
    conn = get_connection()
    stats = {}
    stats['total'] = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    stats['approved'] = conn.execute("SELECT COUNT(*) FROM tasks WHERE approval='Approved'").fetchone()[0]
    stats['pending'] = conn.execute("SELECT COUNT(*) FROM tasks WHERE approval IN ('To be approved','In Progress')").fetchone()[0]
    stats['rejected'] = conn.execute("SELECT COUNT(*) FROM tasks WHERE approval='Rejected'").fetchone()[0]
    stats['done'] = conn.execute("SELECT COUNT(*) FROM tasks WHERE status='Done'").fetchone()[0]
    stats['in_progress'] = conn.execute("SELECT COUNT(*) FROM tasks WHERE status='In Progress'").fetchone()[0]
    stats['todo'] = conn.execute("SELECT COUNT(*) FROM tasks WHERE status='To Do'").fetchone()[0]
    stats['blocked'] = conn.execute("SELECT COUNT(*) FROM tasks WHERE status='Blocked'").fetchone()[0]

    # Per owner
    rows = conn.execute("SELECT owner, COUNT(*) as c FROM tasks WHERE owner != '' GROUP BY owner ORDER BY c DESC").fetchall()
    stats['by_owner'] = [(r['owner'], r['c']) for r in rows]

    # Per platform
    rows = conn.execute("SELECT platform, COUNT(*) as c FROM task_platforms GROUP BY platform ORDER BY c DESC").fetchall()
    stats['by_platform'] = [(r['platform'], r['c']) for r in rows]

    conn.close()
    return stats


def reset_db():
    """Drop all data and re-initialize."""
    conn = get_connection()
    conn.executescript("""
        DELETE FROM task_platforms;
        DELETE FROM tasks;
        DELETE FROM import_log;
    """)
    conn.commit()
    conn.close()
