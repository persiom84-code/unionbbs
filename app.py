"""
UnionBBS - Flask 메인 애플리케이션
PostgreSQL (운영) 전용
"""
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import joinedload
from datetime import datetime, date, timedelta, timezone
KST = timedelta(hours=9)
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
    position_cd   = db.Column(db.String(20))
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

class CondoBrand(db.Model):
    __tablename__ = 'TB_CONDO_BRAND'
    brand_id   = db.Column(db.Integer, primary_key=True, autoincrement=True)
    brand_name = db.Column(db.String(50), nullable=False)
    sort_order = db.Column(db.Integer, default=0)
    use_yn     = db.Column(db.String(1), default='Y')
    resorts    = db.relationship('CondoResort', backref='brand', lazy=True)

class CondoResort(db.Model):
    __tablename__ = 'TB_CONDO_RESORT'
    resort_id   = db.Column(db.Integer, primary_key=True, autoincrement=True)
    brand_id    = db.Column(db.Integer, db.ForeignKey('TB_CONDO_BRAND.brand_id'), nullable=False)
    resort_name = db.Column(db.String(100), nullable=False)
    sort_order  = db.Column(db.Integer, default=0)
    use_yn      = db.Column(db.String(1), default='Y')
    facilities  = db.relationship('CondoFacility', backref='resort', lazy=True)

class CondoFacility(db.Model):
    __tablename__ = 'TB_CONDO_FACILITY'
    facility_id   = db.Column(db.Integer, primary_key=True, autoincrement=True)
    resort_id     = db.Column(db.Integer, db.ForeignKey('TB_CONDO_RESORT.resort_id'), nullable=False)
    facility_name = db.Column(db.String(100), nullable=False)
    location      = db.Column(db.String(200))
    description   = db.Column(db.Text)
    image_url     = db.Column(db.String(500))
    area_info     = db.Column(db.String(200))
    price_info    = db.Column(db.Text)
    extra_info    = db.Column(db.Text)
    sort_order    = db.Column(db.Integer, default=0)
    region_name   = db.Column(db.String(50))
    use_yn        = db.Column(db.String(1), default='Y')
    created_dt    = db.Column(db.DateTime, default=datetime.now)
    updated_dt    = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    rooms         = db.relationship('CondoRoom', backref='facility', lazy=True)

class CondoRoom(db.Model):
    __tablename__ = 'TB_CONDO_ROOM'
    room_id       = db.Column(db.Integer, primary_key=True, autoincrement=True)
    facility_id   = db.Column(db.Integer, db.ForeignKey('TB_CONDO_FACILITY.facility_id'), nullable=False)
    room_type     = db.Column(db.String(100), nullable=False)
    price         = db.Column(db.Integer, default=0)
    price_offpeak = db.Column(db.Integer, default=0)
    price_peak    = db.Column(db.Integer, default=0)
    price_holiday = db.Column(db.Integer, default=0)
    price_extra   = db.Column(db.Integer, default=0)
    extra_info    = db.Column(db.Text)
    sort_order    = db.Column(db.Integer, default=0)
    use_yn        = db.Column(db.String(1), default='Y')

class CondoReserve(db.Model):
    __tablename__ = 'TB_CONDO_RESERVE'
    reserve_seq = db.Column(db.Integer, primary_key=True, autoincrement=True)
    facility_id = db.Column(db.Integer, db.ForeignKey('TB_CONDO_FACILITY.facility_id'), nullable=False)
    room_id     = db.Column(db.Integer, db.ForeignKey('TB_CONDO_ROOM.room_id'))
    emp_no      = db.Column(db.String(20))
    check_in    = db.Column(db.Date, nullable=False)
    check_out   = db.Column(db.Date, nullable=False)
    status      = db.Column(db.String(10), default='APPLY')
    memo        = db.Column(db.Text)
    cancel_dt   = db.Column(db.DateTime)
    use_yn      = db.Column(db.String(1), default='Y')
    reg_dt      = db.Column(db.DateTime, default=datetime.now)

class CondoSeason(db.Model):
    __tablename__ = 'TB_CONDO_SEASON'
    season_seq  = db.Column(db.Integer, primary_key=True, autoincrement=True)
    season_name = db.Column(db.String(100), nullable=False)
    season_type = db.Column(db.String(20), nullable=False)  # peak/offpeak/holiday/extra
    start_date  = db.Column(db.String(5), nullable=False)   # MM-DD 형식
    end_date    = db.Column(db.String(5), nullable=False)   # MM-DD 형식
    use_yn      = db.Column(db.String(1), default='Y')

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
    category   = db.Column(db.String(50))
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
    status     = db.Column(db.String(10), default='APPLY')
    reg_dt     = db.Column(db.DateTime, default=datetime.now)

class BookRequest(db.Model):
    __tablename__ = 'TB_BOOK_REQUEST'
    request_seq = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title       = db.Column(db.String(200), nullable=False)
    author      = db.Column(db.String(100))
    publisher   = db.Column(db.String(100))
    reason      = db.Column(db.Text)
    req_year    = db.Column(db.Integer)
    status      = db.Column(db.String(10), default='WAIT')
    emp_no      = db.Column(db.String(20), nullable=False)
    use_yn      = db.Column(db.String(1), default='Y')
    reg_dt      = db.Column(db.DateTime, default=datetime.now)

class About(db.Model):
    __tablename__ = 'TB_ABOUT'
    about_seq    = db.Column(db.Integer, primary_key=True, autoincrement=True)
    slogan       = db.Column(db.String(100))
    greeting     = db.Column(db.Text)
    chairman_img = db.Column(db.String(500))
    mod_dt       = db.Column(db.DateTime, onupdate=datetime.now)

class VoteTarget(db.Model):
    __tablename__ = 'TB_VOTE_TARGET'
    target_seq    = db.Column(db.Integer, primary_key=True, autoincrement=True)
    vote_seq      = db.Column(db.Integer, db.ForeignKey('TB_VOTE.vote_seq'), nullable=False)
    union_dept_cd = db.Column(db.String(20), nullable=False)

# ══════════════════════════════════════════════════════════
# Auth Helpers
# ══════════════════════════════════════════════════════════

FORCE_PWD_EXEMPT = {'login', 'logout', 'force_pwd_change', 'static'}

