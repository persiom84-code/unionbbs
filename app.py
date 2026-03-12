"""
UnionBBS - Flask 메인 애플리케이션
PostgreSQL (운영) 전용
"""
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date, timedelta
from functools import wraps
import bcrypt
import os
import cloudinary
import cloudinary.uploader

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-prod')

# ── DB 설정 ──────────────────────────────────────────────
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set!")

if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql+psycopg2://', 1)
elif DATABASE_URL.startswith('postgresql://'):
    DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+psycopg2://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'pool_pre_ping': True}

db = SQLAlchemy(app, session_options={'expire_on_commit': False})

# Cloudinary 초기화
cloudinary.config(
    cloud_name  = os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key     = os.environ.get('CLOUDINARY_API_KEY'),
    api_secret  = os.environ.get('CLOUDINARY_API_SECRET')
)

# ══════════════════════════════════════════════════════════
# Models
# ══════════════════════════════════════════════════════════

class User(db.Model):
    __tablename__ = 'TB_USER'
    user_seq      = db.Column(db.Integer, primary_key=True, autoincrement=True)
    emp_no        = db.Column(db.String(20), nullable=False, unique=True)
    emp_nm        = db.Column(db.String(100), nullable=False)
    gender        = db.Column(db.String(1), nullable=False)
    birth_dt      = db.Column(db.Date)
    phone_no      = db.Column(db.String(20))
    email         = db.Column(db.String(100), unique=True)
    dept_cd       = db.Column(db.String(20))
    union_dept_cd = db.Column(db.String(20))
    emp_type_cd   = db.Column(db.String(10))
    rank_cd       = db.Column(db.String(10))
    position_cd   = db.Column(db.String(10))
    user_level    = db.Column(db.Integer, default=4)
    term_start    = db.Column(db.Date)
    term_end      = db.Column(db.Date)
    pwd_hash      = db.Column(db.String(256), nullable=False)
    pwd_chg_dt    = db.Column(db.Date)
    pwd_init_yn   = db.Column(db.String(1), default='Y')
    pwd_fail_cnt  = db.Column(db.Integer, default=0)
    acct_lock_yn  = db.Column(db.String(1), default='N')
    use_yn        = db.Column(db.String(1), default='Y')
    reg_dt        = db.Column(db.DateTime, default=datetime.now)
    mod_dt        = db.Column(db.DateTime, onupdate=datetime.now)

class CompDept(db.Model):
    __tablename__ = 'TB_COMP_DEPT'
    dept_seq       = db.Column(db.Integer, primary_key=True, autoincrement=True)
    dept_cd        = db.Column(db.String(20), nullable=False, unique=True)
    dept_nm        = db.Column(db.String(100), nullable=False)
    parent_dept_cd = db.Column(db.String(20))
    sort_order     = db.Column(db.Integer, default=0)
    use_yn         = db.Column(db.String(1), default='Y')

class UnionDept(db.Model):
    __tablename__ = 'TB_UNION_DEPT'
    union_dept_seq = db.Column(db.Integer, primary_key=True, autoincrement=True)
    union_dept_cd  = db.Column(db.String(20), nullable=False, unique=True)
    union_dept_nm  = db.Column(db.String(100), nullable=False)
    sort_order     = db.Column(db.Integer, default=0)
    use_yn         = db.Column(db.String(1), default='Y')

class Code(db.Model):
    __tablename__ = 'TB_CODE'
    code_seq   = db.Column(db.Integer, primary_key=True, autoincrement=True)
    code_grp   = db.Column(db.String(20), nullable=False)
    code_cd    = db.Column(db.String(20), nullable=False, unique=True)
    code_nm    = db.Column(db.String(100), nullable=False)
    sort_order = db.Column(db.Integer, default=0)
    use_yn     = db.Column(db.String(1), default='Y')

class Notice(db.Model):
    __tablename__ = 'TB_NOTICE'
    notice_seq  = db.Column(db.Integer, primary_key=True, autoincrement=True)
    notice_type = db.Column(db.String(10), nullable=False)
    title       = db.Column(db.String(200), nullable=False)
    content     = db.Column(db.Text, nullable=False)
    is_push     = db.Column(db.String(1), default='N')
    is_top      = db.Column(db.String(1), default='N')
    view_cnt    = db.Column(db.Integer, default=0)
    use_yn      = db.Column(db.String(1), default='Y')
    reg_dt      = db.Column(db.DateTime, default=datetime.now)
    reg_user    = db.Column(db.String(20))
    mod_dt        = db.Column(db.DateTime)
    mod_user      = db.Column(db.String(20))
    allow_comment = db.Column(db.String(1), default='N')
    file_url      = db.Column(db.String(500))
    file_name     = db.Column(db.String(200))

class NoticeComment(db.Model):
    __tablename__ = 'TB_NOTICE_COMMENT'
    comment_seq = db.Column(db.Integer, primary_key=True, autoincrement=True)
    notice_seq  = db.Column(db.Integer, db.ForeignKey('TB_NOTICE.notice_seq'), nullable=False)
    content     = db.Column(db.Text, nullable=False)
    emp_no      = db.Column(db.String(20), nullable=False)
    emp_nm      = db.Column(db.String(100))
    use_yn      = db.Column(db.String(1), default='Y')
    reg_dt      = db.Column(db.DateTime, default=datetime.now)

class Schedule(db.Model):
    __tablename__ = 'TB_SCHEDULE'
    schedule_seq  = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title         = db.Column(db.String(200), nullable=False)
    content       = db.Column(db.Text)
    start_dt      = db.Column(db.DateTime, nullable=False)
    end_dt        = db.Column(db.DateTime, nullable=False)
    location      = db.Column(db.String(200))
    schedule_type = db.Column(db.String(10))
    dept_cd       = db.Column(db.String(20))
    use_yn        = db.Column(db.String(1), default='Y')
    reg_user      = db.Column(db.String(20))

class Vote(db.Model):
    __tablename__ = 'TB_VOTE'
    vote_seq    = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title       = db.Column(db.String(200), nullable=False)
    content     = db.Column(db.Text)
    start_dt    = db.Column(db.DateTime, nullable=False)
    end_dt      = db.Column(db.DateTime, nullable=False)
    vote_status = db.Column(db.String(10), default='READY')
    total_cnt   = db.Column(db.Integer, default=0)
    vote_cnt    = db.Column(db.Integer, default=0)
    use_yn      = db.Column(db.String(1), default='Y')
    reg_user    = db.Column(db.String(20))
    reg_dt      = db.Column(db.DateTime, default=datetime.now)

