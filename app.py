"""
CampusConnect v2.0 – ISBM College of Engineering, Pune
Python Flask Full-Stack | Clean UI | Role-Based | QR Attendance | Timetable
"""

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3, os, json, uuid, hashlib
from datetime import datetime, date, timedelta
from functools import wraps

app = Flask(__name__)
app.secret_key = 'isbm-cc-v2-secret-2025'
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024
DB_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'cc.db')
ALLOWED = {'png','jpg','jpeg','gif','webp'}

# ── DB ────────────────────────────────────────────────────────────────────────
def get_db():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    conn = get_db(); c = conn.cursor()
    c.executescript('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        full_name TEXT NOT NULL,
        role TEXT DEFAULT 'student',
        department TEXT,
        year TEXT,
        semester TEXT,
        roll_number TEXT,
        phone TEXT,
        bio TEXT,
        profile_pic TEXT DEFAULT 'default.png',
        is_active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS departments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        code TEXT NOT NULL,
        hod TEXT,
        intake INTEGER DEFAULT 60,
        established INTEGER,
        description TEXT
    );
    CREATE TABLE IF NOT EXISTS timetable (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        department TEXT NOT NULL,
        year TEXT NOT NULL,
        semester TEXT NOT NULL,
        day TEXT NOT NULL,
        period INTEGER NOT NULL,
        subject TEXT NOT NULL,
        teacher_id INTEGER REFERENCES users(id),
        teacher_name TEXT,
        room TEXT,
        time_from TEXT,
        time_to TEXT,
        created_by INTEGER REFERENCES users(id),
        created_at TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS attendance_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        teacher_id INTEGER REFERENCES users(id),
        department TEXT,
        year TEXT,
        subject TEXT,
        room TEXT,
        session_token TEXT UNIQUE NOT NULL,
        qr_data TEXT,
        date TEXT,
        time_from TEXT,
        time_to TEXT,
        is_active INTEGER DEFAULT 1,
        expires_at TEXT,
        total_students INTEGER DEFAULT 0,
        present_count INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS attendance_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER REFERENCES attendance_sessions(id),
        student_id INTEGER REFERENCES users(id),
        student_name TEXT,
        roll_number TEXT,
        department TEXT,
        year TEXT,
        marked_at TEXT DEFAULT (datetime('now')),
        method TEXT DEFAULT 'qr',
        UNIQUE(session_id, student_id)
    );
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        department TEXT DEFAULT 'All',
        event_type TEXT,
        venue TEXT,
        event_date TEXT,
        event_time TEXT,
        reg_deadline TEXT,
        max_participants INTEGER,
        organizer_id INTEGER REFERENCES users(id),
        organizer_name TEXT,
        banner_image TEXT,
        status TEXT DEFAULT 'upcoming',
        tags TEXT,
        whatsapp_notified INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS event_registrations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id INTEGER REFERENCES events(id),
        user_id INTEGER REFERENCES users(id),
        registered_at TEXT DEFAULT (datetime('now')),
        UNIQUE(event_id, user_id)
    );
    CREATE TABLE IF NOT EXISTS memories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id INTEGER REFERENCES events(id),
        uploader_id INTEGER REFERENCES users(id),
        uploader_name TEXT,
        title TEXT,
        description TEXT,
        image_path TEXT NOT NULL,
        album TEXT,
        likes INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS memory_likes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        memory_id INTEGER REFERENCES memories(id),
        user_id INTEGER REFERENCES users(id),
        UNIQUE(memory_id, user_id)
    );
    CREATE TABLE IF NOT EXISTS notices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT,
        category TEXT DEFAULT 'general',
        author_id INTEGER REFERENCES users(id),
        author_name TEXT,
        author_role TEXT,
        department TEXT DEFAULT 'All',
        year TEXT DEFAULT 'All',
        is_important INTEGER DEFAULT 0,
        whatsapp_message TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS achievements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER REFERENCES users(id),
        student_name TEXT,
        title TEXT,
        description TEXT,
        achievement_type TEXT,
        date TEXT,
        certificate_image TEXT,
        department TEXT,
        approved INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now'))
    );
    ''')
    # Seed departments
    c.execute("SELECT COUNT(*) FROM departments")
    if c.fetchone()[0] == 0:
        depts = [
            ('Computer Engineering','CE','Dr. Rajesh Kumar',120,2003,'Core computing, algorithms, software systems'),
            ('Information Technology','IT','Dr. Priya Sharma',60,2005,'Networking, web systems, databases'),
            ('Electronics & Telecommunication','ENTC','Dr. Anil Patil',60,2003,'Circuits, communication, embedded systems'),
            ('Mechanical Engineering','ME','Dr. Suresh Jadhav',60,2003,'Design, manufacturing, thermodynamics'),
            ('Civil Engineering','Civil','Dr. Meena Kulkarni',60,2008,'Structures, surveying, construction'),
            ('AIDS (AI & Data Science)','AIDS','Dr. Neha Desai',60,2021,'Machine learning, data analytics, AI'),
        ]
        c.executemany("INSERT INTO departments (name,code,hod,intake,established,description) VALUES (?,?,?,?,?,?)", depts)
    # Seed admin
    c.execute("SELECT COUNT(*) FROM users WHERE role='admin'")
    if c.fetchone()[0] == 0:
        pw = generate_password_hash('admin@isbm123')
        c.execute("INSERT INTO users (username,email,password,full_name,role,department) VALUES (?,?,?,?,?,?)",
                  ('admin','admin@isbm.edu.in',pw,'Admin ISBM','admin','Administration'))
    # Seed teacher
    c.execute("SELECT COUNT(*) FROM users WHERE role='teacher'")
    if c.fetchone()[0] == 0:
        pw2 = generate_password_hash('teacher@123')
        c.execute("INSERT INTO users (username,email,password,full_name,role,department) VALUES (?,?,?,?,?,?)",
                  ('teacher1','teacher@isbm.edu.in',pw2,'Dr. Rajesh Kumar','teacher','Computer Engineering'))
    # Seed organizer
    c.execute("SELECT COUNT(*) FROM users WHERE role='organizer'")
    if c.fetchone()[0] == 0:
        pw3 = generate_password_hash('organizer@123')
        c.execute("INSERT INTO users (username,email,password,full_name,role,department) VALUES (?,?,?,?,?,?)",
                  ('organizer1','organizer@isbm.edu.in',pw3,'Sneha Patil','organizer','Computer Engineering'))
    # Seed events
    c.execute("SELECT COUNT(*) FROM events")
    if c.fetchone()[0] == 0:
        evs = [
            ('TechFest 2025','Annual technical festival with coding competitions and hackathons.','All','technical','Main Auditorium','2025-03-15','09:00','2025-03-10',500,3,'Sneha Patil',None,'upcoming','coding,hackathon'),
            ('Cultural Night – Rang De','Grand cultural evening with music, dance, drama.','All','cultural','Open Air Theatre','2025-02-28','18:00','2025-02-25',800,3,'Sneha Patil',None,'upcoming','dance,music'),
            ('AI/ML Workshop','Hands-on Machine Learning workshop with Python.','AIDS','workshop','CS Lab 201','2025-02-20','10:00','2025-02-18',50,3,'Sneha Patil',None,'completed','AI,ML,Python'),
        ]
        c.executemany("INSERT INTO events (title,description,department,event_type,venue,event_date,event_time,reg_deadline,max_participants,organizer_id,organizer_name,banner_image,status,tags) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", evs)
    # Seed notices
    c.execute("SELECT COUNT(*) FROM notices")
    if c.fetchone()[0] == 0:
        ns = [
            ('Semester VI Exam Schedule Released','Examination schedule for Sem VI is now available on the portal. Report to exam hall 30 mins early.','academic',2,'Dr. Rajesh Kumar','teacher','All','All',1,'📢 ISBM Notice: Semester VI Exam Schedule Released. Check the portal for details. -ISBM CE Dept'),
            ('TCS Placement Drive – Register Now','TCS conducting placement drive on 10th March 2025. All BE students must register before 5th March.','placement',3,'Sneha Patil','organizer','All','BE',1,'🎯 ISBM Placement: TCS Drive on 10th March! Register at isbm-campusconnect.in by 5th March. All BE students.'),
            ('Library Extended Hours','Library open 7 AM – 10 PM during examination period. Silence to be maintained.','general',2,'Dr. Rajesh Kumar','teacher','All','All',0,'📚 ISBM: Library extended hours (7AM-10PM) during exams. Maintain silence please.'),
        ]
        c.executemany("INSERT INTO notices (title,content,category,author_id,author_name,author_role,department,year,is_important,whatsapp_message) VALUES (?,?,?,?,?,?,?,?,?,?)", ns)
    # Seed timetable
    c.execute("SELECT COUNT(*) FROM timetable")
    if c.fetchone()[0] == 0:
        tt = [
            ('Computer Engineering','SE','3','Monday',1,'Data Structures',2,'Dr. Rajesh Kumar','CS-101','09:00','10:00',2),
            ('Computer Engineering','SE','3','Monday',2,'Discrete Mathematics',2,'Dr. Rajesh Kumar','CS-101','10:00','11:00',2),
            ('Computer Engineering','SE','3','Monday',3,'Database Management',2,'Dr. Rajesh Kumar','CS-102','11:15','12:15',2),
            ('Computer Engineering','SE','3','Tuesday',1,'Operating Systems',2,'Dr. Rajesh Kumar','CS-103','09:00','10:00',2),
            ('Computer Engineering','SE','3','Tuesday',2,'Computer Networks',2,'Dr. Rajesh Kumar','CS-101','10:00','11:00',2),
            ('Computer Engineering','SE','3','Wednesday',1,'Data Structures',2,'Dr. Rajesh Kumar','CS-Lab','11:15','13:15',2),
            ('Computer Engineering','TE','5','Monday',1,'Machine Learning',2,'Dr. Rajesh Kumar','CS-201','09:00','10:00',2),
            ('Computer Engineering','TE','5','Monday',2,'Cloud Computing',2,'Dr. Rajesh Kumar','CS-201','10:00','11:00',2),
        ]
        c.executemany("INSERT INTO timetable (department,year,semester,day,period,subject,teacher_id,teacher_name,room,time_from,time_to,created_by) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", tt)
    conn.commit(); conn.close()

def allowed_file(f):
    return '.' in f and f.rsplit('.',1)[1].lower() in ALLOWED

# ── Auth ──────────────────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def d(*a, **kw):
        if 'user_id' not in session:
            flash('Please login to continue.','warning')
            return redirect(url_for('login'))
        return f(*a, **kw)
    return d

def role_required(*roles):
    def dec(f):
        @wraps(f)
        def d(*a, **kw):
            if 'user_id' not in session: return redirect(url_for('login'))
            if session.get('role') not in roles:
                flash('Access denied.','danger')
                return redirect(url_for('dashboard'))
            return f(*a, **kw)
        return d
    return dec

def get_current_user():
    if 'user_id' in session:
        conn = get_db()
        u = conn.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
        conn.close()
        return u
    return None

@app.context_processor
def inject():
    return dict(current_user=get_current_user(), now=datetime.now())

# ── Public Routes ─────────────────────────────────────────────────────────────
@app.route('/')
def index():
    conn = get_db()
    events = conn.execute("SELECT e.*, (SELECT COUNT(*) FROM event_registrations WHERE event_id=e.id) as rc FROM events e WHERE status='upcoming' ORDER BY event_date LIMIT 6").fetchall()
    notices = conn.execute("SELECT * FROM notices ORDER BY is_important DESC, created_at DESC LIMIT 5").fetchall()
    memories = conn.execute("SELECT * FROM memories ORDER BY created_at DESC LIMIT 8").fetchall()
    stats = {
        'students': conn.execute("SELECT COUNT(*) FROM users WHERE role='student'").fetchone()[0] or 2400,
        'events': conn.execute("SELECT COUNT(*) FROM events").fetchone()[0],
        'departments': conn.execute("SELECT COUNT(*) FROM departments").fetchone()[0],
        'memories': conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0],
    }
    depts = conn.execute("SELECT * FROM departments").fetchall()
    conn.close()
    return render_template('index.html', events=events, notices=notices, memories=memories, stats=stats, depts=depts)

# ── Auth Routes ───────────────────────────────────────────────────────────────
@app.route('/login', methods=['GET','POST'])
def login():
    if 'user_id' in session: return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email = request.form.get('email','').strip()
        pw = request.form.get('password','')
        conn = get_db()
        u = conn.execute("SELECT * FROM users WHERE email=? AND is_active=1", (email,)).fetchone()
        conn.close()
        if u and check_password_hash(u['password'], pw):
            session.update({'user_id':u['id'],'username':u['username'],'role':u['role'],'full_name':u['full_name'],'department':u['department'],'year':u['year']})
            flash(f'Welcome back, {u["full_name"]}! 👋','success')
            return redirect(url_for('dashboard'))
        flash('Invalid email or password.','danger')
    return render_template('auth/login.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if 'user_id' in session: return redirect(url_for('dashboard'))
    conn = get_db()
    depts = conn.execute("SELECT * FROM departments").fetchall()
    conn.close()
    if request.method == 'POST':
        data = {k: request.form.get(k,'').strip() for k in ['full_name','username','email','password','confirm','department','year','semester','roll_number','phone','role']}
        if data['password'] != data['confirm']:
            flash('Passwords do not match.','danger')
            return render_template('auth/register.html', depts=depts)
        if len(data['password']) < 6:
            flash('Password must be 6+ characters.','danger')
            return render_template('auth/register.html', depts=depts)
        # Only allow student role on public register; teacher/organizer/admin via admin
        role = 'student' if data['role'] not in ('student',) else data['role']
        conn = get_db()
        if conn.execute("SELECT id FROM users WHERE email=? OR username=?",(data['email'],data['username'])).fetchone():
            conn.close(); flash('Email or username already exists.','danger')
            return render_template('auth/register.html', depts=depts)
        try:
            conn.execute("INSERT INTO users (username,email,password,full_name,role,department,year,semester,roll_number,phone) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (data['username'],data['email'],generate_password_hash(data['password']),data['full_name'],'student',data['department'],data['year'],data['semester'],data['roll_number'],data['phone']))
            conn.commit(); conn.close()
            flash('Registration successful! Please login.','success')
            return redirect(url_for('login'))
        except: conn.close(); flash('Registration failed.','danger')
    return render_template('auth/register.html', depts=depts)

@app.route('/logout')
def logout():
    session.clear(); flash('Logged out successfully.','info')
    return redirect(url_for('index'))

# ── Dashboard ─────────────────────────────────────────────────────────────────
@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db()
    uid = session['user_id']; role = session['role']
    dept = session.get('department',''); year = session.get('year','')

    # Role-specific data
    if role == 'student':
        my_events = conn.execute("SELECT e.* FROM events e JOIN event_registrations r ON e.id=r.event_id WHERE r.user_id=? ORDER BY e.event_date DESC LIMIT 5", (uid,)).fetchall()
        # Notices visible to this student (dept match or 'All', year match or 'All')
        notices = conn.execute("SELECT * FROM notices WHERE (department='All' OR department=?) AND (year='All' OR year=?) ORDER BY is_important DESC, created_at DESC LIMIT 5", (dept, year)).fetchall()
        # My attendance
        my_att = conn.execute("SELECT COUNT(*) FROM attendance_records WHERE student_id=?", (uid,)).fetchone()[0]
        upcoming = conn.execute("SELECT COUNT(*) FROM events WHERE status='upcoming'").fetchone()[0]
        today_tt = conn.execute("SELECT * FROM timetable WHERE department=? AND year=? AND day=? ORDER BY period", (dept, year, datetime.now().strftime('%A'))).fetchall()
        stats = {'my_events': len(list(my_events)), 'upcoming': upcoming, 'attendance': my_att, 'achievements': conn.execute("SELECT COUNT(*) FROM achievements WHERE student_id=?", (uid,)).fetchone()[0]}
        return render_template('dashboard/student.html', my_events=my_events, notices=notices, today_tt=today_tt, stats=stats)

    elif role == 'teacher':
        # Teacher sees their sessions and student attendance
        sessions = conn.execute("SELECT * FROM attendance_sessions WHERE teacher_id=? ORDER BY created_at DESC LIMIT 10", (uid,)).fetchall()
        my_students = conn.execute("SELECT u.*, (SELECT COUNT(*) FROM attendance_records ar JOIN attendance_sessions s ON ar.session_id=s.id WHERE ar.student_id=u.id AND s.teacher_id=?) as att_count FROM users u WHERE u.role='student' AND u.department=? ORDER BY u.full_name", (uid, dept)).fetchall()
        recent_att = conn.execute("SELECT ar.*, s.subject, s.date FROM attendance_records ar JOIN attendance_sessions s ON ar.session_id=s.id WHERE s.teacher_id=? ORDER BY ar.marked_at DESC LIMIT 20", (uid,)).fetchall()
        stats = {'my_sessions': len(list(sessions)), 'total_students': len(list(my_students)), 'today_sessions': conn.execute("SELECT COUNT(*) FROM attendance_sessions WHERE teacher_id=? AND date=?", (uid, date.today().isoformat())).fetchone()[0]}
        return render_template('dashboard/teacher.html', sessions=sessions, my_students=my_students, recent_att=recent_att, stats=stats)

    elif role == 'organizer':
        my_events = conn.execute("SELECT e.*, (SELECT COUNT(*) FROM event_registrations WHERE event_id=e.id) as rc FROM events e WHERE e.organizer_id=? ORDER BY e.event_date DESC", (uid,)).fetchall()
        upcoming_events = conn.execute("SELECT e.*, (SELECT COUNT(*) FROM event_registrations WHERE event_id=e.id) as rc FROM events e WHERE status='upcoming' ORDER BY event_date LIMIT 6").fetchall()
        recent_memories = conn.execute("SELECT * FROM memories WHERE uploader_id=? ORDER BY created_at DESC LIMIT 6", (uid,)).fetchall()
        stats = {'my_events': len(list(my_events)), 'total_regs': conn.execute("SELECT COUNT(*) FROM event_registrations WHERE event_id IN (SELECT id FROM events WHERE organizer_id=?)", (uid,)).fetchone()[0], 'memories': len(list(recent_memories))}
        return render_template('dashboard/organizer.html', my_events=my_events, upcoming_events=upcoming_events, recent_memories=recent_memories, stats=stats)

    elif role == 'admin':
        stats = {
            'users': conn.execute("SELECT COUNT(*) FROM users").fetchone()[0],
            'students': conn.execute("SELECT COUNT(*) FROM users WHERE role='student'").fetchone()[0],
            'teachers': conn.execute("SELECT COUNT(*) FROM users WHERE role='teacher'").fetchone()[0],
            'events': conn.execute("SELECT COUNT(*) FROM events").fetchone()[0],
            'memories': conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0],
            'pending': conn.execute("SELECT COUNT(*) FROM achievements WHERE approved=0").fetchone()[0],
        }
        recent_users = conn.execute("SELECT * FROM users ORDER BY created_at DESC LIMIT 8").fetchall()
        return render_template('dashboard/admin.html', stats=stats, recent_users=recent_users)

    conn.close()
    return redirect(url_for('index'))

# ── Timetable ─────────────────────────────────────────────────────────────────
@app.route('/timetable')
@login_required
def timetable():
    conn = get_db()
    role = session['role']; uid = session['user_id']
    days = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday']

    if role == 'student':
        dept = session.get('department',''); year = session.get('year','')
        tt = conn.execute("SELECT * FROM timetable WHERE department=? AND year=? ORDER BY day, period", (dept, year)).fetchall()
        depts = None; years = None
    elif role == 'teacher':
        dept = session.get('department','')
        tt = conn.execute("SELECT * FROM timetable WHERE teacher_id=? ORDER BY day, period", (uid,)).fetchall()
        depts = None; years = None
    else:
        dept_f = request.args.get('dept','Computer Engineering')
        year_f = request.args.get('year','SE')
        tt = conn.execute("SELECT * FROM timetable WHERE department=? AND year=? ORDER BY day, period", (dept_f, year_f)).fetchall()
        depts = conn.execute("SELECT * FROM departments").fetchall()
        years = ['FE','SE','TE','BE']
        dept = dept_f; year = year_f

    # Organize by day
    schedule = {d: {} for d in days}
    for row in tt:
        schedule[row['day']][row['period']] = row

    conn.close()
    return render_template('timetable/view.html', schedule=schedule, days=days, dept=dept, year=year,
                           depts=depts, years=years if role in ('admin','organizer') else None)

@app.route('/timetable/manage', methods=['GET','POST'])
@login_required
@role_required('admin','teacher')
def manage_timetable():
    conn = get_db()
    depts = conn.execute("SELECT * FROM departments").fetchall()
    teachers = conn.execute("SELECT * FROM users WHERE role='teacher' ORDER BY full_name").fetchall()

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            conn.execute("INSERT INTO timetable (department,year,semester,day,period,subject,teacher_id,teacher_name,room,time_from,time_to,created_by) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (request.form['department'], request.form['year'], request.form['semester'],
                 request.form['day'], request.form['period'], request.form['subject'],
                 request.form['teacher_id'], request.form['teacher_name'],
                 request.form['room'], request.form['time_from'], request.form['time_to'],
                 session['user_id']))
            conn.commit()
            flash('Timetable entry added!','success')
        elif action == 'delete':
            conn.execute("DELETE FROM timetable WHERE id=?", (request.form['tt_id'],))
            conn.commit()
            flash('Entry deleted.','info')
        conn.close()
        return redirect(url_for('manage_timetable'))

    tt_all = conn.execute("SELECT t.*, u.full_name as teacher FROM timetable t LEFT JOIN users u ON t.teacher_id=u.id ORDER BY t.department, t.year, t.day, t.period").fetchall()
    conn.close()
    return render_template('timetable/manage.html', depts=depts, teachers=teachers, tt_all=tt_all)

# ── QR Attendance ─────────────────────────────────────────────────────────────
@app.route('/attendance')
@login_required
def attendance():
    conn = get_db()
    uid = session['user_id']; role = session['role']

    if role == 'teacher' or role == 'admin':
        sessions_list = conn.execute("""SELECT s.*, 
            (SELECT COUNT(*) FROM attendance_records WHERE session_id=s.id) as present_count
            FROM attendance_sessions s WHERE s.teacher_id=? ORDER BY s.created_at DESC LIMIT 20""", (uid,)).fetchall()
        # Students in teacher's dept
        dept = session.get('department','')
        students = conn.execute("SELECT u.*, (SELECT COUNT(*) FROM attendance_records ar JOIN attendance_sessions s2 ON ar.session_id=s2.id WHERE ar.student_id=u.id AND s2.teacher_id=?) as att_count FROM users u WHERE u.role='student' AND u.department=? ORDER BY u.year, u.roll_number", (uid, dept)).fetchall()
        conn.close()
        return render_template('attendance/teacher.html', sessions=sessions_list, students=students)
    else:
        # Student: view their own attendance only
        dept = session.get('department',''); year = session.get('year','')
        my_records = conn.execute("""SELECT ar.*, s.subject, s.date, s.time_from, s.department
            FROM attendance_records ar JOIN attendance_sessions s ON ar.session_id=s.id
            WHERE ar.student_id=? ORDER BY ar.marked_at DESC""", (uid,)).fetchall()
        total_sessions = conn.execute("SELECT COUNT(*) FROM attendance_sessions WHERE department=? AND year=? AND is_active=0", (dept, year)).fetchone()[0]
        conn.close()
        return render_template('attendance/student.html', my_records=my_records, total_sessions=total_sessions)

@app.route('/attendance/create', methods=['GET','POST'])
@login_required
@role_required('teacher','admin')
def create_attendance_session():
    conn = get_db()
    if request.method == 'POST':
        token = uuid.uuid4().hex[:12].upper()
        att_url = f"/attendance/mark/{token}"
        qr_data = f"ISBM-ATTENDANCE:{token}"  # Frontend will render QR from this
        dept = request.form.get('department', session.get('department',''))
        year = request.form.get('year','')
        expires = (datetime.now() + timedelta(minutes=int(request.form.get('duration', 15)))).isoformat()
        conn.execute("""INSERT INTO attendance_sessions (teacher_id, department, year, subject, room, session_token, qr_data, date, time_from, expires_at)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (session['user_id'], dept, year, request.form['subject'], request.form.get('room',''),
             token, qr_data, date.today().isoformat(), datetime.now().strftime('%H:%M'), expires))
        conn.commit()
        sess_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.close()
        flash(f'Attendance session created! Token: {token}','success')
        return redirect(url_for('attendance_session', session_id=sess_id))
    depts = conn.execute("SELECT * FROM departments").fetchall()
    conn.close()
    return render_template('attendance/create.html', depts=depts)

@app.route('/attendance/session/<int:session_id>')
@login_required
@role_required('teacher','admin')
def attendance_session(session_id):
    conn = get_db()
    sess = conn.execute("SELECT * FROM attendance_sessions WHERE id=?", (session_id,)).fetchone()
    if not sess:
        flash('Session not found.','danger')
        return redirect(url_for('attendance'))
    records = conn.execute("""SELECT ar.*, u.roll_number, u.year FROM attendance_records ar
        JOIN users u ON ar.student_id=u.id WHERE ar.session_id=? ORDER BY ar.marked_at""", (session_id,)).fetchall()
    present_count = len(records)
    total_students = conn.execute("SELECT COUNT(*) FROM users WHERE department=? AND year=? AND role='student'",
                                  (sess['department'], sess['year'])).fetchone()[0]
    conn.close()
    return render_template('attendance/session.html', sess=sess, records=records,
                           present_count=present_count, total_students=total_students)

@app.route('/attendance/mark/<token>', methods=['GET','POST'])
@login_required
def mark_attendance(token):
    conn = get_db()
    sess = conn.execute("SELECT * FROM attendance_sessions WHERE session_token=? AND is_active=1", (token,)).fetchone()
    if not sess:
        conn.close()
        return render_template('attendance/mark_result.html', success=False, msg='Session expired or invalid.')
    # Check expiry
    if sess['expires_at'] and datetime.fromisoformat(sess['expires_at']) < datetime.now():
        conn.execute("UPDATE attendance_sessions SET is_active=0 WHERE id=?", (sess['id'],))
        conn.commit(); conn.close()
        return render_template('attendance/mark_result.html', success=False, msg='QR code has expired. Ask teacher for new one.')
    # Check already marked
    existing = conn.execute("SELECT id FROM attendance_records WHERE session_id=? AND student_id=?", (sess['id'], session['user_id'])).fetchone()
    if existing:
        conn.close()
        return render_template('attendance/mark_result.html', success=True, msg='Attendance already marked for this session!', already=True)
    # Verify student is in correct dept/year
    u = conn.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
    if u['role'] != 'student':
        conn.close()
        return render_template('attendance/mark_result.html', success=False, msg='Only students can mark attendance.')
    conn.execute("INSERT INTO attendance_records (session_id, student_id, student_name, roll_number, department, year) VALUES (?,?,?,?,?,?)",
                 (sess['id'], session['user_id'], u['full_name'], u['roll_number'], u['department'], u['year']))
    conn.commit(); conn.close()
    return render_template('attendance/mark_result.html', success=True, msg=f'✅ Attendance marked for {sess["subject"]}!', subject=sess['subject'])

@app.route('/attendance/session/<int:session_id>/close', methods=['POST'])
@login_required
@role_required('teacher','admin')
def close_session(session_id):
    conn = get_db()
    conn.execute("UPDATE attendance_sessions SET is_active=0 WHERE id=? AND teacher_id=?", (session_id, session['user_id']))
    conn.commit(); conn.close()
    flash('Session closed.','info')
    return redirect(url_for('attendance_session', session_id=session_id))

# ── Notices ───────────────────────────────────────────────────────────────────
@app.route('/notices')
@login_required
def notices():
    conn = get_db()
    role = session['role']; uid = session['user_id']
    dept = session.get('department',''); year = session.get('year','')
    cat = request.args.get('cat','')

    if role == 'student':
        # Students only see notices addressed to them
        q = "SELECT * FROM notices WHERE (department='All' OR department=?) AND (year='All' OR year=?)"
        params = [dept, year]
        if cat: q += " AND category=?"; params.append(cat)
        q += " ORDER BY is_important DESC, created_at DESC"
        ns = conn.execute(q, params).fetchall()
    else:
        # Teachers/organizers/admin see all notices they can manage
        q = "SELECT * FROM notices WHERE 1=1"
        params = []
        if cat: q += " AND category=?"; params.append(cat)
        q += " ORDER BY is_important DESC, created_at DESC"
        ns = conn.execute(q, params).fetchall()

    conn.close()
    return render_template('notices.html', notices=ns, cat_filter=cat)

@app.route('/notices/create', methods=['GET','POST'])
@login_required
@role_required('teacher','organizer','admin')
def create_notice():
    conn = get_db()
    depts = conn.execute("SELECT * FROM departments").fetchall()
    conn.close()
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        dept = request.form.get('department','All')
        year = request.form.get('year','All')
        cat = request.form.get('category','general')
        important = 1 if request.form.get('is_important') else 0
        # Auto-generate WhatsApp message
        wa_msg = f"📢 *ISBM CampusConnect*\n*{title}*\n\n{content[:200]}\n\n_From: {session['full_name']} | {session['role'].title()}_\n_Dept: {dept} | Year: {year}_"
        conn = get_db()
        conn.execute("INSERT INTO notices (title,content,category,author_id,author_name,author_role,department,year,is_important,whatsapp_message) VALUES (?,?,?,?,?,?,?,?,?,?)",
                     (title, content, cat, session['user_id'], session['full_name'], session['role'], dept, year, important, wa_msg))
        conn.commit(); conn.close()
        flash('Notice posted! WhatsApp message generated.','success')
        return redirect(url_for('notices'))
    return render_template('create_notice.html', depts=depts)

# ── Events ────────────────────────────────────────────────────────────────────
@app.route('/events')
def events():
    conn = get_db()
    dept_f = request.args.get('dept',''); type_f = request.args.get('type',''); status_f = request.args.get('status',''); q = request.args.get('q','')
    query = "SELECT e.*, (SELECT COUNT(*) FROM event_registrations WHERE event_id=e.id) as rc FROM events e WHERE 1=1"
    params = []
    if dept_f: query += " AND (e.department=? OR e.department='All')"; params.append(dept_f)
    if type_f: query += " AND e.event_type=?"; params.append(type_f)
    if status_f: query += " AND e.status=?"; params.append(status_f)
    if q: query += " AND (e.title LIKE ? OR e.description LIKE ?)"; params += [f'%{q}%',f'%{q}%']
    query += " ORDER BY e.event_date DESC"
    all_events = conn.execute(query, params).fetchall()
    depts = conn.execute("SELECT * FROM departments").fetchall()
    conn.close()
    return render_template('events/list.html', events=all_events, depts=depts, dept_filter=dept_f, type_filter=type_f, status_filter=status_f, search=q)

@app.route('/events/<int:eid>')
def event_detail(eid):
    conn = get_db()
    ev = conn.execute("SELECT * FROM events WHERE id=?", (eid,)).fetchone()
    if not ev: flash('Event not found.','danger'); return redirect(url_for('events'))
    regs = conn.execute("SELECT u.full_name, u.department, u.year, r.registered_at FROM event_registrations r JOIN users u ON r.user_id=u.id WHERE r.event_id=? LIMIT 30", (eid,)).fetchall()
    rc = conn.execute("SELECT COUNT(*) FROM event_registrations WHERE event_id=?", (eid,)).fetchone()[0]
    is_reg = False
    if 'user_id' in session:
        is_reg = conn.execute("SELECT id FROM event_registrations WHERE event_id=? AND user_id=?", (eid, session['user_id'])).fetchone() is not None
    mems = conn.execute("SELECT * FROM memories WHERE event_id=? ORDER BY created_at DESC", (eid,)).fetchall()
    conn.close()
    return render_template('events/detail.html', ev=ev, regs=regs, rc=rc, is_reg=is_reg, mems=mems)

@app.route('/events/<int:eid>/register', methods=['POST'])
@login_required
def register_event(eid):
    conn = get_db()
    ev = conn.execute("SELECT * FROM events WHERE id=?", (eid,)).fetchone()
    if not ev: conn.close(); return redirect(url_for('events'))
    if conn.execute("SELECT id FROM event_registrations WHERE event_id=? AND user_id=?", (eid, session['user_id'])).fetchone():
        conn.close(); flash('Already registered!','info'); return redirect(url_for('event_detail', eid=eid))
    rc = conn.execute("SELECT COUNT(*) FROM event_registrations WHERE event_id=?", (eid,)).fetchone()[0]
    if ev['max_participants'] and rc >= ev['max_participants']:
        conn.close(); flash('Event is full!','danger'); return redirect(url_for('event_detail', eid=eid))
    conn.execute("INSERT INTO event_registrations (event_id, user_id) VALUES (?,?)", (eid, session['user_id']))
    conn.commit(); conn.close()
    flash('Registered successfully! 🎉','success')
    return redirect(url_for('event_detail', eid=eid))

@app.route('/events/<int:eid>/unregister', methods=['POST'])
@login_required
def unregister_event(eid):
    conn = get_db()
    conn.execute("DELETE FROM event_registrations WHERE event_id=? AND user_id=?", (eid, session['user_id']))
    conn.commit(); conn.close()
    flash('Unregistered.','info')
    return redirect(url_for('event_detail', eid=eid))

@app.route('/events/create', methods=['GET','POST'])
@login_required
@role_required('organizer','admin')
def create_event():
    conn = get_db()
    depts = conn.execute("SELECT * FROM departments").fetchall()
    conn.close()
    if request.method == 'POST':
        banner = request.files.get('banner')
        bpath = None
        if banner and allowed_file(banner.filename):
            fname = f"ev_{uuid.uuid4().hex}_{secure_filename(banner.filename)}"
            banner.save(os.path.join(UPLOAD_FOLDER, 'events', fname)); bpath = fname
        conn = get_db()
        conn.execute("INSERT INTO events (title,description,department,event_type,venue,event_date,event_time,reg_deadline,max_participants,organizer_id,organizer_name,banner_image,tags) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (request.form['title'], request.form['description'], request.form['department'],
             request.form['event_type'], request.form['venue'], request.form['event_date'],
             request.form.get('event_time',''), request.form.get('reg_deadline'),
             request.form.get('max_participants') or None,
             session['user_id'], session['full_name'], bpath, request.form.get('tags','')))
        conn.commit(); conn.close()
        flash('Event created!','success')
        return redirect(url_for('events'))
    return render_template('events/create.html', depts=depts)

# ── Memories ──────────────────────────────────────────────────────────────────
@app.route('/memories')
def memories():
    conn = get_db()
    ef = request.args.get('event',''); af = request.args.get('album','')
    q = "SELECT m.*, e.title as event_title FROM memories m LEFT JOIN events e ON m.event_id=e.id WHERE 1=1"
    params = []
    if ef: q += " AND m.event_id=?"; params.append(ef)
    if af: q += " AND m.album=?"; params.append(af)
    q += " ORDER BY m.created_at DESC"
    mems = conn.execute(q, params).fetchall()
    evs = conn.execute("SELECT id, title FROM events ORDER BY event_date DESC").fetchall()
    albums = conn.execute("SELECT DISTINCT album FROM memories WHERE album IS NOT NULL").fetchall()
    liked = set()
    if 'user_id' in session:
        liked = {r['memory_id'] for r in conn.execute("SELECT memory_id FROM memory_likes WHERE user_id=?", (session['user_id'],)).fetchall()}
    conn.close()
    return render_template('memories/gallery.html', mems=mems, evs=evs, albums=albums, ef=ef, af=af, liked=liked)

@app.route('/memories/upload', methods=['GET','POST'])
@login_required
@role_required('organizer','admin')
def upload_memory():
    conn = get_db(); evs = conn.execute("SELECT id, title FROM events ORDER BY event_date DESC").fetchall(); conn.close()
    if request.method == 'POST':
        files = request.files.getlist('photos'); cnt = 0
        for f in files:
            if f and allowed_file(f.filename):
                fname = f"mem_{uuid.uuid4().hex}_{secure_filename(f.filename)}"
                f.save(os.path.join(UPLOAD_FOLDER, 'memories', fname))
                conn = get_db()
                conn.execute("INSERT INTO memories (event_id,uploader_id,uploader_name,title,description,image_path,album) VALUES (?,?,?,?,?,?,?)",
                    (request.form.get('event_id') or None, session['user_id'], session['full_name'],
                     request.form.get('title',''), request.form.get('description',''), fname, request.form.get('album','')))
                conn.commit(); conn.close(); cnt += 1
        flash(f'{cnt} photo(s) uploaded!','success')
        return redirect(url_for('memories'))
    return render_template('memories/upload.html', evs=evs)

@app.route('/memories/<int:mid>/like', methods=['POST'])
@login_required
def like_memory(mid):
    conn = get_db()
    ex = conn.execute("SELECT id FROM memory_likes WHERE memory_id=? AND user_id=?", (mid, session['user_id'])).fetchone()
    if ex:
        conn.execute("DELETE FROM memory_likes WHERE memory_id=? AND user_id=?", (mid, session['user_id']))
        conn.execute("UPDATE memories SET likes=likes-1 WHERE id=?", (mid,)); liked = False
    else:
        conn.execute("INSERT INTO memory_likes (memory_id,user_id) VALUES (?,?)", (mid, session['user_id']))
        conn.execute("UPDATE memories SET likes=likes+1 WHERE id=?", (mid,)); liked = True
    conn.commit()
    likes = conn.execute("SELECT likes FROM memories WHERE id=?", (mid,)).fetchone()[0]
    conn.close()
    return jsonify({'liked': liked, 'likes': likes})

@app.route('/memories/<int:mid>/download')
def download_memory(mid):
    conn = get_db(); m = conn.execute("SELECT * FROM memories WHERE id=?", (mid,)).fetchone(); conn.close()
    if not m: flash('Not found.','danger'); return redirect(url_for('memories'))
    return send_from_directory(os.path.join(UPLOAD_FOLDER, 'memories'), m['image_path'], as_attachment=True)

# ── Profile ───────────────────────────────────────────────────────────────────
@app.route('/profile')
@login_required
def profile():
    conn = get_db()
    u = conn.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
    my_events = conn.execute("SELECT e.* FROM events e JOIN event_registrations r ON e.id=r.event_id WHERE r.user_id=?", (session['user_id'],)).fetchall()
    my_ach = conn.execute("SELECT * FROM achievements WHERE student_id=? ORDER BY date DESC", (session['user_id'],)).fetchall()
    conn.close()
    return render_template('profile.html', u=u, my_events=my_events, my_ach=my_ach)

@app.route('/profile/edit', methods=['GET','POST'])
@login_required
def edit_profile():
    conn = get_db()
    u = conn.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
    depts = conn.execute("SELECT * FROM departments").fetchall()
    conn.close()
    if request.method == 'POST':
        pp = request.files.get('profile_pic'); pname = u['profile_pic']
        if pp and allowed_file(pp.filename):
            pname = f"pp_{session['user_id']}_{secure_filename(pp.filename)}"
            pp.save(os.path.join(UPLOAD_FOLDER, 'profiles', pname))
        conn = get_db()
        conn.execute("UPDATE users SET full_name=?,phone=?,bio=?,department=?,year=?,profile_pic=? WHERE id=?",
                     (request.form['full_name'], request.form.get('phone',''), request.form.get('bio',''),
                      request.form.get('department',''), request.form.get('year',''), pname, session['user_id']))
        conn.commit(); conn.close()
        session['full_name'] = request.form['full_name']
        flash('Profile updated!','success')
        return redirect(url_for('profile'))
    return render_template('edit_profile.html', u=u, depts=depts)

# ── Admin ─────────────────────────────────────────────────────────────────────
@app.route('/admin/users')
@login_required
@role_required('admin')
def admin_users():
    conn = get_db()
    users = conn.execute("SELECT * FROM users ORDER BY role, full_name").fetchall()
    conn.close()
    return render_template('admin/users.html', users=users)

@app.route('/admin/users/<int:uid>/action', methods=['POST'])
@login_required
@role_required('admin')
def admin_user_action(uid):
    action = request.form.get('action')
    conn = get_db()
    if action == 'toggle':
        u = conn.execute("SELECT is_active FROM users WHERE id=?", (uid,)).fetchone()
        if u: conn.execute("UPDATE users SET is_active=? WHERE id=?", (0 if u['is_active'] else 1, uid))
    elif action == 'role':
        conn.execute("UPDATE users SET role=? WHERE id=?", (request.form['role'], uid))
    conn.commit(); conn.close()
    flash('User updated.','success')
    return redirect(url_for('admin_users'))

@app.route('/admin/add-user', methods=['GET','POST'])
@login_required
@role_required('admin')
def admin_add_user():
    conn = get_db(); depts = conn.execute("SELECT * FROM departments").fetchall(); conn.close()
    if request.method == 'POST':
        conn = get_db()
        conn.execute("INSERT INTO users (username,email,password,full_name,role,department,year,roll_number,phone) VALUES (?,?,?,?,?,?,?,?,?)",
            (request.form['username'], request.form['email'],
             generate_password_hash(request.form['password']),
             request.form['full_name'], request.form['role'],
             request.form.get('department',''), request.form.get('year',''),
             request.form.get('roll_number',''), request.form.get('phone','')))
        conn.commit(); conn.close()
        flash(f'{request.form["role"].title()} account created!','success')
        return redirect(url_for('admin_users'))
    return render_template('admin/add_user.html', depts=depts)

# ── API ───────────────────────────────────────────────────────────────────────
@app.route('/api/stats')
def api_stats():
    conn = get_db()
    data = {k: conn.execute(q).fetchone()[0] for k,q in [
        ('students',"SELECT COUNT(*) FROM users WHERE role='student'"),
        ('events',"SELECT COUNT(*) FROM events"),
        ('memories',"SELECT COUNT(*) FROM memories"),
        ('departments',"SELECT COUNT(*) FROM departments"),
    ]}
    conn.close()
    return jsonify(data)

@app.route('/api/attendance/live/<token>')
def api_attendance_live(token):
    conn = get_db()
    sess = conn.execute("SELECT * FROM attendance_sessions WHERE session_token=?", (token,)).fetchone()
    if not sess: conn.close(); return jsonify({'error':'not found'}), 404
    records = conn.execute("SELECT ar.student_name, ar.marked_at FROM attendance_records ar WHERE ar.session_id=? ORDER BY ar.marked_at DESC LIMIT 5", (sess['id'],)).fetchall()
    count = conn.execute("SELECT COUNT(*) FROM attendance_records WHERE session_id=?", (sess['id'],)).fetchone()[0]
    conn.close()
    expires = sess['expires_at']
    return jsonify({'count': count, 'is_active': bool(sess['is_active']), 'expires_at': expires, 'recent': [dict(r) for r in records]})

@app.route('/achievements', methods=['GET'])
def achievements():
    conn = get_db()
    df = request.args.get('dept','')
    q = "SELECT * FROM achievements WHERE approved=1"
    params = []
    if df: q += " AND department=?"; params.append(df)
    q += " ORDER BY date DESC"
    achs = conn.execute(q, params).fetchall()
    depts = conn.execute("SELECT * FROM departments").fetchall()
    conn.close()
    return render_template('achievements.html', achs=achs, depts=depts, dept_filter=df)

@app.route('/achievements/add', methods=['GET','POST'])
@login_required
def add_achievement():
    if request.method == 'POST':
        cert = request.files.get('certificate'); cp = None
        if cert and allowed_file(cert.filename):
            fn = f"cert_{uuid.uuid4().hex}_{secure_filename(cert.filename)}"
            cert.save(os.path.join(UPLOAD_FOLDER, 'events', fn)); cp = fn
        conn = get_db()
        conn.execute("INSERT INTO achievements (student_id,student_name,title,description,achievement_type,date,certificate_image,department) VALUES (?,?,?,?,?,?,?,?)",
            (session['user_id'], session['full_name'], request.form['title'],
             request.form.get('description',''), request.form['achievement_type'],
             request.form.get('date',''), cp, request.form.get('department', session.get('department',''))))
        conn.commit(); conn.close()
        flash('Achievement submitted for approval!','success')
        return redirect(url_for('profile'))
    return render_template('add_achievement.html')

@app.route('/departments')
def departments():
    conn = get_db()
    depts = conn.execute("SELECT * FROM departments").fetchall()
    stats = {}
    for d in depts:
        stats[d['id']] = {
            'students': conn.execute("SELECT COUNT(*) FROM users WHERE department=? AND role='student'", (d['name'],)).fetchone()[0],
            'events': conn.execute("SELECT COUNT(*) FROM events WHERE department=? OR department='All'", (d['name'],)).fetchone()[0],
        }
    conn.close()
    return render_template('departments.html', depts=depts, stats=stats)

if __name__ == '__main__':
    for d in ['events','memories','profiles','qr']:
        os.makedirs(os.path.join(UPLOAD_FOLDER, d), exist_ok=True)
    os.makedirs('instance', exist_ok=True)
    init_db()
    print("\n🎓 CampusConnect v2.0 – ISBM College of Engineering, Pune")
    print("━"*55)
    print("🌐  http://localhost:5000")
    print("━"*55)
    print("👤  Admin:     admin@isbm.edu.in     / admin@isbm123")
    print("👩‍🏫  Teacher:   teacher@isbm.edu.in  / teacher@123")
    print("🎪  Organizer: organizer@isbm.edu.in / organizer@123")
    print("━"*55)
    app.run(debug=True, host='0.0.0.0', port=5000)