@app.before_request
def enforce_force_pwd_change():
    if session.get('force_pwd_change') and request.endpoint not in FORCE_PWD_EXEMPT:
        return redirect(url_for('force_pwd_change'))


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
    now = datetime.utcnow() + KST
    ongoing_vote = Vote.query.filter(
        Vote.start_dt <= now,
        Vote.end_dt   >= now,
        Vote.use_yn   == 'Y'
    ).first()

    today_start = datetime.combine(date.today(), datetime.min.time())
    today_end   = datetime.combine(date.today(), datetime.max.time())
    today_schedule = Schedule.query.filter(
        Schedule.start_dt >= today_start,
        Schedule.start_dt <= today_end,
        Schedule.use_yn == 'Y'
    ).order_by(Schedule.start_dt).all()

    condo_count = CondoReserve.query.filter_by(emp_no=current_user.emp_no, status='CONFIRM', use_yn='Y').count() if current_user else 0
    book_count  = BookRental.query.filter_by(emp_no=current_user.emp_no, status='RENTAL').count() if current_user else 0

    # 캘린더용 전체 일정
    all_schedules = Schedule.query.filter_by(use_yn='Y').order_by(Schedule.start_dt).all()
    events = [{
        'title': s.title,
        'start': s.start_dt.strftime('%Y-%m-%dT%H:%M:%S'),
        'end':   s.end_dt.strftime('%Y-%m-%dT%H:%M:%S'),
        'className': 'event-notice'
    } for s in all_schedules]

    return render_template('main.html',
        current_user=current_user,
        notice_list=notices,
        ongoing_vote=ongoing_vote,
        today_schedule=today_schedule,
        condo_count=condo_count,
        book_count=book_count,
        current_date_str=date.today().strftime('%Y년 %m월 %d일'),
        events=events,
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
    now = datetime.utcnow() + KST
    my_dept = current_user.union_dept_cd if current_user else None

    # 전체 진행중 투표 후 분회 필터링
    all_active = Vote.query.filter(
        Vote.start_dt <= now,
        Vote.end_dt   >= now,
        Vote.use_yn   == 'Y'
    ).all()

    active_votes = []
    for v in all_active:
        targets = VoteTarget.query.filter_by(vote_seq=v.vote_seq).all()
        if not targets:  # 대상 없으면 전체 공개
            active_votes.append(v)
        elif my_dept and any(t.union_dept_cd == my_dept for t in targets):
            active_votes.append(v)

    archive_votes = Vote.query.filter(
        Vote.end_dt < now,
        Vote.use_yn == 'Y'
    ).all()

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
        now   = datetime.utcnow() + KST
        status = '진행중' if v.start_dt <= now <= v.end_dt else ('예정' if now < v.start_dt else '종료')
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
    union_depts = UnionDept.query.filter_by(use_yn='Y').order_by(UnionDept.sort_order).all()
    union_dept_list = [{'cd': d.union_dept_cd, 'nm': d.union_dept_nm} for d in union_depts]
    return render_template('vote_admin.html',
        current_user=current_user,
        admin_votes=vote_data,
        union_dept_list=union_dept_list,
        active_menu='admin_vote'
    )

@app.route('/admin/book')
@level_required(1)
def admin_book():
    current_user = get_current_user()
    keyword = request.args.get('q', '').strip()
    query = Book.query.filter_by(use_yn='Y')
    if keyword:
        query = query.filter(
            Book.title.ilike(f'%{keyword}%') | Book.author.ilike(f'%{keyword}%')
        )
    book_list = query.order_by(Book.reg_dt.desc()).all()

    # 카테고리 분포
    categories = db.session.query(Book.category)\
        .filter(Book.use_yn == 'Y', Book.category != None)\
        .distinct().order_by(Book.category).all()
    category_list = [c[0] for c in categories if c[0]]

    # 연체 자동 판정
    active_loans = BookRental.query.filter(
        BookRental.status.in_(['LOAN', 'OVERDUE'])
    ).all()
    _check_overdue(active_loans)

    # 대출 신청/처리중 목록
    rental_query = db.session.query(BookRental, Book, User)\
        .outerjoin(Book, BookRental.book_seq == Book.book_seq)\
        .outerjoin(User, BookRental.emp_no == User.emp_no)\
        .filter(BookRental.status.in_(['APPLY', 'APPROVE', 'LOAN', 'OVERDUE']))\
        .order_by(BookRental.reg_dt.desc()).all()

    rental_requests = []
    for r, b, u in rental_query:
        rental_requests.append({
            'rental_seq': r.rental_seq,
            'emp_nm':     u.emp_nm if u else '-',
            'emp_no':     r.emp_no,
            'title':      b.title if b else f'도서#{r.book_seq}',
            'reg_dt':     r.reg_dt.strftime('%Y.%m.%d') if r.reg_dt else '-',
            'rental_dt':  r.rental_dt.strftime('%Y.%m.%d') if r.rental_dt else '-',
            'due_dt':     r.due_dt.strftime('%Y.%m.%d') if r.due_dt else '-',
            'status':     r.status,
        })

    # 매입 신청 목록
    purchase_query = db.session.query(BookRequest, User)\
        .outerjoin(User, BookRequest.emp_no == User.emp_no)\
        .filter(BookRequest.use_yn == 'Y')\
        .order_by(BookRequest.reg_dt.desc()).all()

    purchase_list = []
    for r, u in purchase_query:
        purchase_list.append({
            'request_seq': r.request_seq,
            'emp_nm':      u.emp_nm if u else '-',
            'title':       r.title,
            'author':      r.author or '',
            'publisher':   r.publisher or '',
            'reason':      r.reason or '',
            'req_year':    r.req_year,
            'reg_dt':      r.reg_dt.strftime('%Y.%m.%d') if r.reg_dt else '-',
            'status':      r.status,
        })

    return render_template('book_admin.html',
        current_user=current_user,
        book_list=book_list,
        category_list=category_list,
        keyword=keyword,
        rental_requests=rental_requests,
        purchase_list=purchase_list,
        active_menu='book_admin'
    )


@app.route('/admin/book/rental/process', methods=['POST'])
@level_required(1)
def admin_book_rental_process():
    """대출 신청 처리 - approve/reject/loan/return"""
    rental_seq = request.form.get('rental_seq')
    action = request.form.get('action')
    r = BookRental.query.get_or_404(rental_seq)
    b = Book.query.get(r.book_seq)
    title = b.title if b else "도서"

    if action == 'approve':
        if r.status != 'APPLY':
            flash('승인 가능한 상태가 아닙니다.', 'error')
        else:
            r.status = 'APPROVE'
            flash(f'"{title}" 대출 신청을 승인했습니다.', 'success')

    elif action == 'reject':
        if r.status != 'APPLY':
            flash('반려 가능한 상태가 아닙니다.', 'error')
        else:
            r.status = 'REJECT'
            flash(f'"{title}" 대출 신청을 반려했습니다.', 'success')

    elif action == 'loan':
        if r.status != 'APPROVE':
            flash('대출 처리 가능한 상태가 아닙니다.', 'error')
        else:
            r.status = 'LOAN'
            r.rental_dt = date.today()
            r.due_dt = date.today() + timedelta(days=14)
            if b and b.avail_cnt and b.avail_cnt > 0:
                b.avail_cnt -= 1
            flash(f'"{title}" 대출 처리되었습니다. (반납기한: {r.due_dt.strftime("%Y.%m.%d")})', 'success')

    elif action == 'return':
        if r.status not in ('LOAN', 'OVERDUE'):
            flash('반납 가능한 상태가 아닙니다.', 'error')
        else:
            r.status = 'RETURN'
            r.return_dt = date.today()
            if b:
                b.avail_cnt = (b.avail_cnt or 0) + 1
            flash(f'"{title}" 반납 처리되었습니다.', 'success')

    db.session.commit()
    return redirect(url_for('admin_book'))

@app.route('/admin/vote/create', methods=['POST'])
@level_required(0)
def vote_create():
    current_user = get_current_user()
    start_dt = datetime.strptime(
        request.form.get('start_date') + 'T' + request.form.get('start_time'), '%Y-%m-%dT%H:%M'
    )
    end_dt = datetime.strptime(
        request.form.get('end_date') + 'T' + request.form.get('end_time'), '%Y-%m-%dT%H:%M'
    )
    vote = Vote(
        title       = request.form.get('title'),
        content     = request.form.get('content'),
        start_dt    = start_dt,
        end_dt      = end_dt,
        vote_status = 'OPEN',
        total_cnt   = User.query.filter(User.user_level <= 4, User.use_yn == 'Y').count(),
        reg_user    = current_user.emp_no
    )
    db.session.add(vote)
    db.session.flush()

    items = request.form.getlist('vote_items[]')
    for idx, item_nm in enumerate(items):
        if item_nm.strip():
            db.session.add(VoteItem(vote_seq=vote.vote_seq, item_nm=item_nm, sort_order=idx))

    # 투표 대상 분회 저장
    target_type = request.form.get('target_type', 'ALL')
    if target_type == 'SPECIFIC':
        target_depts = request.form.getlist('target_dept[]')
        for dept_cd in target_depts:
            if dept_cd.strip():
                db.session.add(VoteTarget(vote_seq=vote.vote_seq, union_dept_cd=dept_cd.strip()))

    db.session.commit()
    flash('투표가 생성되었습니다.')
    return redirect(url_for('admin_vote'))


# ══════════════════════════════════════════════════════════
# Routes - 콘도
# ══════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════
# Routes - 콘도
# ══════════════════════════════════════════════════════════

@app.route('/condo')
@login_required
def condo():
    current_user = get_current_user()
    brands = CondoBrand.query.filter_by(use_yn='Y').order_by(CondoBrand.sort_order).all()
    my_reserves = db.session.query(CondoReserve, CondoFacility)\
        .join(CondoFacility, CondoReserve.facility_id == CondoFacility.facility_id)\
        .filter(CondoReserve.emp_no == current_user.emp_no, CondoReserve.use_yn == 'Y')\
        .order_by(CondoReserve.reg_dt.desc()).all()
    reserve_rows = []
    for r, f in my_reserves:
        reserve_rows.append({
            'reserve_seq': r.reserve_seq,
            'facility_name': f.facility_name,
            'check_in':  r.check_in,
            'check_out': r.check_out,
            'status':    r.status,
        })
    return render_template('condo.html',
        current_user=current_user,
        brands=brands,
        my_reserves=reserve_rows,
        active_menu='condo'
    )

@app.route('/api/condo/regions')
@login_required
def api_condo_regions():
    regions = db.session.query(CondoFacility.region_name)\
        .filter(CondoFacility.use_yn == 'Y', CondoFacility.region_name != None)\
        .distinct().order_by(CondoFacility.region_name).all()
    return jsonify([r[0] for r in regions if r[0]])

@app.route('/api/condo/resorts')
@login_required
def api_condo_resorts():
    brand_id = request.args.get('brand_id')
    resorts = CondoResort.query.filter_by(brand_id=brand_id, use_yn='Y').order_by(CondoResort.sort_order).all()
    return jsonify([{'resort_id': r.resort_id, 'resort_name': r.resort_name} for r in resorts])

@app.route('/api/condo/facilities')
@login_required
def api_condo_facilities():
    region_name = request.args.get('region_name')
    query = CondoFacility.query.filter_by(use_yn='Y')
    if region_name:
        query = query.filter_by(region_name=region_name)
    facilities = query.options(
        joinedload(CondoFacility.resort).joinedload(CondoResort.brand)
    ).order_by(CondoFacility.sort_order).all()
    return jsonify([{
        'facility_id':   f.facility_id,
        'facility_name': f.facility_name,
        'brand_name':    f.resort.brand.brand_name if f.resort and f.resort.brand else '',
        'location':      f.location or '',
        'region_name':   f.region_name or '',
        'area_info':     f.area_info or '',
        'price_info':    f.price_info or '',
        'extra_info':    f.extra_info or '',
        'image_url':     f.image_url or '',
    } for f in facilities])

@app.route('/api/condo/rooms')
@login_required
def api_condo_rooms():
    facility_id = request.args.get('facility_id')
    rooms = CondoRoom.query.filter_by(facility_id=facility_id, use_yn='Y').order_by(CondoRoom.sort_order).all()
    return jsonify([{
        'room_id':    r.room_id,
        'room_type':  r.room_type,
        'price':      r.price,
        'extra_info': r.extra_info or '',
    } for r in rooms])

@app.route('/api/condo/availability')
@login_required
def api_condo_availability():
    facility_id = request.args.get('facility_id')
    check_in    = request.args.get('check_in')
    check_out   = request.args.get('check_out')
    count = CondoReserve.query.filter(
        CondoReserve.facility_id == facility_id,
        CondoReserve.status.in_(['APPLY','CONFIRM']),
        CondoReserve.use_yn == 'Y',
        CondoReserve.check_in < check_out,
        CondoReserve.check_out > check_in
    ).count()
    return jsonify({'count': count})
@app.route('/condo/apply', methods=['POST'])
@login_required   
def condo_apply():
    current_user = get_current_user()
    check_in  = datetime.strptime(request.form.get('check_in'), '%Y-%m-%d').date()
    check_out = datetime.strptime(request.form.get('check_out'), '%Y-%m-%d').date()
    if check_out <= check_in:
        flash('퇴실일은 입실일보다 늦어야 합니다.')
        return redirect(url_for('condo'))
    reserve = CondoReserve(
        facility_id = request.form.get('facility_id'),
        room_id     = request.form.get('room_id') or None,
        emp_no      = current_user.emp_no,
        check_in    = check_in,
        check_out   = check_out,
        memo        = request.form.get('memo') or None,
        status      = 'APPLY'
    )
    db.session.add(reserve)
    db.session.commit()
    flash('콘도 신청이 완료되었습니다.')
    return redirect(url_for('condo'))

@app.route('/admin/condo')
@level_required(1)
def admin_condo():
    current_user = get_current_user()
    brands    = CondoBrand.query.filter_by(use_yn='Y').order_by(CondoBrand.sort_order).all()
    resorts   = CondoResort.query.filter_by(use_yn='Y').order_by(CondoResort.sort_order).all()
    facilities = CondoFacility.query.options(
        joinedload(CondoFacility.resort).joinedload(CondoResort.brand)
    ).filter_by(use_yn='Y').order_by(CondoFacility.sort_order).all()

    reserve_list = db.session.query(CondoReserve, CondoFacility, User)\
        .join(CondoFacility, CondoReserve.facility_id == CondoFacility.facility_id)\
        .outerjoin(User, CondoReserve.emp_no == User.emp_no)\
        .filter(CondoReserve.use_yn == 'Y')\
        .order_by(CondoReserve.reg_dt.desc()).all()

    rows = []
    for r, f, u in reserve_list:
        rows.append({
            'reserve_seq':   r.reserve_seq,
            'emp_nm':        u.emp_nm if u else '-',
            'phone_no':      u.phone_no if u else '',
            'facility_name': f.facility_name,
            'check_in':      r.check_in,
            'check_out':     r.check_out,
            'status':        r.status,
            'reg_dt':        r.reg_dt,
        })

    room_query = db.session.query(CondoRoom, CondoFacility, CondoResort, CondoBrand)\
        .join(CondoFacility, CondoRoom.facility_id == CondoFacility.facility_id)\
        .join(CondoResort, CondoFacility.resort_id == CondoResort.resort_id)\
        .join(CondoBrand, CondoResort.brand_id == CondoBrand.brand_id)\
        .filter(CondoRoom.use_yn == 'Y')\
        .order_by(CondoRoom.sort_order).all()
    rooms = [{
        'room_id':       r.room_id,
        'facility_id':   r.facility_id,
        'room_type':     r.room_type,
        'price':         r.price,
        'extra_info':    r.extra_info or '',
        'sort_order':    r.sort_order,
        'brand_name':    b.brand_name,
        'resort_name':   rs.resort_name,
        'facility_name': f.facility_name,
    } for r, f, rs, b in room_query]
    seasons = CondoSeason.query.filter_by(use_yn='Y').order_by(CondoSeason.season_type, CondoSeason.start_date).all()

    # 승인 목록 (기간별/사용자별 필터)
    date_from = request.args.get('date_from', '')
    date_to   = request.args.get('date_to', '')
    emp_nm_q  = request.args.get('emp_nm', '')
    approved_query = db.session.query(CondoReserve, CondoFacility, User)\
        .join(CondoFacility, CondoReserve.facility_id == CondoFacility.facility_id)\
        .outerjoin(User, CondoReserve.emp_no == User.emp_no)\
        .filter(CondoReserve.status == 'CONFIRM', CondoReserve.use_yn == 'Y')
    if date_from:
        approved_query = approved_query.filter(CondoReserve.check_in >= date_from)
    if date_to:
        approved_query = approved_query.filter(CondoReserve.check_in <= date_to)
    if emp_nm_q:
        approved_query = approved_query.filter(User.emp_nm.ilike(f'%{emp_nm_q}%'))
    approved_rows = []
    for r, f, u in approved_query.order_by(CondoReserve.check_in.desc()).all():
        approved_rows.append({
            'reserve_seq':   r.reserve_seq,
            'emp_nm':        u.emp_nm if u else '-',
            'emp_no':        r.emp_no,
            'facility_name': f.facility_name,
            'check_in':      r.check_in,
            'check_out':     r.check_out,
            'reg_dt':        r.reg_dt,
            'memo':          r.memo or '',
        })

    return render_template('condo_admin.html',
        current_user=current_user,
        reserve_list=rows,
        approved_list=approved_rows,
        brands=brands,
        resorts=resorts,
        facilities=facilities,
        rooms=rooms,
        seasons=seasons,
        date_from=date_from,
        date_to=date_to,
        emp_nm_q=emp_nm_q,
        active_menu='admin_condo'
    )

@app.route('/admin/condo/reserve/save', methods=['POST'])
@level_required(1)
def condo_reserve_save():
    reserve = CondoReserve.query.get_or_404(request.form.get('reserve_seq'))
    action  = request.form.get('action')
    if action == 'confirm':
        reserve.status = 'CONFIRM'
    elif action == 'cancel':
        reserve.status    = 'CANCEL'
        reserve.cancel_dt = datetime.now()
    db.session.commit()
    flash('처리 완료되었습니다.')
    return redirect(url_for('admin_condo'))

@app.route('/admin/condo/brand/save', methods=['POST'])
@level_required(1)
def condo_brand_save():
    action = request.form.get('action')
    if action == 'add':
        db.session.add(CondoBrand(
            brand_name = request.form.get('brand_name'),
            sort_order = int(request.form.get('sort_order', 0))
        ))
        flash('브랜드가 등록되었습니다.')
    elif action == 'edit':
        brand = CondoBrand.query.get_or_404(request.form.get('brand_id'))
        brand.brand_name = request.form.get('brand_name')
        brand.sort_order = int(request.form.get('sort_order', brand.sort_order))
        flash('브랜드가 수정되었습니다.')
    elif action == 'delete':
        brand = CondoBrand.query.get_or_404(request.form.get('brand_id'))
        brand.use_yn = 'N'
        flash('브랜드가 삭제되었습니다.')
    db.session.commit()
    return redirect(url_for('admin_condo'))

@app.route('/admin/condo/resort/save', methods=['POST'])
@level_required(1)
def condo_resort_save():
    action = request.form.get('action')
    if action == 'add':
        db.session.add(CondoResort(
            brand_id   = request.form.get('brand_id'),
            resort_name = request.form.get('resort_name'),
            sort_order  = int(request.form.get('sort_order', 0))
        ))
        flash('리조트가 등록되었습니다.')
    elif action == 'edit':
        resort = CondoResort.query.get_or_404(request.form.get('resort_id'))
        resort.brand_id    = request.form.get('brand_id')
        resort.resort_name = request.form.get('resort_name')
        resort.sort_order  = int(request.form.get('sort_order', resort.sort_order))
        flash('리조트가 수정되었습니다.')
    elif action == 'delete':
        resort = CondoResort.query.get_or_404(request.form.get('resort_id'))
        resort.use_yn = 'N'
        flash('리조트가 삭제되었습니다.')
    db.session.commit()
    return redirect(url_for('admin_condo'))

@app.route('/admin/condo/facility/save', methods=['POST'])
@level_required(1)
def condo_facility_save():
    action = request.form.get('action')
    if action == 'add':
        db.session.add(CondoFacility(
            resort_id     = request.form.get('resort_id'),
            facility_name = request.form.get('facility_name'),
            location      = request.form.get('location'),
            description   = request.form.get('description'),
            area_info     = request.form.get('area_info'),
            price_info    = request.form.get('price_info'),
            extra_info    = request.form.get('extra_info'),
            sort_order    = int(request.form.get('sort_order', 0)),
            region_name   = request.form.get('region_name')
        ))
        flash('시설이 등록되었습니다.')
    elif action == 'edit':
        f = CondoFacility.query.get_or_404(request.form.get('facility_id'))
        f.resort_id     = request.form.get('resort_id')
        f.facility_name = request.form.get('facility_name')
        f.location      = request.form.get('location')
        f.description   = request.form.get('description')
        f.area_info     = request.form.get('area_info')
        f.price_info    = request.form.get('price_info')
        f.extra_info    = request.form.get('extra_info')
        f.sort_order    = int(request.form.get('sort_order', f.sort_order))
        f.region_name   = request.form.get('region_name')
        f.updated_dt    = datetime.now()
        flash('시설 정보가 수정되었습니다.')
    elif action == 'delete':
        f = CondoFacility.query.get_or_404(request.form.get('facility_id'))
        f.use_yn = 'N'
        flash('시설이 삭제되었습니다.')
    db.session.commit()
    return redirect(url_for('admin_condo'))

@app.route('/admin/condo/room/save', methods=['POST'])
@level_required(1)
def condo_room_save():
    action = request.form.get('action')
    if action == 'add':
        db.session.add(CondoRoom(
            facility_id   = request.form.get('facility_id'),
            room_type     = request.form.get('room_type'),
            price         = int(request.form.get('price', 0)),
            price_offpeak = int(request.form.get('price_offpeak', 0)),
            price_peak    = int(request.form.get('price_peak', 0)),
            price_holiday = int(request.form.get('price_holiday', 0)),
            price_extra   = int(request.form.get('price_extra', 0)),
            extra_info    = request.form.get('extra_info'),
            sort_order    = int(request.form.get('sort_order', 0))
        ))
        flash('객실이 등록되었습니다.')
    elif action == 'edit':
        r = CondoRoom.query.get_or_404(request.form.get('room_id'))
        r.facility_id   = request.form.get('facility_id')
        r.room_type     = request.form.get('room_type')
        r.price         = int(request.form.get('price', 0))
        r.price_offpeak = int(request.form.get('price_offpeak', 0))
        r.price_peak    = int(request.form.get('price_peak', 0))
        r.price_holiday = int(request.form.get('price_holiday', 0))
        r.price_extra   = int(request.form.get('price_extra', 0))
        r.extra_info    = request.form.get('extra_info')
        r.sort_order    = int(request.form.get('sort_order', r.sort_order))
        flash('객실 정보가 수정되었습니다.')
    elif action == 'delete':
        r = CondoRoom.query.get_or_404(request.form.get('room_id'))
        r.use_yn = 'N'
        flash('객실이 삭제되었습니다.')
    db.session.commit()
    return redirect(url_for('admin_condo'))
@app.route('/admin/condo/import', methods=['POST'])
@level_required(1)
def condo_facility_import():
    import csv, io
    f = request.files.get('csv_file')
    if not f or not f.filename.endswith('.csv'):
        flash('CSV 파일을 선택해주세요.')
        return redirect(url_for('admin_condo'))
    try:
        stream = io.StringIO(f.stream.read().decode('utf-8-sig'))
        reader = csv.DictReader(stream)
        rows = list(reader)

        # ── 브랜드: 이름 기준 중복 체크 후 INSERT ──
        brands = {}
        for i, brand_name in enumerate(dict.fromkeys(r['brand_name'] for r in rows), 1):
            existing = CondoBrand.query.filter_by(brand_name=brand_name).first()
            if existing:
                brands[brand_name] = existing.brand_id
            else:
                b = CondoBrand(brand_name=brand_name, sort_order=i)
                db.session.add(b)
                db.session.flush()
                brands[brand_name] = b.brand_id

        # ── 리조트: (brand_id, resort_name) 기준 중복 체크 후 INSERT ──
        resorts = {}
        seen_resorts = []
        for row in rows:
            key = (row['brand_name'], row['resort_name'])
            if key not in seen_resorts:
                seen_resorts.append(key)
                brand_id = brands[row['brand_name']]
                existing = CondoResort.query.filter_by(
                    brand_id=brand_id, resort_name=row['resort_name']
                ).first()
                if existing:
                    resorts[key] = existing.resort_id
                else:
                    r = CondoResort(
                        brand_id=brand_id,
                        resort_name=row['resort_name'],
                        sort_order=len(seen_resorts)
                    )
                    db.session.add(r)
                    db.session.flush()
                    resorts[key] = r.resort_id

        # ── 시설: (resort_id, facility_name) 기준 중복 체크 → 있으면 UPDATE, 없으면 INSERT ──
        inserted = updated = 0
        for row in rows:
            key = (row['brand_name'], row['resort_name'])
            resort_id = resorts[key]
            existing = CondoFacility.query.filter_by(
                resort_id=resort_id, facility_name=row['facility_name']
            ).first()
            if existing:
                existing.region_name = row.get('region_name') or existing.region_name
                existing.location    = row.get('location')    or existing.location
                existing.area_info   = row.get('area_info')   or existing.area_info
                existing.price_info  = row.get('price_info')  or existing.price_info
                existing.extra_info  = row.get('extra_info')  or existing.extra_info
                existing.sort_order  = int(row.get('sort_order') or existing.sort_order)
                updated += 1
            else:
                db.session.add(CondoFacility(
                    resort_id     = resort_id,
                    facility_name = row['facility_name'],
                    region_name   = row.get('region_name') or None,
                    location      = row.get('location') or None,
                    area_info     = row.get('area_info') or None,
                    price_info    = row.get('price_info') or None,
                    extra_info    = row.get('extra_info') or None,
                    sort_order    = int(row.get('sort_order') or 0)
                ))
                inserted += 1

        db.session.commit()
        flash(f'CSV 가져오기 완료! 신규 {inserted}개 등록, {updated}개 업데이트됨.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'오류: {str(e)}', 'error')
    return redirect(url_for('admin_condo'))
# ══════════════════════════════════════════════════════════
@app.route('/admin/condo/reserve/export')
@level_required(1)
def condo_reserve_export():
    import csv, io
    date_from = request.args.get('date_from', '')
    date_to   = request.args.get('date_to', '')
    query = db.session.query(CondoReserve, CondoFacility, User)\
        .join(CondoFacility, CondoReserve.facility_id == CondoFacility.facility_id)\
        .outerjoin(User, CondoReserve.emp_no == User.emp_no)\
        .filter(CondoReserve.status == 'CONFIRM', CondoReserve.use_yn == 'Y')
    if date_from:
        query = query.filter(CondoReserve.check_in >= date_from)
    if date_to:
        query = query.filter(CondoReserve.check_in <= date_to)
    rows = query.order_by(CondoReserve.check_in).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['신청자','사번','시설명','체크인','체크아웃','신청일','비고'])
    for r, f, u in rows:
        writer.writerow([
            u.emp_nm if u else '-',
            r.emp_no,
            f.facility_name,
            r.check_in.strftime('%Y-%m-%d') if r.check_in else '',
            r.check_out.strftime('%Y-%m-%d') if r.check_out else '',
            r.reg_dt.strftime('%Y-%m-%d') if r.reg_dt else '',
            r.memo or ''
        ])
    output.seek(0)
    from flask import Response
    return Response(
        '\ufeff' + output.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': 'attachment; filename=condo_approved.csv',
            'Cache-Control': 'no-store, no-cache, must-revalidate',
            'Pragma': 'no-cache',
        }
    )