class VoteItem(db.Model):
    __tablename__ = 'TB_VOTE_ITEM'
    item_seq   = db.Column(db.Integer, primary_key=True, autoincrement=True)
    vote_seq   = db.Column(db.Integer, db.ForeignKey('TB_VOTE.vote_seq'), nullable=False)
    item_nm    = db.Column(db.String(200), nullable=False)
    item_cnt   = db.Column(db.Integer, default=0)
    sort_order = db.Column(db.Integer, default=0)

class VoteHistory(db.Model):
    __tablename__ = 'TB_VOTE_HISTORY'
    history_seq = db.Column(db.Integer, primary_key=True, autoincrement=True)
    vote_seq    = db.Column(db.Integer, db.ForeignKey('TB_VOTE.vote_seq'), nullable=False)
    item_seq    = db.Column(db.Integer, db.ForeignKey('TB_VOTE_ITEM.item_seq'), nullable=False)
    emp_no      = db.Column(db.String(20), nullable=False)
    vote_dt     = db.Column(db.DateTime, default=datetime.now)

class Suggestion(db.Model):
    __tablename__ = 'TB_SUGGESTION'
    suggest_seq   = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title         = db.Column(db.String(200), nullable=False)
    content       = db.Column(db.Text, nullable=False)
    is_secret     = db.Column(db.String(1), default='N')
    status        = db.Column(db.String(10), default='WAIT')
    emp_no        = db.Column(db.String(20))
    reply_content = db.Column(db.Text)
    reply_emp_no  = db.Column(db.String(20))
    reply_dt      = db.Column(db.DateTime)
    use_yn        = db.Column(db.String(1), default='Y')
    reg_dt        = db.Column(db.DateTime, default=datetime.now)

class Board(db.Model):
    __tablename__ = 'TB_BOARD'
    board_seq     = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title         = db.Column(db.String(200), nullable=False)
    content       = db.Column(db.Text, nullable=False)
    view_cnt      = db.Column(db.Integer, default=0)
    like_cnt      = db.Column(db.Integer, default=0)
    emp_no        = db.Column(db.String(20), nullable=False)
    emp_nm        = db.Column(db.String(100))
    dept_cd       = db.Column(db.String(20))
    union_dept_cd = db.Column(db.String(20))
    use_yn        = db.Column(db.String(1), default='Y')
    reg_dt        = db.Column(db.DateTime, default=datetime.now)
    mod_dt        = db.Column(db.DateTime)

class BoardComment(db.Model):
    __tablename__ = 'TB_BOARD_COMMENT'
    comment_seq = db.Column(db.Integer, primary_key=True, autoincrement=True)
    board_seq   = db.Column(db.Integer, db.ForeignKey('TB_BOARD.board_seq'), nullable=False)
    content     = db.Column(db.Text, nullable=False)
    emp_no      = db.Column(db.String(20), nullable=False)
    emp_nm      = db.Column(db.String(100))
    use_yn      = db.Column(db.String(1), default='Y')
    reg_dt      = db.Column(db.DateTime, default=datetime.now)

class Condo(db.Model):
    __tablename__ = 'TB_CONDO'
    condo_seq   = db.Column(db.Integer, primary_key=True, autoincrement=True)
    condo_nm    = db.Column(db.String(100), nullable=False)
    region_cd   = db.Column(db.String(10))
    brand_cd    = db.Column(db.String(10))
    location    = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    total_room  = db.Column(db.Integer, default=0)
    use_yn      = db.Column(db.String(1), default='Y')
    rooms       = db.relationship('CondoRoom', backref='condo', lazy=True)

class CondoRoom(db.Model):
    __tablename__ = 'TB_CONDO_ROOM'
    room_seq    = db.Column(db.Integer, primary_key=True, autoincrement=True)
    condo_seq   = db.Column(db.Integer, db.ForeignKey('TB_CONDO.condo_seq'), nullable=False)
    room_type   = db.Column(db.String(50), nullable=False)
    capacity    = db.Column(db.Integer, default=4)
    description = db.Column(db.Text)
    amenities   = db.Column(db.String(500))
    total_cnt   = db.Column(db.Integer, default=1)
    avail_cnt   = db.Column(db.Integer, default=1)
    use_yn      = db.Column(db.String(1), default='Y')

class CondoReserve(db.Model):
    __tablename__ = 'TB_CONDO_RESERVE'
    reserve_seq = db.Column(db.Integer, primary_key=True, autoincrement=True)
    condo_seq   = db.Column(db.Integer, db.ForeignKey('TB_CONDO.condo_seq'), nullable=False)
    room_seq    = db.Column(db.Integer, db.ForeignKey('TB_CONDO_ROOM.room_seq'))
    emp_no      = db.Column(db.String(20))
    guest_seq   = db.Column(db.Integer)
    check_in    = db.Column(db.Date, nullable=False)
    check_out   = db.Column(db.Date, nullable=False)
    status      = db.Column(db.String(10), default='APPLY')
    cancel_dt   = db.Column(db.DateTime)
    use_yn      = db.Column(db.String(1), default='Y')
    reg_dt      = db.Column(db.DateTime, default=datetime.now)

class GuestUser(db.Model):
    __tablename__ = 'TB_GUEST_USER'
    guest_seq = db.Column(db.Integer, primary_key=True, autoincrement=True)
    guest_nm  = db.Column(db.String(100), nullable=False)
    phone_no  = db.Column(db.String(20), nullable=False)
    email     = db.Column(db.String(100), nullable=False, unique=True)
    pwd_hash  = db.Column(db.String(256), nullable=False)
    relation  = db.Column(db.String(50))
    use_yn    = db.Column(db.String(1), default='Y')
    reg_dt    = db.Column(db.DateTime, default=datetime.now)

class Book(db.Model):
    __tablename__ = 'TB_BOOK'
    book_seq   = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title      = db.Column(db.String(200), nullable=False)
    author     = db.Column(db.String(100))
    publisher  = db.Column(db.String(100))
    isbn       = db.Column(db.String(20), unique=True)
    total_cnt  = db.Column(db.Integer, default=1)
    avail_cnt  = db.Column(db.Integer, default=1)
    is_new     = db.Column(db.String(1), default='N')
    use_yn     = db.Column(db.String(1), default='Y')
    reg_dt     = db.Column(db.DateTime, default=datetime.now)

class BookRental(db.Model):
    __tablename__ = 'TB_BOOK_RENTAL'
    rental_seq = db.Column(db.Integer, primary_key=True, autoincrement=True)
    book_seq   = db.Column(db.Integer, db.ForeignKey('TB_BOOK.book_seq'), nullable=False)
    emp_no     = db.Column(db.String(20), nullable=False)
    rental_dt  = db.Column(db.Date, default=date.today)
    due_dt     = db.Column(db.Date, nullable=False)
    return_dt  = db.Column(db.Date)
    status     = db.Column(db.String(10), default='RENTAL')
    reg_dt     = db.Column(db.DateTime, default=datetime.now)

