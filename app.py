import streamlit as st
import uuid
import os
from datetime import datetime, timedelta
import database as db
from onedrive_sync import render_onedrive_sidebar, is_onedrive_configured, backup_db_to_onedrive
import urllib.parse

# --- Page Config ---
st.set_page_config(
    page_title="Wylth — Marketing Task Manager",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Constants ---
STATUS_OPTIONS = ['To Do', 'In Progress', 'Done', 'Carryforward', 'Blocked']
APPROVAL_OPTIONS = ['Draft', 'To be approved', 'In Progress', 'Approved', 'Rejected']
TYPE_OPTIONS = ['Content', 'Campaign', 'Carousel', 'REEL', 'Teaser Video', 'Internal Prep', 'Email Campaign', 'Research', 'Creatives', 'Documentation']

EXCEL_FILE = os.path.join(os.path.dirname(__file__), "Marketing Planner (Product Team) (1).xlsx")

# --- Init DB & Import ---
db.init_db()

# Auto-import Excel on first run
if not db.is_imported() and os.path.exists(EXCEL_FILE):
    count = db.import_from_excel(EXCEL_FILE)
    st.toast(f"✅ Imported {count} tasks from Excel spreadsheet!")

# --- Custom CSS ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,400;0,9..144,500;1,9..144,300;1,9..144,400&family=Inter:wght@300;400;500;600;700&display=swap');

.stApp { font-family: 'Inter', sans-serif; }
.main-header { font-family: 'Fraunces', serif; font-size: 2rem; font-weight: 400; margin-bottom: 0; }
.main-header em { color: #00BAB2; font-style: italic; }
.eyebrow { font-size: 0.65rem; font-weight: 600; letter-spacing: 0.32em; text-transform: uppercase; color: #00BAB2; margin-bottom: 4px; }

.stat-card { padding: 14px 16px; border-radius: 10px; border: 1px solid rgba(48,48,47,0.13); background: #fff; text-align: center; }
.stat-card.approved { border-color: rgba(0,186,178,0.3); background: rgba(0,186,178,0.08); }
.stat-card.pending { border-color: rgba(201,138,44,0.35); background: rgba(201,138,44,0.08); }
.stat-card.rejected { border-color: rgba(194,71,46,0.35); background: rgba(194,71,46,0.08); }
.stat-card.done { border-color: rgba(0,186,178,0.3); background: rgba(0,186,178,0.05); }
.stat-num { font-size: 1.5rem; font-weight: 700; }
.stat-label { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.05em; color: rgba(48,48,47,0.65); }

.task-card { background: #FFFCF9; border: 1px solid rgba(48,48,47,0.13); border-radius: 8px; padding: 14px; margin-bottom: 8px; transition: 0.15s; }
.task-card:hover { border-color: rgba(0,186,178,0.3); box-shadow: 0 2px 10px rgba(0,0,0,0.04); }
.task-title { font-family: 'Fraunces', serif; font-size: 0.9rem; line-height: 1.3; margin-bottom: 6px; }
.task-meta { font-size: 0.7rem; color: rgba(48,48,47,0.42); }
.platform-tag { font-size: 0.65rem; font-weight: 500; padding: 2px 8px; border-radius: 10px; background: rgba(0,186,178,0.12); color: #00857f; border: 1px solid rgba(0,186,178,0.3); display: inline-block; margin: 2px 2px; }
.approval-pill { font-size: 0.6rem; font-weight: 600; padding: 3px 8px; border-radius: 9px; text-transform: uppercase; letter-spacing: 0.03em; display: inline-block; }
.ap-draft { background: rgba(48,48,47,0.13); color: rgba(48,48,47,0.65); }
.ap-to-be-approved { background: rgba(201,138,44,0.12); color: #C98A2C; }
.ap-in-progress { background: rgba(0,186,178,0.12); color: #00857f; }
.ap-approved { background: #00BAB2; color: #fff; }
.ap-rejected { background: #C2472E; color: #fff; }
.owner-badge { width: 24px; height: 24px; border-radius: 50%; background: #30302F; color: #fff; font-size: 0.6rem; font-weight: 600; display: inline-flex; align-items: center; justify-content: center; }
.col-header { font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; padding: 10px 0; border-bottom: 1px solid rgba(48,48,47,0.13); margin-bottom: 10px; }
.week-label { font-family: 'Fraunces', serif; font-style: italic; color: #00BAB2; font-size: 1rem; }
.source-badge { font-size: 0.6rem; padding: 2px 6px; border-radius: 8px; background: rgba(48,48,47,0.06); color: rgba(48,48,47,0.5); display: inline-block; }
</style>
""", unsafe_allow_html=True)


# --- Helper Functions ---
def get_week_bounds(date):
    day_of_week = date.weekday()
    monday = date - timedelta(days=day_of_week)
    sunday = monday + timedelta(days=6)
    return monday, sunday


def format_week_label(monday, sunday):
    return f"Week of {monday.strftime('%b %d')} – {sunday.strftime('%b %d')}"


def get_approval_class(approval):
    return "ap-" + (approval or "draft").lower().replace(" ", "-")


def initials(name):
    if not name:
        return "?"
    return "".join(w[0] for w in name.split() if w)[:2].upper()


def generate_utm_link(base_url, source, medium, campaign):
    if not base_url:
        return ""
    if not base_url.startswith(("http://", "https://")):
        base_url = "https://" + base_url
    params = {
        'utm_source': source or 'direct',
        'utm_medium': medium or 'social',
        'utm_campaign': campaign or 'campaign',
    }
    separator = '&' if '?' in base_url else '?'
    return base_url + separator + urllib.parse.urlencode(params)


# --- Session State Init ---
if 'view' not in st.session_state:
    st.session_state.view = 'board'
if 'week_offset' not in st.session_state:
    st.session_state.week_offset = 0
if 'show_all_weeks' not in st.session_state:
    st.session_state.show_all_weeks = False
if 'editing_task' not in st.session_state:
    st.session_state.editing_task = None
if 'show_form' not in st.session_state:
    st.session_state.show_form = False


# --- Header ---
st.markdown('<div class="eyebrow">Product Team</div>', unsafe_allow_html=True)
st.markdown('<h1 class="main-header">Marketing <em>Task Manager</em></h1>', unsafe_allow_html=True)
st.caption("Plan, tag, assign and track every post across channels.")

# --- Stats ---
stats = db.get_stats()

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.markdown(f'<div class="stat-card"><div class="stat-num">{stats["total"]}</div><div class="stat-label">Total Tasks</div></div>', unsafe_allow_html=True)
with col2:
    st.markdown(f'<div class="stat-card done"><div class="stat-num" style="color:#00BAB2">{stats["done"]}</div><div class="stat-label">Done</div></div>', unsafe_allow_html=True)
with col3:
    st.markdown(f'<div class="stat-card approved"><div class="stat-num" style="color:#00BAB2">{stats["approved"]}</div><div class="stat-label">Approved</div></div>', unsafe_allow_html=True)
with col4:
    st.markdown(f'<div class="stat-card pending"><div class="stat-num" style="color:#C98A2C">{stats["pending"]}</div><div class="stat-label">Pending</div></div>', unsafe_allow_html=True)
with col5:
    st.markdown(f'<div class="stat-card rejected"><div class="stat-num" style="color:#C2472E">{stats["rejected"]}</div><div class="stat-label">Rejected</div></div>', unsafe_allow_html=True)

st.divider()

# --- Tabs ---
tab_dashboard, tab_analytics, tab_import = st.tabs(["📋 Tasks", "📊 Analytics", "📥 Import & Sync"])

# ===========================
# TAB: TASKS
# ===========================
with tab_dashboard:
    # --- Week Navigation ---
    today = datetime.now().date()
    current_monday, current_sunday = get_week_bounds(today)
    selected_monday = current_monday + timedelta(weeks=st.session_state.week_offset)
    selected_sunday = selected_monday + timedelta(days=6)

    wcol1, wcol2, wcol3, wcol4, wcol5 = st.columns([1, 1, 4, 1, 1])
    with wcol1:
        if st.button("◀ Prev", use_container_width=True):
            st.session_state.week_offset -= 1
            st.session_state.show_all_weeks = False
            st.rerun()
    with wcol2:
        if st.button("This Week", use_container_width=True):
            st.session_state.week_offset = 0
            st.session_state.show_all_weeks = False
            st.rerun()
    with wcol3:
        if st.session_state.show_all_weeks:
            st.markdown('<p class="week-label" style="text-align:center;">Showing all weeks</p>', unsafe_allow_html=True)
        else:
            is_current = st.session_state.week_offset == 0
            badge = ' <span style="color:#00BAB2;font-size:0.7rem;">(CURRENT)</span>' if is_current else ''
            st.markdown(f'<p class="week-label" style="text-align:center;">{format_week_label(selected_monday, selected_sunday)}{badge}</p>', unsafe_allow_html=True)
    with wcol4:
        if st.button("Next ▶", use_container_width=True):
            st.session_state.week_offset += 1
            st.session_state.show_all_weeks = False
            st.rerun()
    with wcol5:
        if st.button("All Weeks", use_container_width=True):
            st.session_state.show_all_weeks = not st.session_state.show_all_weeks
            st.rerun()

    st.divider()

    # --- Get & Filter Tasks ---
    all_tasks = db.get_all_tasks()

    # --- Sidebar Filters ---
    with st.sidebar:
        st.markdown("### 🔍 Filters")
        search_query = st.text_input("Search tasks", placeholder="Search by content, comment, type...")
        owner_filter = st.selectbox("Owner", ["All"] + db.get_all_owners())
        status_filter = st.selectbox("Status", ["All"] + STATUS_OPTIONS)
        approval_filter = st.selectbox("Approval", ["All"] + APPROVAL_OPTIONS)
        platform_filter = st.multiselect("Platforms", db.get_all_platforms())

        st.divider()
        st.markdown("### 📊 View")
        view_option = st.radio("Display mode", ["Board", "List"], horizontal=True,
                               index=0 if st.session_state.view == 'board' else 1)
        if view_option.lower() != st.session_state.view:
            st.session_state.view = view_option.lower()
            st.rerun()

        st.divider()
        if st.button("➕ New Task", use_container_width=True, type="primary"):
            st.session_state.show_form = True
            st.session_state.editing_task = None
            st.rerun()

        st.divider()
        # OneDrive section
        render_onedrive_sidebar()

    # --- Filter logic ---
    def filter_tasks(tasks):
        filtered = []
        for t in tasks:
            if not st.session_state.show_all_weeks and t['date']:
                try:
                    task_date = datetime.strptime(t['date'], '%Y-%m-%d').date()
                    task_monday, _ = get_week_bounds(task_date)
                    if task_monday != selected_monday:
                        continue
                except ValueError:
                    continue
            elif not st.session_state.show_all_weeks and not t['date']:
                continue

            if search_query:
                haystack = f"{t['content']} {t['comment']} {t['type']} {t.get('source','')}".lower()
                if search_query.lower() not in haystack:
                    continue
            if owner_filter != "All" and t['owner'] != owner_filter:
                continue
            if status_filter != "All" and t['status'] != status_filter:
                continue
            if approval_filter != "All" and t['approval'] != approval_filter:
                continue
            if platform_filter:
                if not any(p in t.get('platforms', []) for p in platform_filter):
                    continue
            filtered.append(t)
        return filtered

    filtered_tasks = filter_tasks(all_tasks)

    # --- Task Form (Create/Edit) ---
    if st.session_state.show_form:
        task = None
        if st.session_state.editing_task:
            task = db.get_task(st.session_state.editing_task)

        with st.form("task_form", clear_on_submit=True):
            st.markdown(f"### {'Edit Task' if task else 'New Task'}")

            content = st.text_area("Content / Description", value=task['content'] if task else "",
                                   placeholder="e.g. Carousel post on payday effect")

            fcol1, fcol2 = st.columns(2)
            with fcol1:
                type_idx = TYPE_OPTIONS.index(task['type']) if task and task['type'] in TYPE_OPTIONS else 0
                task_type = st.selectbox("Type", TYPE_OPTIONS, index=type_idx)
            with fcol2:
                default_date = datetime.strptime(task['date'], '%Y-%m-%d').date() if task and task['date'] else today
                task_date = st.date_input("Date", value=default_date)

            platforms = st.multiselect("Platform Tags", db.get_all_platforms(),
                                       default=task['platforms'] if task else [])

            fcol3, fcol4, fcol5 = st.columns(3)
            with fcol3:
                owners_list = db.get_all_owners()
                own_idx = owners_list.index(task['owner']) if task and task['owner'] in owners_list else 0
                owner = st.selectbox("Owner", owners_list, index=own_idx)
            with fcol4:
                stat_idx = STATUS_OPTIONS.index(task['status']) if task and task['status'] in STATUS_OPTIONS else 0
                status = st.selectbox("Status", STATUS_OPTIONS, index=stat_idx)
            with fcol5:
                appr_idx = APPROVAL_OPTIONS.index(task['approval']) if task and task['approval'] in APPROVAL_OPTIONS else 0
                approval = st.selectbox("Approval Status", APPROVAL_OPTIONS, index=appr_idx)

            fcol6, fcol7 = st.columns(2)
            with fcol6:
                comment = st.text_area("Comment", value=task['comment'] if task else "",
                                       placeholder="Notes, blockers, context...")
            with fcol7:
                link = st.text_input("Post / Content Link", value=task['link'] if task else "",
                                     placeholder="https://...")
                priority = st.selectbox("Priority", ['', 'High', 'Medium', 'Low'],
                                        index=['', 'High', 'Medium', 'Low'].index(task.get('priority', '')) if task and task.get('priority', '') in ['', 'High', 'Medium', 'Low'] else 0)

            # UTM Builder
            with st.expander("🔗 Link Generator — build a tracked share link"):
                ucol1, ucol2 = st.columns(2)
                with ucol1:
                    utm_base = st.text_input("Base URL", placeholder="https://wylth.com/...")
                    utm_medium = st.selectbox("Medium", ['social', 'email', 'referral', 'whatsapp', 'organic'])
                with ucol2:
                    utm_source = st.text_input("Source", placeholder="instagram")
                    utm_campaign = st.text_input("Campaign", placeholder="auto from content")
                if utm_base:
                    generated_link = generate_utm_link(utm_base, utm_source, utm_medium, utm_campaign)
                    st.code(generated_link, language=None)
                    st.caption("Copy the link above and paste it into the Post/Content Link field")

            bcol1, bcol2, bcol3 = st.columns([2, 1, 1])
            with bcol1:
                submitted = st.form_submit_button("💾 Save Task", type="primary", use_container_width=True)
            with bcol2:
                cancelled = st.form_submit_button("Cancel", use_container_width=True)
            with bcol3:
                deleted = st.form_submit_button("🗑️ Delete", use_container_width=True) if task else False

            if submitted and content:
                task_data = {
                    'id': task['id'] if task else f"t_{uuid.uuid4().hex[:10]}",
                    'content': content,
                    'type': task_type,
                    'date': task_date.strftime('%Y-%m-%d'),
                    'owner': owner,
                    'status': status,
                    'approval': approval,
                    'comment': comment,
                    'link': link,
                    'platforms': platforms,
                    'priority': priority,
                }
                if task:
                    db.update_task(task['id'], task_data)
                    st.toast("✅ Task updated!")
                else:
                    db.create_task(task_data)
                    st.toast("✅ Task created!")
                st.session_state.show_form = False
                st.session_state.editing_task = None
                st.rerun()

            if cancelled:
                st.session_state.show_form = False
                st.session_state.editing_task = None
                st.rerun()

            if deleted and task:
                db.delete_task(task['id'])
                st.toast("🗑️ Task deleted!")
                st.session_state.show_form = False
                st.session_state.editing_task = None
                st.rerun()

    # --- Board View ---
    elif st.session_state.view == 'board':
        if not filtered_tasks:
            st.info("No tasks match the current filters. Try adjusting the week or clearing filters.")
        else:
            cols = st.columns(len(STATUS_OPTIONS))
            for idx, status_col in enumerate(STATUS_OPTIONS):
                with cols[idx]:
                    status_tasks = [t for t in filtered_tasks if (t['status'] or 'To Do') == status_col]
                    st.markdown(f'<div class="col-header">{status_col} ({len(status_tasks)})</div>', unsafe_allow_html=True)

                    if not status_tasks:
                        st.caption("No tasks")
                    else:
                        for t in status_tasks:
                            plat_tags = " ".join(f'<span class="platform-tag">{p}</span>' for p in t.get('platforms', []))
                            ap_class = get_approval_class(t['approval'])
                            date_str = datetime.strptime(t['date'], '%Y-%m-%d').strftime('%b %d') if t['date'] else 'No date'
                            link_icon = "🔗" if t.get('link') else ""
                            source_badge = f'<span class="source-badge">{t.get("source", "")}</span>' if t.get('source') else ''

                            card_html = f"""
                            <div class="task-card">
                                <div class="task-title">{t['content'] or '(untitled)'}</div>
                                <div class="task-meta">{t.get('type', '—')} · {date_str} {source_badge}</div>
                                <div style="margin:6px 0;">{plat_tags or '<span class="platform-tag" style="opacity:0.4">no tag</span>'}</div>
                                <div style="display:flex;justify-content:space-between;align-items:center;">
                                    <span class="owner-badge">{initials(t['owner'])}</span>
                                    <span>{link_icon} <span class="approval-pill {ap_class}">{t['approval'] or 'Draft'}</span></span>
                                </div>
                            </div>
                            """
                            st.markdown(card_html, unsafe_allow_html=True)
                            if st.button("Edit", key=f"edit_{t['id']}", use_container_width=True):
                                st.session_state.editing_task = t['id']
                                st.session_state.show_form = True
                                st.rerun()

    # --- List View ---
    elif st.session_state.view == 'list':
        if not filtered_tasks:
            st.info("No tasks match the current filters. Try adjusting the week or clearing filters.")
        else:
            weeks = {}
            for t in sorted(filtered_tasks, key=lambda x: x['date'] or '9999'):
                if t['date']:
                    try:
                        td = datetime.strptime(t['date'], '%Y-%m-%d').date()
                        mon, sun = get_week_bounds(td)
                        wk_label = format_week_label(mon, sun)
                    except ValueError:
                        wk_label = "No date"
                else:
                    wk_label = "No date"
                weeks.setdefault(wk_label, []).append(t)

            for wk_label, tasks_in_week in weeks.items():
                if st.session_state.show_all_weeks:
                    st.markdown(f'<p class="week-label">{wk_label}</p>', unsafe_allow_html=True)

                hcol1, hcol2, hcol3, hcol4, hcol5, hcol6, hcol7 = st.columns([1, 3, 2, 1.2, 1.2, 1.2, 0.5])
                with hcol1:
                    st.caption("DATE")
                with hcol2:
                    st.caption("TASK")
                with hcol3:
                    st.caption("PLATFORMS")
                with hcol4:
                    st.caption("STATUS")
                with hcol5:
                    st.caption("OWNER")
                with hcol6:
                    st.caption("APPROVAL")
                with hcol7:
                    st.caption("")

                for t in tasks_in_week:
                    lcol1, lcol2, lcol3, lcol4, lcol5, lcol6, lcol7 = st.columns([1, 3, 2, 1.2, 1.2, 1.2, 0.5])
                    with lcol1:
                        if t['date']:
                            td = datetime.strptime(t['date'], '%Y-%m-%d').date()
                            st.markdown(f"**{td.strftime('%b %d')}**  \n{td.strftime('%a')}")
                        else:
                            st.write("—")
                    with lcol2:
                        source_txt = f" · {t.get('source', '')}" if t.get('source') else ''
                        st.markdown(f"**{t['content'] or '(untitled)'}**  \n<span style='font-size:0.7rem;color:gray;'>{t.get('type', '')}{source_txt}</span>", unsafe_allow_html=True)
                    with lcol3:
                        plat_str = ", ".join(t.get('platforms', [])[:3])
                        extra = f" +{len(t['platforms'])-3}" if len(t.get('platforms', [])) > 3 else ""
                        st.write(f"{plat_str}{extra}" if plat_str else "—")
                    with lcol4:
                        st.write(t['status'] or 'To Do')
                    with lcol5:
                        st.markdown(f'<span class="owner-badge">{initials(t["owner"])}</span> {t["owner"]}', unsafe_allow_html=True)
                    with lcol6:
                        ap_class = get_approval_class(t['approval'])
                        st.markdown(f'<span class="approval-pill {ap_class}">{t["approval"] or "Draft"}</span>', unsafe_allow_html=True)
                    with lcol7:
                        if st.button("✏️", key=f"ledit_{t['id']}"):
                            st.session_state.editing_task = t['id']
                            st.session_state.show_form = True
                            st.rerun()
                st.divider()

# ===========================
# TAB: ANALYTICS
# ===========================
with tab_analytics:
    import pandas as pd

    st.markdown("### 📊 Task Analytics")

    acol1, acol2 = st.columns(2)

    with acol1:
        st.markdown("#### Tasks by Owner")
        if stats['by_owner']:
            df_owner = pd.DataFrame(stats['by_owner'], columns=['Owner', 'Tasks'])
            st.bar_chart(df_owner.set_index('Owner'))
        else:
            st.caption("No data")

    with acol2:
        st.markdown("#### Tasks by Platform")
        if stats['by_platform']:
            df_plat = pd.DataFrame(stats['by_platform'], columns=['Platform', 'Tasks'])
            st.bar_chart(df_plat.set_index('Platform'))
        else:
            st.caption("No data")

    st.divider()

    acol3, acol4 = st.columns(2)
    with acol3:
        st.markdown("#### Status Breakdown")
        status_data = {
            'Status': ['To Do', 'In Progress', 'Done', 'Carryforward', 'Blocked'],
            'Count': [stats['todo'], stats['in_progress'], stats['done'],
                      stats['total'] - stats['todo'] - stats['in_progress'] - stats['done'] - stats['blocked'],
                      stats['blocked']]
        }
        df_status = pd.DataFrame(status_data)
        st.bar_chart(df_status.set_index('Status'))

    with acol4:
        st.markdown("#### Approval Breakdown")
        approval_data = {
            'Approval': ['Approved', 'Pending', 'Rejected', 'Draft'],
            'Count': [stats['approved'], stats['pending'], stats['rejected'],
                      stats['total'] - stats['approved'] - stats['pending'] - stats['rejected']]
        }
        df_approval = pd.DataFrame(approval_data)
        st.bar_chart(df_approval.set_index('Approval'))

    # Timeline view
    st.divider()
    st.markdown("#### 📅 Tasks Timeline (by date)")
    all_tasks_for_timeline = db.get_all_tasks()
    dated_tasks = [t for t in all_tasks_for_timeline if t.get('date')]
    if dated_tasks:
        df_timeline = pd.DataFrame(dated_tasks)
        df_timeline['date'] = pd.to_datetime(df_timeline['date'])
        daily_counts = df_timeline.groupby('date').size().reset_index(name='Tasks')
        daily_counts = daily_counts.set_index('date')
        st.line_chart(daily_counts)

# ===========================
# TAB: IMPORT & SYNC
# ===========================
with tab_import:
    st.markdown("### 📥 Data Import & Sync")

    icol1, icol2 = st.columns(2)

    with icol1:
        st.markdown("#### Import from Excel")
        st.caption("Upload a Marketing Planner Excel file to import tasks")

        uploaded_file = st.file_uploader("Upload Excel file", type=['xlsx', 'xls'])
        if uploaded_file:
            temp_path = f"/tmp/{uploaded_file.name}"
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            if st.button("🔄 Import Data", type="primary"):
                count = db.import_from_excel(temp_path)
                os.remove(temp_path)
                st.success(f"✅ Imported {count} tasks!")
                st.rerun()

        st.divider()
        st.markdown("#### Re-import Original File")
        if os.path.exists(EXCEL_FILE):
            st.caption(f"File: `{os.path.basename(EXCEL_FILE)}`")
            if st.button("🔄 Re-import from original Excel"):
                db.reset_db()
                db.init_db()
                count = db.import_from_excel(EXCEL_FILE)
                st.success(f"✅ Re-imported {count} tasks from original spreadsheet!")
                st.rerun()
        else:
            st.warning("Original Excel file not found in the project folder.")

    with icol2:
        st.markdown("#### ☁️ OneDrive Sync")

        if is_onedrive_configured():
            st.success("OneDrive is configured!")
            if st.button("📤 Backup DB to OneDrive Now"):
                success, msg = backup_db_to_onedrive()
                if success:
                    st.success(msg)
                else:
                    st.error(msg)
        else:
            st.info("Configure OneDrive in the sidebar to enable cloud backup and sync.")
            with st.expander("How to set up OneDrive"):
                st.markdown("""
                1. Register an app at [Azure Portal](https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationsListBlade)
                2. Set Redirect URI to `http://localhost:8501`
                3. Add API permissions: `Files.ReadWrite`, `User.Read`
                4. Create a client secret
                5. Add to `.streamlit/secrets.toml`:
                ```toml
                ONEDRIVE_CLIENT_ID = "your-app-id"
                ONEDRIVE_CLIENT_SECRET = "your-secret"
                ONEDRIVE_REDIRECT_URI = "http://localhost:8501"
                ```
                6. Restart the app and sign in via the sidebar
                """)

        st.divider()
        st.markdown("#### 📊 Database Info")
        st.metric("Total tasks in DB", stats['total'])
        conn = db.get_connection()
        log = conn.execute("SELECT * FROM import_log ORDER BY imported_at DESC LIMIT 5").fetchall()
        conn.close()
        if log:
            st.markdown("**Recent imports:**")
            for entry in log:
                st.text(f"  {entry['filename']} — {entry['row_count']} rows — {entry['imported_at'][:16]}")

        st.divider()
        st.markdown("#### ⚠️ Danger Zone")
        if st.button("🗑️ Reset Database"):
            st.warning("This will delete ALL tasks. Click again to confirm.")
        if st.button("⚠️ CONFIRM: Reset All Data"):
            db.reset_db()
            db.init_db()
            st.success("Database reset. Re-import your data.")
            st.rerun()


# --- Quick Status Update (bottom of sidebar) ---
with st.sidebar:
    st.divider()
    st.markdown("### ⚡ Quick Status Update")
    task_options = [(t['id'], t['content'][:50]) for t in all_tasks[:50]]
    if task_options:
        quick_task = st.selectbox(
            "Select task",
            options=task_options,
            format_func=lambda x: x[1],
            key="quick_task_select"
        )
        new_status = st.selectbox("New status", STATUS_OPTIONS, key="quick_status")
        if st.button("Update Status", use_container_width=True):
            if quick_task:
                db.update_task_status(quick_task[0], new_status)
                st.toast(f"✅ Moved to {new_status}")
                st.rerun()

    st.divider()
    st.markdown("### ➕ Add Platform/Owner")
    new_platform = st.text_input("New platform name", key="new_plat")
    if st.button("Add Platform") and new_platform:
        db.add_platform(new_platform.strip())
        st.toast(f"Added platform: {new_platform}")
        st.rerun()

    new_owner = st.text_input("New owner name", key="new_own")
    if st.button("Add Owner") and new_owner:
        db.add_owner(new_owner.strip())
        st.toast(f"Added owner: {new_owner}")
        st.rerun()