@app.route('/admin/condo/season/save', methods=['POST'])
@level_required(1)
def condo_season_save():
    action = request.form.get('action')
    if action == 'add':
        db.session.add(CondoSeason(
            season_name = request.form.get('season_name'),
            season_type = request.form.get('season_type'),
            start_date  = request.form.get('start_date'),
            end_date    = request.form.get('end_date')
        ))
        flash('시즌이 등록되었습니다.')
    elif action == 'edit':
        s = CondoSeason.query.get_or_404(request.form.get('season_seq'))
        s.season_name = request.form.get('season_name')
        s.season_type = request.form.get('season_type')
        s.start_date  = request.form.get('start_date')
        s.end_date    = request.form.get('end_date')
        flash('시즌이 수정되었습니다.')
    elif action == 'delete':
        s = CondoSeason.query.get_or_404(request.form.get('season_seq'))
        s.use_yn = 'N'
        flash('시즌이 삭제되었습니다.')
    db.session.commit()
    return redirect(url_for('admin_condo'))

# Routes - 도서
# ══════════════════════════════════════════════════════════

def _check_overdue(rentals):
    """대출 목록의 연체 자동 판정 — D+17(due_dt+3) 부터 OVERDUE로 변경"""
    today = date.today()
    changed = False
    for r in rentals:
        if r.status == 'LOAN' and r.due_dt and (today - r.due_dt).days > 3:
            r.status = 'OVERDUE'
            changed = True
    if changed:
        db.session.commit()