class BookRequest(db.Model):
    __tablename__ = 'TB_BOOK_REQUEST'
    request_seq = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title       = db.Column(db.String(200), nullable=False)
    author      = db.Column(db.String(100))
    publisher   = db.Column(db.String(100))
    reason      = db.Column(db.Text)
    status      = db.Column(db.String(10), default='WAIT')
    emp_no      = db.Column(db.String(20), nullable=False)
    use_yn      = db.Column(db.String(1), default='Y')
    reg_dt      = db.Column(db.DateTime, default=datetime.now)

# ══════════════════════════════════════════════════════════
# Auth Helpers
# ══════════════════════════════════════════════════════════

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'emp_no' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def level_required(max_level):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if 'emp_no' not in session:
                return redirect(url_for('login'))
            if session.get('user_level', 99) > max_level:
                flash('접근 권한이 없습니다.')
                return redirect(url_for('main'))
            return f(*args, **kwargs)
        return wrapper
    return decorator

def get_current_user():
    if 'emp_no' not in session:
        return None
    return User.query.filter_by(emp_no=session['emp_no'], use_yn='Y').first()

# ══════════════════════════════════════════════════════════
# Routes - Auth
# ══════════════════════════════════════════════════════════

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        emp_no   = request.form.get('emp_no', '').strip()
        password = request.form.get('password', '')

        user = User.query.filter_by(emp_no=emp_no, use_yn='Y').first()

        if not user:
            flash('사번 또는 비밀번호가 올바르지 않습니다.')
            return render_template('login.html')

        if user.acct_lock_yn == 'Y':
            flash('계정이 잠겨 있습니다. 관리자에게 문의하세요.')
            return render_template('login.html')

        try:
            pw_match = bcrypt.checkpw(password.encode(), user.pwd_hash.encode())
        except Exception:
            pw_match = (password == emp_no)

        if pw_match:
            user.pwd_fail_cnt = 0
            db.session.commit()
            session['emp_no']     = user.emp_no
            session['emp_nm']     = user.emp_nm
            session['user_level'] = user.user_level
            session['user_seq']   = user.user_seq

            if user.pwd_init_yn == 'Y':
                session['force_pwd_change'] = True
                flash('초기 비밀번호를 반드시 변경해야 합니다.', 'warning')
                return redirect(url_for('force_pwd_change'))

            if user.pwd_chg_dt:
                days_since = (date.today() - user.pwd_chg_dt).days
                if days_since >= 90:
                    session['pwd_expired'] = True
                    flash(f'비밀번호 변경 후 {days_since}일이 경과했습니다. 변경을 권장합니다.', 'info')

            return redirect(url_for('main'))
        else:
            user.pwd_fail_cnt = (user.pwd_fail_cnt or 0) + 1
            if user.pwd_fail_cnt >= 5:
                user.acct_lock_yn = 'Y'
                flash('로그인 5회 실패로 계정이 잠겼습니다. 관리자에게 문의하세요.')
            else:
                flash(f'비밀번호가 올바르지 않습니다. ({user.pwd_fail_cnt}/5)')
            db.session.commit()

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ══════════════════════════════════════════════════════════
# Routes - Main
# ══════════════════════════════════════════════════════════

@app.route('/')
@login_required
def main():
    current_user = get_current_user()
    notices      = Notice.query.filter_by(use_yn='Y').order_by(Notice.reg_dt.desc()).limit(5).all()
    ongoing_vote = Vote.query.filter_by(vote_status='ONGOING', use_yn='Y').first()

    today_start = datetime.combine(date.today(), datetime.min.time())
    today_end   = datetime.combine(date.today(), datetime.max.time())
    today_schedule = Schedule.query.filter(
        Schedule.start_dt >= today_start,
        Schedule.start_dt <= today_end,
        Schedule.use_yn == 'Y'
    ).order_by(Schedule.start_dt).all()

    condo_count = CondoReserve.query.filter_by(emp_no=current_user.emp_no, status='CONFIRM', use_yn='Y').count() if current_user else 0
    book_count  = BookRental.query.filter_by(emp_no=current_user.emp_no, status='RENTAL').count() if current_user else 0

    return render_template('main.html',
        current_user=current_user,
        notice_list=notices,
        ongoing_vote=ongoing_vote,
        today_schedule=today_schedule,
        condo_count=condo_count,
        book_count=book_count,
        current_date_str=date.today().strftime('%Y년 %m월 %d일'),
        active_menu='dashboard'
    )


# ══════════════════════════════════════════════════════════
# Routes - 공지사항
# ══════════════════════════════════════════════════════════

@app.route('/notice')
@login_required
def notice():
    current_user = get_current_user()
    notice_type  = request.args.get('type', '')
    query        = Notice.query.filter_by(use_yn='Y')
    if notice_type:
        query = query.filter_by(notice_type=notice_type)
    notices = query.order_by(Notice.is_top.desc(), Notice.reg_dt.desc()).all()
    return render_template('notice.html',
        current_user=current_user,
        notice_list=notices,
        notice_type=notice_type,
        active_menu='notice'
    )

@app.route('/notice/write')
@level_required(0)
def notice_write():
    current_user = get_current_user()
    return render_template('notice_write.html',
        current_user=current_user,
        active_menu='notice'
    )

@app.route('/notice/view/<int:notice_seq>')
@login_required
def notice_view(notice_seq):
    current_user = get_current_user()
    db.session.execute(
        db.text('UPDATE "TB_NOTICE" SET view_cnt = COALESCE(view_cnt,0) + 1 WHERE notice_seq = :seq'),
        {'seq': notice_seq}
    )
    db.session.commit()
    item = Notice.query.get_or_404(notice_seq)
    comments = NoticeComment.query.filter_by(notice_seq=notice_seq, use_yn='Y').order_by(NoticeComment.reg_dt.asc()).all()
    return render_template('notice_view.html',
        current_user=current_user,
        item=item,
        comment_list=comments,
        active_menu='notice'
    )

@app.route('/notice/delete/<int:notice_seq>', methods=['POST'])
@level_required(0)
def notice_delete(notice_seq):
    item = Notice.query.get_or_404(notice_seq)
    item.use_yn = 'N'
    db.session.commit()
    return redirect(url_for('notice'))