def _has_penalty(emp_no):
    """해당 사용자가 패널티 상태인지 (OVERDUE 보유 여부) — 자동 판정 포함"""
    rentals = BookRental.query.filter(
        BookRental.emp_no == emp_no,
        BookRental.status.in_(['LOAN', 'OVERDUE'])
    ).all()
    _check_overdue(rentals)
    return any(r.status == 'OVERDUE' for r in rentals)


@app.route('/book')
@login_required
def book():
    current_user = get_current_user()
    keyword  = request.args.get('q', '').strip()
    category = request.args.get('category', '').strip()

    query = Book.query.filter_by(use_yn='Y')
    if keyword:
        query = query.filter(
            Book.title.ilike(f'%{keyword}%') |
            Book.author.ilike(f'%{keyword}%') |
            Book.publisher.ilike(f'%{keyword}%')
        )
    if category:
        query = query.filter_by(category=category)
    books = query.order_by(Book.reg_dt.desc()).all()

    # 카테고리 목록 (필터 dropdown용)
    categories = db.session.query(Book.category)\
        .filter(Book.use_yn == 'Y', Book.category != None)\
        .distinct().order_by(Book.category).all()
    category_list = [c[0] for c in categories if c[0]]

    # 내 대출 이력 + 연체 자동 판정
    my_rentals = db.session.query(BookRental, Book)\
        .outerjoin(Book, BookRental.book_seq == Book.book_seq)\
        .filter(BookRental.emp_no == current_user.emp_no)\
        .order_by(BookRental.reg_dt.desc()).all()
    _check_overdue([r for r, b in my_rentals])

    rental_rows = [{
        'book_title': b.title if b else f'도서#{r.book_seq}',
        'rental_dt':  r.rental_dt,
        'due_dt':     r.due_dt,
        'return_dt':  r.return_dt,
        'status':     r.status,
        'reg_dt':     r.reg_dt,
    } for r, b in my_rentals]

    # 패널티 여부
    has_penalty = any(r['status'] == 'OVERDUE' for r in rental_rows)

    # 신청 진행중인 book_seq 목록 (중복 신청 방지용)
    pending_book_seqs = {r.book_seq for r, b in my_rentals
                        if r.status in ('APPLY', 'APPROVE', 'LOAN', 'OVERDUE')}

    # 매입 신청 잔여 카운트 (연간 5권, 승인기준)
    this_year = date.today().year
    approved_this_year = BookRequest.query.filter(
        BookRequest.emp_no == current_user.emp_no,
        BookRequest.req_year == this_year,
        BookRequest.status == 'APPROVE',
        BookRequest.use_yn == 'Y',
    ).count()
    remaining_purchases = max(0, 5 - approved_this_year)

    return render_template('book.html',
        current_user=current_user,
        book_list=books,
        category_list=category_list,
        keyword=keyword,
        active_category=category,
        my_rentals=rental_rows,
        pending_book_seqs=pending_book_seqs,
        has_penalty=has_penalty,
        remaining_purchases=remaining_purchases,
        active_menu='book'
    )


@app.route('/book/rental/<int:book_seq>', methods=['POST'])
@login_required
def book_rental(book_seq):
    """대출 신청 — APPLY 상태로 등록 (관리자 승인 후 LOAN으로 전환)"""
    current_user = get_current_user()

    # 패널티 차단
    if _has_penalty(current_user.emp_no):
        flash('연체된 도서가 있어 대출 신청이 불가합니다. 반납 후 이용해주세요.', 'error')
        return redirect(url_for('book'))

    b = Book.query.get_or_404(book_seq)

    # 이미 신청/승인/대출중이면 차단
    existing = BookRental.query.filter(
        BookRental.book_seq == book_seq,
        BookRental.emp_no == current_user.emp_no,
        BookRental.status.in_(['APPLY', 'APPROVE', 'LOAN', 'OVERDUE'])
    ).first()
    if existing:
        flash('이미 신청 또는 대출 중인 도서입니다.', 'error')
        return redirect(url_for('book'))

    # 다른 사람이 대출중이면 차단
    if b.avail_cnt is None or b.avail_cnt <= 0:
        flash('현재 대출 가능한 도서가 아닙니다.', 'error')
        return redirect(url_for('book'))

    # 다른 사람이 신청/승인 단계여도 차단 (선착순)
    other_pending = BookRental.query.filter(
        BookRental.book_seq == book_seq,
        BookRental.status.in_(['APPLY', 'APPROVE'])
    ).first()
    if other_pending:
        flash('다른 조합원이 이미 신청한 도서입니다.', 'error')
        return redirect(url_for('book'))

    rental = BookRental(
        book_seq  = book_seq,
        emp_no    = current_user.emp_no,
        rental_dt = None,
        due_dt    = date.today() + timedelta(days=14),  # 임시값, 승인 시점에 재설정
        status    = 'APPLY',
    )
    db.session.add(rental)
    db.session.commit()
    flash('대출 신청이 완료되었습니다. 관리자 승인 후 도서가 발송됩니다.', 'success')
    return redirect(url_for('book'))


@app.route('/book/request', methods=['POST'])
@login_required
def book_request():
    """매입 신청 — 연간 5권(승인기준) 제한 + 패널티 차단"""
    current_user = get_current_user()

    # 패널티 차단
    if _has_penalty(current_user.emp_no):
        flash('연체된 도서가 있어 매입 신청이 불가합니다.', 'error')
        return redirect(url_for('book'))

    this_year = date.today().year
    approved_cnt = BookRequest.query.filter(
        BookRequest.emp_no == current_user.emp_no,
        BookRequest.req_year == this_year,
        BookRequest.status == 'APPROVE',
        BookRequest.use_yn == 'Y',
    ).count()
    if approved_cnt >= 5:
        flash(f'올해 매입 신청 한도(5권)를 모두 사용하셨습니다.', 'error')
        return redirect(url_for('book'))

    title = (request.form.get('title') or '').strip()
    if not title:
        flash('도서명을 입력해주세요.', 'error')
        return redirect(url_for('book'))

    req = BookRequest(
        title     = title,
        author    = (request.form.get('author') or '').strip() or None,
        publisher = (request.form.get('publisher') or '').strip() or None,
        reason    = (request.form.get('reason') or '').strip() or None,
        req_year  = this_year,
        status    = 'WAIT',
        emp_no    = current_user.emp_no,
    )
    db.session.add(req)
    db.session.commit()
    flash('도서 매입 신청이 완료되었습니다.', 'success')
    return redirect(url_for('book'))

@app.route('/admin/book/save', methods=['POST'])
@level_required(1)
def book_admin_save():
    action = request.form.get('action')
    if action == 'add':
        db.session.add(Book(
            title     = request.form.get('title', '').strip(),
            author    = request.form.get('author', '').strip() or None,
            publisher = request.form.get('publisher', '').strip() or None,
            category  = request.form.get('category', '').strip() or None,
            total_cnt = 1,
            avail_cnt = 1,
            use_yn    = 'Y'
        ))
        flash('도서가 등록되었습니다.', 'success')
    elif action == 'edit':
        b = Book.query.get_or_404(request.form.get('book_seq'))
        b.title     = request.form.get('title', '').strip()
        b.author    = request.form.get('author', '').strip() or None
        b.publisher = request.form.get('publisher', '').strip() or None
        b.category  = request.form.get('category', '').strip() or None
        flash('도서 정보가 수정되었습니다.', 'success')
    elif action == 'delete':
        b = Book.query.get_or_404(request.form.get('book_seq'))
        b.use_yn = 'N'
        flash('도서가 삭제되었습니다.', 'success')
    db.session.commit()
    return redirect(url_for('admin_book'))