@app.route('/notice/save', methods=['POST'])
@level_required(1)
def notice_save():
    current_user = get_current_user()
    file_url  = None
    file_name = None
    if 'attach_file' in request.files:
        f = request.files['attach_file']
        if f and f.filename:
            result   = cloudinary.uploader.upload(f, folder='unionbbs/notice', resource_type='auto')
            file_url  = result.get('secure_url')
            file_name = f.filename
    notice = Notice(
        notice_type   = request.form.get('notice_type'),
        title         = request.form.get('title'),
        content       = request.form.get('content'),
        is_push       = request.form.get('send_mail', 'N'),
        allow_comment = request.form.get('allow_comment', 'N'),
        file_url      = file_url,
        file_name     = file_name,
        reg_user      = current_user.emp_no
    )
    db.session.add(notice)

    if request.form.get('event_date'):
        schedule = Schedule(
            title         = request.form.get('title'),
            content       = request.form.get('content'),
            start_dt      = datetime.strptime(
                f"{request.form.get('event_date')} {request.form.get('event_time', '09:00')}",
                '%Y-%m-%d %H:%M'
            ),
            end_dt        = datetime.strptime(
                f"{request.form.get('event_date')} 18:00", '%Y-%m-%d %H:%M'
            ),
            location      = request.form.get('event_location'),
            schedule_type = '01',
            reg_user      = current_user.emp_no
        )
        db.session.add(schedule)

    db.session.commit()
    flash('공지사항이 등록되었습니다.')
    return redirect(url_for('notice'))


@app.route('/notice/comment/save', methods=['POST'])
@login_required
def notice_comment_save():
    current_user = get_current_user()
    notice_seq = request.form.get('notice_seq')
    comment = NoticeComment(
        notice_seq = notice_seq,
        content    = request.form.get('comment'),
        emp_no     = current_user.emp_no,
        emp_nm     = current_user.emp_nm
    )
    db.session.add(comment)
    db.session.commit()
    return redirect(url_for('notice_view', notice_seq=notice_seq))

@app.route('/notice/comment/delete/<int:comment_seq>', methods=['POST'])
@login_required
def notice_comment_delete(comment_seq):
    comment = NoticeComment.query.get_or_404(comment_seq)
    notice_seq = comment.notice_seq
    comment.use_yn = 'N'
    db.session.commit()
    return redirect(url_for('notice_view', notice_seq=notice_seq))

# ══════════════════════════════════════════════════════════
# Routes - 일정
# ══════════════════════════════════════════════════════════

@app.route('/schedule')
@login_required
def schedule():
    current_user = get_current_user()
    schedules    = Schedule.query.filter_by(use_yn='Y').order_by(Schedule.start_dt).all()
    events = [{
        'title': s.title,
        'start': s.start_dt.strftime('%Y-%m-%dT%H:%M:%S'),
        'end':   s.end_dt.strftime('%Y-%m-%dT%H:%M:%S'),
        'className': 'event-notice'
    } for s in schedules]
    return render_template('schedule.html',
        current_user=current_user,
        events=events,
        active_menu='schedule'
    )

@app.route('/api/schedule/save', methods=['POST'])
@login_required
def schedule_save():
    current_user = get_current_user()
    data = request.json
    schedule = Schedule(
        title    = data.get('title'),
        start_dt = datetime.strptime(data.get('date'), '%Y-%m-%d'),
        end_dt   = datetime.strptime(data.get('date'), '%Y-%m-%d'),
        reg_user = current_user.emp_no
    )
    db.session.add(schedule)
    db.session.commit()
    return jsonify({'status': 'ok', 'schedule_seq': schedule.schedule_seq})


# ══════════════════════════════════════════════════════════
# Routes - 게시판
# ══════════════════════════════════════════════════════════

@app.route('/board')
@login_required
def board():
    current_user = get_current_user()
    keyword = request.args.get('q', '')
    query   = Board.query.filter_by(use_yn='Y')
    if keyword:
        query = query.filter(
            Board.title.contains(keyword) | Board.content.contains(keyword)
        )
    posts = query.order_by(Board.reg_dt.desc()).all()
    return render_template('board.html',
        current_user=current_user,
        post_list=posts,
        total_count=len(posts),
        keyword=keyword,
        active_menu='board'
    )

@app.route('/board/write')
@login_required
def board_write():
    current_user = get_current_user()
    return render_template('board_write.html',
        current_user=current_user,
        active_menu='board'
    )

@app.route('/board/view/<int:board_seq>')
@login_required
def board_view(board_seq):
    current_user = get_current_user()
    db.session.execute(
        db.text('UPDATE "TB_BOARD" SET view_cnt = COALESCE(view_cnt,0) + 1 WHERE board_seq = :seq'),
        {'seq': board_seq}
    )
    db.session.commit()
    post = Board.query.filter_by(board_seq=board_seq, use_yn='Y').first_or_404()
    comments = BoardComment.query.filter_by(board_seq=board_seq, use_yn='Y').order_by(BoardComment.reg_dt.asc()).all()
    return render_template('board_view.html',
        current_user=current_user,
        post=post,
        comment_list=comments,
        active_menu='board'
    )

@app.route('/board/save', methods=['POST'])
@login_required
def board_save():
    current_user = get_current_user()
    post = Board(
        title         = request.form.get('title'),
        content       = request.form.get('content'),
        emp_no        = current_user.emp_no,
        emp_nm        = current_user.emp_nm,
        dept_cd       = current_user.dept_cd,
        union_dept_cd = current_user.union_dept_cd,
        use_yn        = 'Y'
    )
    db.session.add(post)
    db.session.commit()
    return redirect(url_for('board'))

@app.route('/board/delete/<int:board_seq>', methods=['POST'])
@login_required
def board_delete(board_seq):
    post = Board.query.get_or_404(board_seq)
    post.use_yn = 'N'
    db.session.commit()
    return redirect(url_for('board'))

@app.route('/board/comment/save', methods=['POST'])
@login_required
def board_comment_save():
    current_user = get_current_user()
    board_seq = request.form.get('board_seq')
    comment = BoardComment(
        board_seq = board_seq,
        content   = request.form.get('comment'),
        emp_no    = current_user.emp_no,
        emp_nm    = current_user.emp_nm
    )
    db.session.add(comment)
    db.session.commit()
    return redirect(url_for('board_view', board_seq=board_seq))

@app.route('/board/comment/delete/<int:comment_seq>', methods=['POST'])
@login_required
def board_comment_delete(comment_seq):
    comment = BoardComment.query.get_or_404(comment_seq)
    board_seq = comment.board_seq
    comment.use_yn = 'N'
    db.session.commit()
    return redirect(url_for('board_view', board_seq=board_seq))


# ══════════════════════════════════════════════════════════
# Routes - 투표
# ══════════════════════════════════════════════════════════