@app.route('/admin/book/import', methods=['POST'])
@level_required(1)
def admin_book_import():
    import csv, io
    f = request.files.get('csv_file')
    if not f or not f.filename.endswith('.csv'):
        flash('CSV 파일을 선택해주세요.', 'error')
        return redirect(url_for('admin_book'))
    try:
        stream = io.StringIO(f.stream.read().decode('utf-8-sig'))
        reader = csv.DictReader(stream)
        rows = list(reader)

        inserted = updated = skipped = 0
        for row in rows:
            title = (row.get('title') or '').strip()
            if not title:
                skipped += 1
                continue
            author    = (row.get('author') or '').strip() or None
            publisher = (row.get('publisher') or '').strip() or None
            category  = (row.get('category') or '').strip() or None

            # 중복판정: title + author 조합
            existing = Book.query.filter_by(title=title, author=author).first()
            if existing:
                existing.publisher = publisher or existing.publisher
                existing.category  = category  or existing.category
                if existing.use_yn == 'N':
                    existing.use_yn = 'Y'
                updated += 1
            else:
                db.session.add(Book(
                    title     = title,
                    author    = author,
                    publisher = publisher,
                    category  = category,
                    total_cnt = 1,
                    avail_cnt = 1,
                    use_yn    = 'Y'
                ))
                inserted += 1

        db.session.commit()
        flash(f'CSV 업로드 완료! 신규 {inserted}권, {updated}권 업데이트, {skipped}건 건너뜀.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'오류: {str(e)}', 'error')
    return redirect(url_for('admin_book'))


@app.route('/admin/book/export')
@level_required(1)
def admin_book_export():
    import csv, io
    books = Book.query.filter_by(use_yn='Y').order_by(Book.reg_dt.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['title','author','publisher','category','total_cnt','avail_cnt','use_yn'])
    for b in books:
        writer.writerow([
            b.title or '',
            b.author or '',
            b.publisher or '',
            b.category or '',
            b.total_cnt if b.total_cnt is not None else 1,
            b.avail_cnt if b.avail_cnt is not None else 1,
            b.use_yn or 'Y',
        ])
    output.seek(0)
    from flask import Response
    return Response(
        '\ufeff' + output.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': 'attachment; filename=books.csv',
            'Cache-Control': 'no-store, no-cache, must-revalidate',
            'Pragma': 'no-cache',
        }
    )

@app.route('/admin/book/request/process', methods=['POST'])
@level_required(1)
def book_request_process():
    req = BookRequest.query.get_or_404(request.form.get('request_seq'))
    action = request.form.get('action')
    if action == 'approve':
        req.status = 'APPROVE'
        flash(f'"{req.title}" 매입 신청을 승인했습니다.', 'success')
    elif action == 'reject':
        req.status = 'REJECT'
        flash(f'"{req.title}" 매입 신청을 반려했습니다.', 'success')
    db.session.commit()
    return redirect(url_for('admin_book'))


# ══════════════════════════════════════════════════════════
# Routes - 조합소개
# ══════════════════════════════════════════════════════════

@app.route('/about')
@login_required
def about():
    current_user  = get_current_user()
    executives    = User.query.filter_by(user_level=1, use_yn='Y').all()
    delegates     = User.query.filter_by(user_level=2, use_yn='Y').all()
    chairman      = User.query.filter_by(position_cd='CHAIRMAN', use_yn='Y').first()
    auditors      = User.query.filter_by(position_cd='AUDITOR', use_yn='Y').all()
    senior_vice   = User.query.filter_by(position_cd='SENIOR_VICE', use_yn='Y').first()
    vice_chairman = User.query.filter_by(position_cd='VICE', use_yn='Y').first()
    about_data    = About.query.first()
    return render_template('about.html',
        current_user=current_user,
        executives=executives,
        delegates=delegates,
        auditors=auditors,
        chairman=chairman,
        chairman_nm=chairman.emp_nm if chairman else '미등록',
        chairman_img=about_data.chairman_img if about_data else None,
        senior_vice=senior_vice,
        vice_chairman=vice_chairman,
        slogan_text=about_data.slogan if about_data else None,
        greeting_text=about_data.greeting if about_data else None,
        active_menu='about'
    )

@app.route('/admin/about/save', methods=['POST'])
@level_required(0)
def admin_about_save():
    about_data = About.query.first()
    if not about_data:
        about_data = About()
        db.session.add(about_data)

    section = request.form.get('section')

    if section == 'slogan':
        about_data.slogan   = request.form.get('slogan_text', '').strip()
        about_data.greeting = request.form.get('greeting_text', '').strip()
        flash('슬로건 및 인사말이 저장되었습니다.')

    elif section == 'chairman_img':
        f = request.files.get('chairman_img')
        if f and f.filename:
            result = cloudinary.uploader.upload(f, folder='unionbbs/about', resource_type='image')
            about_data.chairman_img = result.get('secure_url')
            flash('위원장 사진이 등록되었습니다.')

    elif section == 'auditor':
        action  = request.form.get('action')
        emp_no  = request.form.get('emp_no', '').strip()
        user    = User.query.filter_by(emp_no=emp_no, use_yn='Y').first()
        if user:
            if action == 'add':
                user.position_cd = 'AUDITOR'
                flash(f'{user.emp_nm} 회계감사로 등록되었습니다.')
            elif action == 'remove':
                user.position_cd = None
                flash(f'{user.emp_nm} 회계감사 해제되었습니다.')
        else:
            flash('해당 사번의 사용자를 찾을 수 없습니다.')

    elif section == 'executive':
        action = request.form.get('action')
        emp_no = request.form.get('emp_no', '').strip()
        user   = User.query.filter_by(emp_no=emp_no, use_yn='Y').first()
        if user:
            if action == 'add':
                user.user_level = 1
                flash(f'{user.emp_nm} 집행위원으로 등록되었습니다.')
            elif action == 'remove':
                user.user_level = 4
                flash(f'{user.emp_nm} 집행위원 해제되었습니다. (조합원으로 변경)')
        else:
            flash('해당 사번의 사용자를 찾을 수 없습니다.')

    elif section == 'delegate':
        action = request.form.get('action')
        emp_no = request.form.get('emp_no', '').strip()
        user   = User.query.filter_by(emp_no=emp_no, use_yn='Y').first()
        if user:
            if action == 'add':
                user.user_level = 2
                flash(f'{user.emp_nm} 대의원으로 등록되었습니다.')
            elif action == 'remove':
                user.user_level = 4
                flash(f'{user.emp_nm} 대의원 해제되었습니다. (조합원으로 변경)')
        else:
            flash('해당 사번의 사용자를 찾을 수 없습니다.')

    db.session.commit()
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


@app.route('/admin/user/update', methods=['POST'])
@level_required(0)
def admin_user_update():
    try:
        emp_no      = request.form.get('emp_no', '').strip()
        user_level  = request.form.get('user_level', '').strip()
        position_cd = request.form.get('position_cd', '').strip()
        user = User.query.filter_by(emp_no=emp_no, use_yn='Y').first()
        if not user:
            return jsonify({'ok': False, 'msg': '사용자를 찾을 수 없습니다.'})
        if user_level != '':
            user.user_level = int(user_level)
        user.position_cd   = position_cd if position_cd else None
        union_dept_cd = request.form.get('union_dept_cd', '').strip()
        user.union_dept_cd = union_dept_cd if union_dept_cd else None
        db.session.commit()
        return jsonify({'ok': True, 'msg': f'{user.emp_nm} 정보가 변경되었습니다.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'ok': False, 'msg': f'오류: {str(e)}'})

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
            'emp_no':         u.emp_no,
            'emp_nm':         u.emp_nm,
            'user_level':     u.user_level,
            'position_cd':    u.position_cd or '',
            'union_dept_cd':  u.union_dept_cd or '',
            'acct_lock_yn':   u.acct_lock_yn,
            'pwd_init_yn':    u.pwd_init_yn,
            'pwd_chg_dt':     u.pwd_chg_dt.strftime('%Y.%m.%d') if u.pwd_chg_dt else '미변경',
            'pwd_days':       days,
            'pwd_warn':       days is not None and days >= 80,
        })
    union_depts = UnionDept.query.filter_by(use_yn='Y').order_by(UnionDept.sort_order).all()
    return render_template('admin_user.html',
        current_user=current_user,
        user_rows=user_rows,
        union_depts=union_depts,
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


@app.route('/admin/add-test-users')
@app.route('/admin/add-test-users/<int:batch>')
@level_required(0)
def add_test_users(batch=1):
    try:
        all_names = [
            '김철수','이영희','박민준','최수진','정다은','강동훈','윤서연','임재혁',
            '한지민','오승현','신예린','류성호','배지현','남궁민','황수빈','전태양',
            '조아름','서민기','권나연','홍길동','문선희','양재원','엄지혜','장현우',
            '송미래','고은별','구본철','안소희','노태준','마지훈','하승연','심재민',
            '국찬영','진수아','도현석','추민서','변성준','소지원','옥상훈','편리나'
        ]
        all_levels = ([1]*5 + [2]*10 + [3]*5 + [4]*20)
        dept_list  = ['D001','D002','D003','D004','D005','D006','D007','D008']
        union_list = ['U001','U002','U003','U004','U005']
        rank_list  = ['R01','R02','R03','R04','R05']

        if batch < 1 or batch > 4:
            return '배치 번호는 1~4 사이여야 합니다.'

        start = (batch - 1) * 10
        end   = start + 10
        names  = all_names[start:end]
        levels = all_levels[start:end]

        created = 0
        for i, (name, level) in enumerate(zip(names, levels), start + 1):
            emp_no = f'EMP{i:03d}'
            if User.query.filter_by(emp_no=emp_no).first():
                continue
            pwd_hash = bcrypt.hashpw(emp_no.encode(), bcrypt.gensalt(rounds=4)).decode()
            db.session.add(User(
                emp_no        = emp_no,
                emp_nm        = name,
                gender        = 'M' if i % 2 == 0 else 'F',
                email         = f'{emp_no.lower()}@yuanta.com',
                dept_cd       = dept_list[i % len(dept_list)],
                union_dept_cd = union_list[i % len(union_list)],
                rank_cd       = rank_list[i % len(rank_list)],
                emp_type_cd   = '01',
                user_level    = level,
                pwd_hash      = pwd_hash,
                pwd_chg_dt    = None,
                pwd_init_yn   = 'Y',
                use_yn        = 'Y'
            ))
            db.session.commit()
            created += 1

        total = User.query.filter(User.emp_no.like('EMP%')).count()
        next_batch = batch + 1
        if next_batch <= 4:
            return f'배치 {batch} 완료 ({created}개 생성, 누적 {total}개) → 다음: /admin/add-test-users/{next_batch}'
        else:
            return f'전체 완료! 총 {total}개 테스트 계정 생성됨 (비밀번호 = 사번)'

    except Exception as e:
        db.session.rollback()
        return f'오류: {str(e)}'

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
            conn.execute(db.text('ALTER TABLE "TB_USER" ALTER COLUMN position_cd TYPE VARCHAR(20)'))
            conn.execute(db.text('''CREATE TABLE IF NOT EXISTS "TB_VOTE_TARGET" (
                target_seq SERIAL PRIMARY KEY,
                vote_seq INTEGER NOT NULL,
                union_dept_cd VARCHAR(20) NOT NULL
            )'''))
            conn.execute(db.text('ALTER TABLE "TB_NOTICE" ADD COLUMN IF NOT EXISTS allow_comment VARCHAR(1) DEFAULT \'N\''))
            conn.execute(db.text('ALTER TABLE "TB_NOTICE" ADD COLUMN IF NOT EXISTS file_url VARCHAR(500)'))
            conn.execute(db.text('ALTER TABLE "TB_NOTICE" ADD COLUMN IF NOT EXISTS file_name VARCHAR(200)'))
            # TB_CONDO 스키마 변경: region_cd→brand_group_cd, brand_cd→resort_cd, 신규 컬럼 추가
            conn.execute(db.text('ALTER TABLE "TB_CONDO" ADD COLUMN IF NOT EXISTS brand_group_cd VARCHAR(20)'))
            conn.execute(db.text('ALTER TABLE "TB_CONDO" ADD COLUMN IF NOT EXISTS resort_cd VARCHAR(30)'))
            conn.execute(db.text('ALTER TABLE "TB_CONDO" ADD COLUMN IF NOT EXISTS image_url VARCHAR(500)'))
            conn.execute(db.text('ALTER TABLE "TB_CONDO" ADD COLUMN IF NOT EXISTS price_info TEXT'))
            conn.execute(db.text('ALTER TABLE "TB_CONDO" ADD COLUMN IF NOT EXISTS area_info VARCHAR(200)'))
            conn.execute(db.text('ALTER TABLE "TB_CONDO" ADD COLUMN IF NOT EXISTS extra_info TEXT'))
            conn.execute(db.text('ALTER TABLE "TB_CONDO" ADD COLUMN IF NOT EXISTS sort_order INTEGER DEFAULT 0'))
            conn.execute(db.text('''CREATE TABLE IF NOT EXISTS "TB_NOTICE_COMMENT" (
                comment_seq SERIAL PRIMARY KEY,
                notice_seq INTEGER NOT NULL,
                content TEXT NOT NULL,
                emp_no VARCHAR(20) NOT NULL,
                emp_nm VARCHAR(100),
                use_yn VARCHAR(1) DEFAULT \'Y\',
                reg_dt TIMESTAMP DEFAULT NOW()
            )'''))
            # 콘도 신규 3테이블 생성
            conn.execute(db.text('''CREATE TABLE IF NOT EXISTS "TB_CONDO_BRAND" (
                brand_id   SERIAL PRIMARY KEY,
                brand_name VARCHAR(50) NOT NULL,
                sort_order INT DEFAULT 0,
                use_yn     CHAR(1) DEFAULT 'Y'
            )'''))
            conn.execute(db.text('''CREATE TABLE IF NOT EXISTS "TB_CONDO_RESORT" (
                resort_id   SERIAL PRIMARY KEY,
                brand_id    INT NOT NULL REFERENCES "TB_CONDO_BRAND"(brand_id),
                resort_name VARCHAR(100) NOT NULL,
                sort_order  INT DEFAULT 0,
                use_yn      CHAR(1) DEFAULT 'Y'
            )'''))
            conn.execute(db.text('''CREATE TABLE IF NOT EXISTS "TB_CONDO_FACILITY" (
                facility_id   SERIAL PRIMARY KEY,
                resort_id     INT NOT NULL REFERENCES "TB_CONDO_RESORT"(resort_id),
                facility_name VARCHAR(100) NOT NULL,
                location      VARCHAR(200),
                description   TEXT,
                image_url     VARCHAR(500),
                area_info     VARCHAR(200),
                price_info    TEXT,
                extra_info    TEXT,
                sort_order    INT DEFAULT 0,
                use_yn        CHAR(1) DEFAULT 'Y',
                created_dt    TIMESTAMP DEFAULT NOW(),
                updated_dt    TIMESTAMP DEFAULT NOW()
            )'''))
            conn.execute(db.text('ALTER TABLE "TB_CONDO_RESERVE" ADD COLUMN IF NOT EXISTS facility_id INTEGER REFERENCES "TB_CONDO_FACILITY"(facility_id)'))
            conn.execute(db.text('''CREATE TABLE IF NOT EXISTS "TB_CONDO_ROOM" (
                room_id     SERIAL PRIMARY KEY,
                facility_id INTEGER,
                room_type   VARCHAR(100) NOT NULL,
                price       INTEGER DEFAULT 0,
                extra_info  TEXT,
                sort_order  INT DEFAULT 0,
                use_yn      CHAR(1) DEFAULT \'Y\'
            )'''))
            conn.execute(db.text('ALTER TABLE "TB_CONDO_RESERVE" ADD COLUMN IF NOT EXISTS room_id INTEGER'))

            # 스키마 변경만 (데이터 초기화 없음)
            conn.execute(db.text('ALTER TABLE "TB_CONDO_FACILITY" ADD COLUMN IF NOT EXISTS region_name VARCHAR(50)'))
            conn.execute(db.text('ALTER TABLE "TB_CONDO_RESERVE" ALTER COLUMN condo_seq DROP NOT NULL'))
            # TB_CONDO_ROOM 가격 4종 컬럼 추가
            conn.execute(db.text('ALTER TABLE "TB_CONDO_ROOM" ADD COLUMN IF NOT EXISTS price_offpeak INTEGER DEFAULT 0'))
            conn.execute(db.text('ALTER TABLE "TB_CONDO_ROOM" ADD COLUMN IF NOT EXISTS price_peak INTEGER DEFAULT 0'))
            conn.execute(db.text('ALTER TABLE "TB_CONDO_ROOM" ADD COLUMN IF NOT EXISTS price_holiday INTEGER DEFAULT 0'))
            conn.execute(db.text('ALTER TABLE "TB_CONDO_ROOM" ADD COLUMN IF NOT EXISTS price_extra INTEGER DEFAULT 0'))
            # TB_CONDO_RESERVE 비고 컬럼 추가
            conn.execute(db.text('ALTER TABLE "TB_CONDO_RESERVE" ADD COLUMN IF NOT EXISTS memo TEXT'))
            # TB_CONDO_SEASON 시즌 관리 테이블
            conn.execute(db.text('''CREATE TABLE IF NOT EXISTS "TB_CONDO_SEASON" (
                season_seq   SERIAL PRIMARY KEY,
                season_name  VARCHAR(100) NOT NULL,
                season_type  VARCHAR(20) NOT NULL,
                start_date   VARCHAR(5) NOT NULL,
                end_date     VARCHAR(5) NOT NULL,
                use_yn       CHAR(1) DEFAULT 'Y'
            )'''))
            # 도서 시스템 컬럼 추가
            conn.execute(db.text('ALTER TABLE "TB_BOOK" ADD COLUMN IF NOT EXISTS category VARCHAR(50)'))
            conn.execute(db.text('ALTER TABLE "TB_BOOK_REQUEST" ADD COLUMN IF NOT EXISTS req_year INTEGER'))
            conn.commit()
        return '마이그레이션 완료!'
    except Exception as e:
        return f'오류: {str(e)}'     
# ══════════════════════════════════════════════════════════
# Routes - 분회 관리
# ══════════════════════════════════════════════════════════

@app.route('/admin/user/export')
@level_required(1)
def admin_user_export():
    import csv, io
    users = User.query.filter_by(use_yn='Y').order_by(User.user_level, User.emp_no).all()
    rank_map = {c.code_cd: c.code_nm for c in Code.query.filter_by(code_grp='RANK').all()}
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['emp_no','emp_nm','gender','birth_dt','phone_no','email',
                     'dept_cd','union_dept_cd','emp_type_cd','rank_cd','user_level'])
    for u in users:
        writer.writerow([
            u.emp_no,
            u.emp_nm,
            u.gender or '',
            u.birth_dt.strftime('%Y-%m-%d') if u.birth_dt else '',
            u.phone_no or '',
            u.email or '',
            u.dept_cd or '',
            u.union_dept_cd or '',
            u.emp_type_cd or '',
            u.rank_cd or '',
            u.user_level if u.user_level is not None else 4,
        ])
    output.seek(0)
    from flask import Response
    return Response(
        '﻿' + output.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': 'attachment; filename=users.csv',
            'Cache-Control': 'no-store, no-cache, must-revalidate',
            'Pragma': 'no-cache',
        }
    )