@app.route('/vote')
@login_required
def vote():
    current_user  = get_current_user()
    active_votes  = Vote.query.filter_by(vote_status='ONGOING', use_yn='Y').all()
    archive_votes = Vote.query.filter_by(vote_status='CLOSED', use_yn='Y').all()

    for v in active_votes:
        v.items            = VoteItem.query.filter_by(vote_seq=v.vote_seq).order_by(VoteItem.sort_order).all()
        v.has_voted        = VoteHistory.query.filter_by(vote_seq=v.vote_seq, emp_no=current_user.emp_no).first() is not None
        v.participation_rate = round((v.vote_cnt / v.total_cnt * 100), 1) if v.total_cnt else 0

    for v in archive_votes:
        items = VoteItem.query.filter_by(vote_seq=v.vote_seq).all()
        total = sum(i.item_cnt for i in items) or 1
        max_cnt = max((i.item_cnt for i in items), default=0)
        v.results = [{
            'item_name': i.item_nm,
            'vote_cnt':  i.item_cnt,
            'percent':   round(i.item_cnt / total * 100, 1),
            'is_max':    i.item_cnt == max_cnt
        } for i in items]
        v.participation_rate = round((v.vote_cnt / v.total_cnt * 100), 1) if v.total_cnt else 0
        v.participant_cnt    = v.vote_cnt
        v.total_voters       = v.total_cnt

    return render_template('vote.html',
        current_user=current_user,
        active_votes=active_votes,
        archive_votes=archive_votes,
        active_menu='vote'
    )

@app.route('/vote/submit', methods=['POST'])
@login_required
def vote_submit():
    current_user = get_current_user()
    vote_seq     = request.form.get('vote_seq')
    item_seq     = request.form.get('selected_item')
    auth_pwd     = request.form.get('auth_password', '')

    try:
        pw_match = bcrypt.checkpw(auth_pwd.encode(), current_user.pwd_hash.encode())
    except Exception:
        pw_match = (auth_pwd == current_user.emp_no)

    if not pw_match:
        flash('비밀번호 인증에 실패했습니다.')
        return redirect(url_for('vote'))

    already = VoteHistory.query.filter_by(vote_seq=vote_seq, emp_no=current_user.emp_no).first()
    if already:
        flash('이미 투표하셨습니다.')
        return redirect(url_for('vote'))

    history = VoteHistory(vote_seq=vote_seq, item_seq=item_seq, emp_no=current_user.emp_no)
    db.session.add(history)

    item = VoteItem.query.get(item_seq)
    if item:
        item.item_cnt += 1
    vote = Vote.query.get(vote_seq)
    if vote:
        vote.vote_cnt += 1

    db.session.commit()
    flash('투표가 완료되었습니다.')
    return redirect(url_for('vote'))

@app.route('/admin/vote')
@level_required(1)
def admin_vote():
    current_user = get_current_user()
    votes = Vote.query.order_by(Vote.reg_dt.desc()).all()
    vote_data = []
    for v in votes:
        total = v.total_cnt or 1
        cnt   = VoteHistory.query.filter_by(vote_seq=v.vote_seq).count()
        now   = datetime.now()
        status = '진행중' if v.vote_status == 'OPEN' and v.start_dt <= now <= v.end_dt else '종료'
        vote_data.append({
            'vote_seq': v.vote_seq,
            'title': v.title,
            'target_group': '전 조합원',
            'start_dt': v.start_dt.strftime('%Y.%m.%d') if v.start_dt else '-',
            'end_dt':   v.end_dt.strftime('%Y.%m.%d')   if v.end_dt   else '-',
            'participation_rate': round(cnt / total * 100, 1),
            'participant_cnt': cnt,
            'total_voters': total,
            'status': status,
        })
    union_depts = UnionDept.query.filter_by(use_yn='Y').all()
    region_dict = {}
    for d in union_depts:
        region = d.region_nm if hasattr(d, 'region_nm') else '기타'
        region_dict.setdefault(region, []).append({'seq': d.union_dept_seq, 'name': d.union_dept_nm})
    return render_template('vote_admin.html',
        current_user=current_user,
        admin_votes=vote_data,
        region_dict=region_dict,
        active_menu='admin_vote'
    )

@app.route('/admin/book')
@level_required(1)
def admin_book():
    current_user = get_current_user()
    rental_requests = db.session.query(BookRental, Book, User)\
        .join(Book, BookRental.book_seq == Book.book_seq)\
        .outerjoin(User, BookRental.emp_no == User.emp_no)\
        .filter(BookRental.use_yn == 'Y')\
        .order_by(BookRental.reg_dt.desc()).all()

    req_rows = []
    for r, b, u in rental_requests:
        req_rows.append({
            'req_seq': r.rental_seq,
            'type':    '대출',
            'emp_nm':  u.emp_nm if u else '-',
            'title':   b.title,
            'req_dt':  r.reg_dt.strftime('%Y.%m.%d') if r.reg_dt else '-',
            'status':  r.status,
        })

    purchase_list = BookRequest.query.filter_by(use_yn='Y').order_by(BookRequest.reg_dt.desc()).all()
    book_list     = Book.query.filter_by(use_yn='Y').order_by(Book.reg_dt.desc()).all()
    my_rentals = []
    return render_template('book.html',
        current_user=current_user,
        rental_requests=req_rows,
        purchase_list=purchase_list,
        book_list=book_list,
        my_rentals=my_rentals,
        active_menu='book'
    )

@app.route('/admin/vote/create', methods=['POST'])
@level_required(1)
def vote_create():
    current_user = get_current_user()
    vote = Vote(
        title       = request.form.get('title'),
        content     = request.form.get('content'),
        start_dt    = datetime.strptime(request.form.get('start_dt'), '%Y-%m-%dT%H:%M'),
        end_dt      = datetime.strptime(request.form.get('end_dt'), '%Y-%m-%dT%H:%M'),
        vote_status = 'READY',
        total_cnt   = User.query.filter(User.user_level <= 4, User.use_yn == 'Y').count(),
        reg_user    = current_user.emp_no
    )
    db.session.add(vote)
    db.session.flush()

    items = request.form.getlist('vote_items[]')
    for idx, item_nm in enumerate(items):
        if item_nm.strip():
            db.session.add(VoteItem(vote_seq=vote.vote_seq, item_nm=item_nm, sort_order=idx))

    db.session.commit()
    flash('투표가 생성되었습니다.')
    return redirect(url_for('admin_vote'))


# ══════════════════════════════════════════════════════════
# Routes - 콘도
# ══════════════════════════════════════════════════════════