@app.route('/admin/user/import', methods=['POST'])
@level_required(1)
def admin_user_import():
    import csv, io
    f = request.files.get('csv_file')
    if not f or not f.filename.endswith('.csv'):
        flash('CSV 파일을 선택해주세요.', 'error')
        return redirect(url_for('admin_user_list'))
    try:
        stream = io.StringIO(f.stream.read().decode('utf-8-sig'))
        reader = csv.DictReader(stream)
        rows = list(reader)

        inserted = updated = skipped = 0
        for row in rows:
            emp_no = row.get('emp_no', '').strip()
            emp_nm = row.get('emp_nm', '').strip()
            if not emp_no or not emp_nm:
                skipped += 1
                continue

            gender = row.get('gender', 'M').strip()
            gender = 'M' if gender in ('M', '남') else 'F'

            def parse_date(val):
                if not val or not val.strip():
                    return None
                val = val.strip().replace('/', '-').replace('.', '-')
                for fmt in ('%Y-%m-%d', '%Y%m%d'):
                    try:
                        return datetime.strptime(val, fmt).date()
                    except ValueError:
                        continue
                return None

            level_str = row.get('user_level', '4').strip()
            try:
                level = int(level_str) if level_str else 4
            except ValueError:
                level = 4

            existing = User.query.filter_by(emp_no=emp_no).first()
            if existing:
                # 기존 사용자 업데이트 (union_dept_cd는 공란이면 기존값 유지)
                existing.emp_nm      = emp_nm
                existing.gender      = gender
                existing.birth_dt    = parse_date(row.get('birth_dt', ''))
                existing.phone_no    = row.get('phone_no', '').strip() or existing.phone_no
                existing.email       = row.get('email', '').strip() or existing.email
                existing.dept_cd     = row.get('dept_cd', '').strip() or existing.dept_cd
                if row.get('union_dept_cd', '').strip():
                    existing.union_dept_cd = row.get('union_dept_cd', '').strip()
                existing.emp_type_cd = row.get('emp_type_cd', '').strip() or existing.emp_type_cd
                existing.rank_cd     = row.get('rank_cd', '').strip() or existing.rank_cd
                existing.user_level  = level
                existing.mod_dt      = datetime.now()
                if existing.use_yn == 'N':
                    existing.use_yn = 'Y'
                updated += 1
            else:
                # 신규 사용자 INSERT
                pwd_hash = bcrypt.hashpw(emp_no.encode(), bcrypt.gensalt()).decode()
                db.session.add(User(
                    emp_no        = emp_no,
                    emp_nm        = emp_nm,
                    gender        = gender,
                    birth_dt      = parse_date(row.get('birth_dt', '')),
                    phone_no      = row.get('phone_no', '').strip() or None,
                    email         = row.get('email', '').strip() or None,
                    dept_cd       = row.get('dept_cd', '').strip() or None,
                    union_dept_cd = row.get('union_dept_cd', '').strip() or None,
                    emp_type_cd   = row.get('emp_type_cd', '').strip() or None,
                    rank_cd       = row.get('rank_cd', '').strip() or None,
                    user_level    = level,
                    pwd_hash      = pwd_hash,
                    pwd_init_yn   = 'Y',
                    pwd_chg_dt    = None,
                    use_yn        = 'Y',
                ))
                inserted += 1

        db.session.commit()
        flash(f'CSV 업로드 완료! 신규 {inserted}명 등록, {updated}명 업데이트, {skipped}건 건너뜀.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'오류: {str(e)}', 'error')
    return redirect(url_for('admin_user_list'))


@app.route('/admin/union-dept')
@level_required(0)
def admin_union_dept():
    current_user = get_current_user()
    union_depts  = UnionDept.query.filter_by(use_yn='Y').order_by(UnionDept.sort_order).all()
    dept_list    = []
    for d in union_depts:
        members = User.query.filter_by(union_dept_cd=d.union_dept_cd, use_yn='Y').all()
        # 소속 회사 부서 목록 (중복 제거)
        comp_depts = list({u.dept_cd for u in members if u.dept_cd})
        dept_list.append({
            'cd':         d.union_dept_cd,
            'nm':         d.union_dept_nm,
            'sort_order': d.sort_order,
            'member_cnt': len(members),
            'comp_depts': comp_depts,
        })
    # 미배정 회사 부서
    all_comp_depts = CompDept.query.filter_by(use_yn='Y').order_by(CompDept.sort_order).all()
    return render_template('admin_union_dept.html',
        current_user=current_user,
        dept_list=dept_list,
        all_comp_depts=all_comp_depts,
        active_menu='admin_union_dept'
    )

@app.route('/admin/union-dept/save', methods=['POST'])
@level_required(0)
def admin_union_dept_save():
    action        = request.form.get('action')
    union_dept_cd = request.form.get('union_dept_cd', '').strip()
    union_dept_nm = request.form.get('union_dept_nm', '').strip()

    if action == 'add':
        # 삭제된 것 포함 전체 조회
        existing = UnionDept.query.filter_by(union_dept_cd=union_dept_cd).first()
        if existing and existing.use_yn == 'Y':
            flash('이미 존재하는 분회 코드입니다.')
        elif existing and existing.use_yn == 'N':
            # 삭제됐던 분회 재활성화
            existing.union_dept_nm = union_dept_nm
            existing.sort_order    = int(request.form.get('sort_order', 0))
            existing.use_yn        = 'Y'
            flash(f'{union_dept_nm} 분회가 등록되었습니다.')
        else:
            db.session.add(UnionDept(
                union_dept_cd=union_dept_cd,
                union_dept_nm=union_dept_nm,
                sort_order=int(request.form.get('sort_order', 0))
            ))
            flash(f'{union_dept_nm} 분회가 등록되었습니다.')

    elif action == 'edit':
        dept = UnionDept.query.filter_by(union_dept_cd=union_dept_cd).first()
        if dept:
            dept.union_dept_nm = union_dept_nm
            dept.sort_order    = int(request.form.get('sort_order', dept.sort_order))
            flash(f'{union_dept_nm} 분회 정보가 수정되었습니다.')

    elif action == 'delete':
        dept = UnionDept.query.filter_by(union_dept_cd=union_dept_cd).first()
        if dept:
            # 소속 인원 분회 해제
            User.query.filter_by(union_dept_cd=union_dept_cd).update({'union_dept_cd': None})
            dept.use_yn = 'N'
            flash(f'{dept.union_dept_nm} 분회가 삭제되었습니다.')

    elif action == 'assign':
        # 회사 부서 → 분회 일괄 배정
        dept_cd       = request.form.get('dept_cd', '').strip()
        target_dept_cd = request.form.get('target_union_dept_cd', '').strip()
        cnt = User.query.filter_by(dept_cd=dept_cd, use_yn='Y').update({'union_dept_cd': target_dept_cd})
        flash(f'{dept_cd} 부서 {cnt}명을 {target_dept_cd} 분회에 배정했습니다.')

    db.session.commit()
    return redirect(url_for('admin_union_dept'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)