REGION_MAP = {
    'ALL':          '전체',
    'METRO':        '수도권',
    'GANGWON':      '강원',
    'CHUNGCHEONG':  '충청',
    'JEOLLA':       '전라',
    'GYEONGSANG':   '경상',
}
BRAND_MAP = {
    'ALL':     '전체',
    'SONO':    '소노',
    'HANWHA':  '한화',
    'LOTTE':   '롯데',
    'ANTO':    '안토',
}

@app.route('/condo')
@login_required
def condo():
    current_user = get_current_user()
    region  = request.args.get('region', 'ALL')
    brand   = request.args.get('brand', 'ALL')

    query = Condo.query.filter_by(use_yn='Y')
    if region != 'ALL':
        query = query.filter_by(region_cd=region)
    if brand != 'ALL':
        query = query.filter_by(brand_cd=brand)
    condos = query.order_by(Condo.region_cd, Condo.brand_cd, Condo.condo_nm).all()

    my_reserves = db.session.query(CondoReserve, Condo, CondoRoom)\
        .join(Condo, CondoReserve.condo_seq == Condo.condo_seq)\
        .outerjoin(CondoRoom, CondoReserve.room_seq == CondoRoom.room_seq)\
        .filter(CondoReserve.emp_no == current_user.emp_no, CondoReserve.use_yn == 'Y')\
        .order_by(CondoReserve.reg_dt.desc()).all()

    return render_template('condo.html',
        current_user=current_user,
        condo_list=condos,
        my_reserves=my_reserves,
        region_map=REGION_MAP,
        brand_map=BRAND_MAP,
        sel_region=region,
        sel_brand=brand,
        active_menu='condo'
    )

@app.route('/api/condo/rooms')
@login_required
def api_condo_rooms():
    condo_seq = request.args.get('condo_seq')
    rooms = CondoRoom.query.filter_by(condo_seq=condo_seq, use_yn='Y').all()
    return jsonify([{
        'room_seq':    r.room_seq,
        'room_type':   r.room_type,
        'capacity':    r.capacity,
        'description': r.description or '',
        'amenities':   r.amenities or '',
        'avail_cnt':   r.avail_cnt,
    } for r in rooms])

@app.route('/condo/apply', methods=['POST'])
@login_required
def condo_apply():
    current_user = get_current_user()
    reserve = CondoReserve(
        condo_seq  = request.form.get('condo_seq'),
        room_seq   = request.form.get('room_seq') or None,
        emp_no     = current_user.emp_no,
        check_in   = datetime.strptime(request.form.get('check_in'), '%Y-%m-%d').date(),
        check_out  = datetime.strptime(request.form.get('check_out'), '%Y-%m-%d').date(),
        status     = 'APPLY'
    )
    db.session.add(reserve)
    db.session.commit()
    flash('콘도 신청이 완료되었습니다.')
    return redirect(url_for('condo'))

@app.route('/admin/condo')
@level_required(1)
def admin_condo():
    current_user = get_current_user()
    reserve_list = db.session.query(CondoReserve, Condo, User, CondoRoom)\
        .join(Condo, CondoReserve.condo_seq == Condo.condo_seq)\
        .outerjoin(User, CondoReserve.emp_no == User.emp_no)\
        .outerjoin(CondoRoom, CondoReserve.room_seq == CondoRoom.room_seq)\
        .filter(CondoReserve.use_yn == 'Y')\
        .order_by(CondoReserve.reg_dt.desc()).all()

    rows = []
    for r, c, u, rm in reserve_list:
        rows.append({
            'reserve_seq':  r.reserve_seq,
            'emp_nm':       u.emp_nm if u else '비조합원',
            'phone_no':     u.phone_no if u else '',
            'condo_name':   c.condo_nm,
            'region_nm':    REGION_MAP.get(c.region_cd, ''),
            'brand_nm':     BRAND_MAP.get(c.brand_cd, ''),
            'room_type':    rm.room_type if rm else '',
            'check_in':     r.check_in,
            'check_out':    r.check_out,
            'status':       r.status,
            'reg_dt':       r.reg_dt,
        })

    condo_list = Condo.query.filter_by(use_yn='Y').order_by(Condo.region_cd, Condo.condo_nm).all()
    return render_template('condo_admin.html',
        current_user=current_user,
        reserve_list=rows,
        condo_list=condo_list,
        region_map=REGION_MAP,
        brand_map=BRAND_MAP,
        active_menu='admin_condo'
    )

@app.route('/admin/condo/save', methods=['POST'])
@level_required(1)
def condo_admin_save():
    reserve_seq = request.form.get('reserve_seq')
    action      = request.form.get('action')
    reserve     = CondoReserve.query.get_or_404(reserve_seq)
    if action == 'confirm':
        reserve.status = 'CONFIRM'
    elif action == 'cancel':
        reserve.status    = 'CANCEL'
        reserve.cancel_dt = datetime.now()
    db.session.commit()
    flash('처리 완료되었습니다.')
    return redirect(url_for('admin_condo'))

@app.route('/admin/condo/add', methods=['POST'])
@level_required(1)
def condo_add():
    condo = Condo(
        condo_nm    = request.form.get('condo_nm'),
        region_cd   = request.form.get('region_cd'),
        brand_cd    = request.form.get('brand_cd'),
        location    = request.form.get('location'),
        description = request.form.get('description'),
        total_room  = int(request.form.get('total_room', 1)),
        use_yn      = 'Y'
    )
    db.session.add(condo)
    db.session.commit()
    flash('리조트가 등록되었습니다.')
    return redirect(url_for('admin_condo'))

@app.route('/admin/condo/edit', methods=['POST'])
@level_required(1)
def condo_edit():
    condo = Condo.query.get_or_404(request.form.get('condo_seq'))
    condo.condo_nm    = request.form.get('condo_nm')
    condo.region_cd   = request.form.get('region_cd')
    condo.brand_cd    = request.form.get('brand_cd')
    condo.location    = request.form.get('location')
    condo.description = request.form.get('description')
    condo.total_room  = int(request.form.get('total_room', condo.total_room))
    db.session.commit()
    flash('리조트 정보가 수정되었습니다.')
    return redirect(url_for('admin_condo'))

@app.route('/admin/condo/room/add', methods=['POST'])
@level_required(1)
def condo_room_add():
    room = CondoRoom(
        condo_seq   = request.form.get('condo_seq'),
        room_type   = request.form.get('room_type'),
        capacity    = int(request.form.get('capacity', 4)),
        description = request.form.get('description'),
        amenities   = request.form.get('amenities'),
        total_cnt   = int(request.form.get('total_cnt', 1)),
        avail_cnt   = int(request.form.get('total_cnt', 1)),
        use_yn      = 'Y'
    )
    db.session.add(room)
    condo = Condo.query.get(request.form.get('condo_seq'))
    if condo:
        condo.total_room = CondoRoom.query.filter_by(condo_seq=condo.condo_seq, use_yn='Y').count() + 1
    db.session.commit()
    flash('객실유형이 등록되었습니다.')
    return redirect(url_for('admin_condo'))

@app.route('/admin/condo/room/edit', methods=['POST'])
@level_required(1)
def condo_room_edit():
    room = CondoRoom.query.get_or_404(request.form.get('room_seq'))
    room.room_type   = request.form.get('room_type')
    room.capacity    = int(request.form.get('capacity', room.capacity))
    room.description = request.form.get('description')
    room.amenities   = request.form.get('amenities')
    room.total_cnt   = int(request.form.get('total_cnt', room.total_cnt))
    db.session.commit()
    flash('객실 정보가 수정되었습니다.')
    return redirect(url_for('admin_condo'))


# ══════════════════════════════════════════════════════════
# Routes - 도서
# ══════════════════════════════════════════════════════════

@app.route('/book')
@login_required
def book():
    current_user = get_current_user()
    books        = Book.query.filter_by(use_yn='Y').order_by(Book.reg_dt.desc()).all()
    my_rentals   = BookRental.query.filter_by(emp_no=current_user.emp_no)\
                    .order_by(BookRental.rental_dt.desc()).all()
    return render_template('book.html',
        current_user=current_user,
        book_list=books,
        my_rentals=my_rentals,
        active_menu='book'
    )

@app.route('/book/rental/<int:book_seq>', methods=['POST'])
@login_required
def book_rental(book_seq):
    current_user = get_current_user()
    b = Book.query.get_or_404(book_seq)
    if b.avail_cnt <= 0:
        flash('현재 대출 가능한 도서가 없습니다.')
        return redirect(url_for('book'))
    rental = BookRental(
        book_seq  = book_seq,
        emp_no    = current_user.emp_no,
        rental_dt = date.today(),
        due_dt    = date.today() + timedelta(days=14)
    )
    b.avail_cnt -= 1
    db.session.add(rental)
    db.session.commit()
    flash('대출 신청이 완료되었습니다.')
    return redirect(url_for('book'))

@app.route('/book/request', methods=['POST'])
@login_required
def book_request():
    current_user = get_current_user()
    req = BookRequest(
        title     = request.form.get('title'),
        author    = request.form.get('author'),
        publisher = request.form.get('publisher'),
        reason    = request.form.get('reason'),
        emp_no    = current_user.emp_no
    )
    db.session.add(req)
    db.session.commit()
    flash('도서 구매 희망 신청이 완료되었습니다.')
    return redirect(url_for('book'))

@app.route('/admin/book/save', methods=['POST'])
@level_required(1)
def book_admin_save():
    book = Book(
        title     = request.form.get('title'),
        author    = request.form.get('author'),
        publisher = request.form.get('publisher'),
        isbn      = request.form.get('isbn'),
        total_cnt = int(request.form.get('total_cnt', 1)),
        avail_cnt = int(request.form.get('total_cnt', 1)),
        is_new    = 'Y'
    )
    db.session.add(book)
    db.session.commit()
    flash('도서가 등록되었습니다.')
    return redirect(url_for('book'))

@app.route('/admin/book/request/process', methods=['POST'])
@level_required(1)
def book_request_process():
    req = BookRequest.query.get_or_404(request.form.get('request_seq'))
    action = request.form.get('action')
    req.status = 'DONE' if action == 'approve' else 'REJECT'
    db.session.commit()
    flash('처리 완료되었습니다.')
    return redirect(url_for('book'))


# ══════════════════════════════════════════════════════════
# Routes - 조합소개
# ══════════════════════════════════════════════════════════

@app.route('/about')
@login_required
def about():
    current_user  = get_current_user()
    executives    = User.query.filter_by(user_level=1, use_yn='Y').all()
    delegates     = User.query.filter_by(user_level=2, use_yn='Y').all()
    chairman      = User.query.filter_by(user_level=0, use_yn='Y').first()
    auditors      = User.query.filter_by(user_level=2, use_yn='Y').limit(2).all()
    slogan_text   = None
    greeting_text = None
    senior_vice   = None
    vice_chairman = None
    return render_template('about.html',
        current_user=current_user,
        executives=executives,
        delegates=delegates,
        auditors=auditors,
        chairman=chairman,
        chairman_nm=chairman.emp_nm if chairman else '미등록',
        senior_vice=senior_vice,
        vice_chairman=vice_chairman,
        slogan_text=slogan_text,
        greeting_text=greeting_text,
        active_menu='about'
    )

@app.route('/admin/about/save', methods=['POST'])
@level_required(0)
def admin_about_save():
    section = request.form.get('section')
    flash(f'저장되었습니다. (section: {section})')
    return redirect(url_for('about'))


# ══════════════════════════════════════════════════════════
# Routes - 프로필
# ══════════════════════════════════════════════════════════

@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def profile_edit():
    current_user = get_current_user()
    if request.method == 'POST':
        new_pwd = request.form.get('new_password', '')
        cur_pwd = request.form.get('current_password', '')

        try:
            pw_match = bcrypt.checkpw(cur_pwd.encode(), current_user.pwd_hash.encode())
        except Exception:
            pw_match = (cur_pwd == current_user.emp_no)

        if not pw_match:
            flash('현재 비밀번호가 올바르지 않습니다.')
        elif len(new_pwd) < 8:
            flash('새 비밀번호는 8자리 이상이어야 합니다.')
        else:
            hashed = bcrypt.hashpw(new_pwd.encode(), bcrypt.gensalt()).decode()
            current_user.pwd_hash   = hashed
            current_user.pwd_chg_dt = date.today()
            current_user.mod_dt     = datetime.now()
            db.session.commit()
            flash('비밀번호가 변경되었습니다.')
            return redirect(url_for('main'))

    return render_template('main.html',
        current_user=current_user,
        show_profile=True,
        active_menu='profile'
    )


# ══════════════════════════════════════════════════════════
# Routes - 비밀번호 강제 변경
# ══════════════════════════════════════════════════════════

@app.route('/pwd/force-change', methods=['GET', 'POST'])
@login_required
def force_pwd_change():
    current_user = get_current_user()

    if request.method == 'POST':
        new_pwd     = request.form.get('new_password', '').strip()
        new_pwd_cfm = request.form.get('new_password_confirm', '').strip()

        if len(new_pwd) < 8:
            flash('비밀번호는 8자리 이상이어야 합니다.', 'error')
        elif new_pwd != new_pwd_cfm:
            flash('새 비밀번호와 확인 비밀번호가 일치하지 않습니다.', 'error')
        elif new_pwd == current_user.emp_no:
            flash('사번과 동일한 비밀번호는 사용할 수 없습니다.', 'error')
        else:
            hashed = bcrypt.hashpw(new_pwd.encode(), bcrypt.gensalt()).decode()
            current_user.pwd_hash    = hashed
            current_user.pwd_chg_dt  = date.today()
            current_user.pwd_init_yn = 'N'
            current_user.mod_dt      = datetime.now()
            db.session.commit()
            session.pop('force_pwd_change', None)
            flash('비밀번호가 변경되었습니다.', 'success')
            return redirect(url_for('main'))

    return render_template('force_pwd_change.html', current_user=current_user)


@app.route('/admin/user/reset-pwd', methods=['POST'])
@level_required(1)
def admin_reset_pwd():
    target_emp_no = request.form.get('emp_no', '').strip()
    target_user   = User.query.filter_by(emp_no=target_emp_no, use_yn='Y').first()

    if not target_user:
        return jsonify({'ok': False, 'msg': f'사번 {target_emp_no} 사용자를 찾을 수 없습니다.'})

    hashed = bcrypt.hashpw(target_emp_no.encode(), bcrypt.gensalt()).decode()
    target_user.pwd_hash     = hashed
    target_user.pwd_init_yn  = 'Y'
    target_user.pwd_chg_dt   = None
    target_user.pwd_fail_cnt = 0
    target_user.acct_lock_yn = 'N'
    target_user.mod_dt       = datetime.now()
    db.session.commit()

    return jsonify({'ok': True, 'msg': f'{target_user.emp_nm}({target_emp_no}) 비밀번호가 사번으로 초기화되었습니다.'})


@app.route('/admin/user/list')
@level_required(1)
def admin_user_list():
    current_user = get_current_user()
    users = User.query.filter_by(use_yn='Y').order_by(User.user_level, User.emp_no).all()
    today = date.today()
    user_rows = []
    for u in users:
        days = (today - u.pwd_chg_dt).days if u.pwd_chg_dt else None
        user_rows.append({
            'emp_no':       u.emp_no,
            'emp_nm':       u.emp_nm,
            'user_level':   u.user_level,
            'acct_lock_yn': u.acct_lock_yn,
            'pwd_init_yn':  u.pwd_init_yn,
            'pwd_chg_dt':   u.pwd_chg_dt.strftime('%Y.%m.%d') if u.pwd_chg_dt else '미변경',
            'pwd_days':     days,
            'pwd_warn':     days is not None and days >= 80,
        })
    return render_template('admin_user.html',
        current_user=current_user,
        user_rows=user_rows,
        active_menu='admin_user'
    )


# ══════════════════════════════════════════════════════════
# DB 초기화 (관리자 계정 + 공통코드만)
# ══════════════════════════════════════════════════════════

def init_db():
    db.create_all()

    if User.query.first():
        print("DB already initialized - skipping")
        return

    print("Creating initial data...")

    def make_pw(raw):
        return bcrypt.hashpw(raw.encode(), bcrypt.gensalt()).decode()

    # 공통코드
    db.session.add_all([
        Code(code_grp='EMP_TYPE', code_cd='01', code_nm='종합직', sort_order=1),
        Code(code_grp='EMP_TYPE', code_cd='02', code_nm='일반직', sort_order=2),
        Code(code_grp='EMP_TYPE', code_cd='03', code_nm='기술직', sort_order=3),
        Code(code_grp='RANK', code_cd='R01', code_nm='부장', sort_order=1),
        Code(code_grp='RANK', code_cd='R02', code_nm='차장', sort_order=2),
        Code(code_grp='RANK', code_cd='R03', code_nm='과장', sort_order=3),
        Code(code_grp='RANK', code_cd='R04', code_nm='대리', sort_order=4),
        Code(code_grp='RANK', code_cd='R05', code_nm='사원', sort_order=5),
    ])

    # 관리자 계정 1개만 생성
    db.session.add(
        User(emp_no='ADMIN', emp_nm='시스템관리자', gender='M',
             email='admin@yuanta.com', dept_cd='D001',
             user_level=0,
             pwd_hash=make_pw('Admin1234!'),
             pwd_chg_dt=date.today(),
             pwd_init_yn='N',
             use_yn='Y')
    )

    db.session.commit()
    print("Initial setup complete!")
    print("Admin: ADMIN / Admin1234!")


# ── 모든 실행 환경에서 DB 초기화 ──────────────────────────
with app.app_context():
    init_db()

@app.route('/admin/migrate')
@level_required(0)
def migrate():
    try:
        with db.engine.connect() as conn:
            conn.execute(db.text('ALTER TABLE "TB_VOTE" ADD COLUMN IF NOT EXISTS reg_dt TIMESTAMP DEFAULT NOW()'))
            conn.execute(db.text('ALTER TABLE "TB_BOARD" ADD COLUMN IF NOT EXISTS emp_nm VARCHAR(100)'))
            conn.execute(db.text('ALTER TABLE "TB_BOARD" ADD COLUMN IF NOT EXISTS dept_cd VARCHAR(20)'))
            conn.execute(db.text('ALTER TABLE "TB_BOARD" ADD COLUMN IF NOT EXISTS union_dept_cd VARCHAR(20)'))
            conn.execute(db.text('ALTER TABLE "TB_BOARD_COMMENT" ADD COLUMN IF NOT EXISTS emp_nm VARCHAR(100)'))
            conn.execute(db.text('ALTER TABLE "TB_NOTICE" ADD COLUMN IF NOT EXISTS allow_comment VARCHAR(1) DEFAULT \'N\''))
            conn.execute(db.text('ALTER TABLE "TB_NOTICE" ADD COLUMN IF NOT EXISTS file_url VARCHAR(500)'))
            conn.execute(db.text('ALTER TABLE "TB_NOTICE" ADD COLUMN IF NOT EXISTS file_name VARCHAR(200)'))
            conn.execute(db.text('''CREATE TABLE IF NOT EXISTS "TB_NOTICE_COMMENT" (
                comment_seq SERIAL PRIMARY KEY,
                notice_seq INTEGER NOT NULL,
                content TEXT NOT NULL,
                emp_no VARCHAR(20) NOT NULL,
                emp_nm VARCHAR(100),
                use_yn VARCHAR(1) DEFAULT \'Y\',
                reg_dt TIMESTAMP DEFAULT NOW()
            )'''))
            conn.commit()
        return '마이그레이션 완료!'
    except Exception as e:
        return f'오류: {str(e)}'


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)