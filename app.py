"""
UnionBBS - Flask 메인 애플리케이션
SQLite (테스트) / Oracle (운영) 전환 가능
"""
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date, timedelta
from functools import wraps
import bcrypt
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-prod')

# ── DB 설정 ──────────────────────────────────────────────
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL', 'sqlite:///unionbbs.db'
)
# Oracle 전환 시:
# app.config['SQLALCHEMY_DATABASE_URI'] = 'oracle+oracledb://user:pw@host:1521/service'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

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
    pwd_chg_dt    = db.Column(db.Date)                          # 마지막 비밀번호 변경일
    pwd_init_yn   = db.Column(db.String(1), default='Y')        # Y=초기비번(강제변경 필요)
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
    mod_dt      = db.Column(db.DateTime)
    mod_user    = db.Column(db.String(20))

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
    board_seq = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title     = db.Column(db.String(200), nullable=False)
    content   = db.Column(db.Text, nullable=False)
    view_cnt  = db.Column(db.Integer, default=0)
    like_cnt  = db.Column(db.Integer, default=0)
    emp_no    = db.Column(db.String(20), nullable=False)
    use_yn    = db.Column(db.String(1), default='Y')
    reg_dt    = db.Column(db.DateTime, default=datetime.now)
    mod_dt    = db.Column(db.DateTime)

class BoardComment(db.Model):
    __tablename__ = 'TB_BOARD_COMMENT'
    comment_seq = db.Column(db.Integer, primary_key=True, autoincrement=True)
    board_seq   = db.Column(db.Integer, db.ForeignKey('TB_BOARD.board_seq'), nullable=False)
    content     = db.Column(db.Text, nullable=False)
    emp_no      = db.Column(db.String(20), nullable=False)
    use_yn      = db.Column(db.String(1), default='Y')
    reg_dt      = db.Column(db.DateTime, default=datetime.now)

class Condo(db.Model):
    __tablename__ = 'TB_CONDO'
    condo_seq   = db.Column(db.Integer, primary_key=True, autoincrement=True)
    condo_nm    = db.Column(db.String(100), nullable=False)
    region_cd   = db.Column(db.String(10))   # 대분류: METRO/GANGWON/CHUNGCHEONG/JEOLLA/GYEONGSANG
    brand_cd    = db.Column(db.String(10))   # 중분류: SONO/HANWHA/LOTTE/ANTO
    location    = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    total_room  = db.Column(db.Integer, default=0)
    use_yn      = db.Column(db.String(1), default='Y')
    rooms       = db.relationship('CondoRoom', backref='condo', lazy=True)

class CondoRoom(db.Model):
    __tablename__ = 'TB_CONDO_ROOM'
    room_seq    = db.Column(db.Integer, primary_key=True, autoincrement=True)
    condo_seq   = db.Column(db.Integer, db.ForeignKey('TB_CONDO.condo_seq'), nullable=False)
    room_type   = db.Column(db.String(50), nullable=False)   # 객실유형명 (예: 스탠다드, 디럭스)
    capacity    = db.Column(db.Integer, default=4)           # 수용 인원
    description = db.Column(db.Text)                         # 객실 상세 설명
    amenities   = db.Column(db.String(500))                  # 편의시설 (콤마구분)
    total_cnt   = db.Column(db.Integer, default=1)           # 총 객실 수
    avail_cnt   = db.Column(db.Integer, default=1)           # 예약 가능 객실
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

        # 비밀번호 검증 (bcrypt)
        try:
            pw_match = bcrypt.checkpw(password.encode(), user.pwd_hash.encode())
        except Exception:
            pw_match = (password == emp_no)  # mock: 최초 비밀번호 = 사번

        if pw_match:
            user.pwd_fail_cnt = 0
            db.session.commit()
            session['emp_no']     = user.emp_no
            session['emp_nm']     = user.emp_nm
            session['user_level'] = user.user_level
            session['user_seq']   = user.user_seq

            # 초기 비밀번호(사번) 강제 변경
            if user.pwd_init_yn == 'Y':
                session['force_pwd_change'] = True
                flash('초기 비밀번호를 반드시 변경해야 합니다.', 'warning')
                return redirect(url_for('force_pwd_change'))

            # 90일 만료 경고
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

    # 오늘 일정
    today_start = datetime.combine(date.today(), datetime.min.time())
    today_end   = datetime.combine(date.today(), datetime.max.time())
    today_schedule = Schedule.query.filter(
        Schedule.start_dt >= today_start,
        Schedule.start_dt <= today_end,
        Schedule.use_yn == 'Y'
    ).order_by(Schedule.start_dt).all()

    # 복지 카운트
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
        active_menu='notice'
    )

@app.route('/notice/view/<int:notice_seq>')
@login_required
def notice_view(notice_seq):
    current_user = get_current_user()
    item = Notice.query.get_or_404(notice_seq)
    item.view_cnt = (item.view_cnt or 0) + 1
    db.session.commit()
    return render_template('notice.html',
        current_user=current_user,
        notice_list=Notice.query.filter_by(use_yn='Y').order_by(Notice.reg_dt.desc()).all(),
        selected_notice=item,
        active_menu='notice'
    )

@app.route('/notice/save', methods=['POST'])
@level_required(1)
def notice_save():
    current_user = get_current_user()
    notice = Notice(
        notice_type = request.form.get('notice_type'),
        title       = request.form.get('title'),
        content     = request.form.get('content'),
        is_push     = request.form.get('send_mail', 'N'),
        reg_user    = current_user.emp_no
    )
    db.session.add(notice)

    # 일정 연동 처리
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
    keyword      = request.args.get('q', '')
    query        = Board.query.filter_by(use_yn='Y')
    if keyword:
        query = query.filter(
            Board.title.contains(keyword) | Board.content.contains(keyword)
        )
    posts = query.order_by(Board.reg_dt.desc()).all()
    return render_template('board.html',
        current_user=current_user,
        post_list=posts,
        active_menu='board'
    )

@app.route('/board/save', methods=['POST'])
@login_required
def board_save():
    current_user = get_current_user()
    post = Board(
        title   = request.form.get('title'),
        content = request.form.get('content'),
        emp_no  = current_user.emp_no
    )
    db.session.add(post)
    db.session.commit()
    return redirect(url_for('board'))

@app.route('/board/comment/save', methods=['POST'])
@login_required
def board_comment_save():
    current_user = get_current_user()
    comment = BoardComment(
        board_seq = request.form.get('board_seq'),
        content   = request.form.get('content'),
        emp_no    = current_user.emp_no
    )
    db.session.add(comment)
    db.session.commit()
    return redirect(url_for('board'))


# ══════════════════════════════════════════════════════════
# Routes - 투표
# ══════════════════════════════════════════════════════════

@app.route('/vote')
@login_required
def vote():
    current_user  = get_current_user()
    active_votes  = Vote.query.filter_by(vote_status='ONGOING', use_yn='Y').all()
    archive_votes = Vote.query.filter_by(vote_status='CLOSED', use_yn='Y').all()

    # 각 투표에 항목 및 참여 여부 추가
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

    # 비밀번호 재확인
    try:
        pw_match = bcrypt.checkpw(auth_pwd.encode(), current_user.pwd_hash.encode())
    except Exception:
        pw_match = (auth_pwd == current_user.emp_no)

    if not pw_match:
        flash('비밀번호 인증에 실패했습니다.')
        return redirect(url_for('vote'))

    # 중복 투표 확인
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
    # update parent condo total_room
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
    from datetime import timedelta
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
    current_user = get_current_user()
    executives   = User.query.filter_by(user_level=1, use_yn='Y').all()
    delegates    = User.query.filter_by(user_level=2, use_yn='Y').all()
    chairman     = User.query.filter_by(user_level=0, use_yn='Y').first()
    auditors     = User.query.filter_by(user_level=2, use_yn='Y').limit(2).all()  # 회계감사: 별도 구분 컬럼 추가 전 임시
    # 조합소개 설정 (TB_CODE 또는 별도 설정 테이블에서 불러올 수 있음 - 현재는 기본값)
    slogan_text  = None  # TODO: 설정 테이블 연동
    greeting_text = None
    senior_vice  = None
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
    # TODO: 설정 테이블(TB_CONFIG 등) 생성 후 실제 저장 로직 구현
    # 현재는 flash만 표시
    section = request.form.get('section')
    flash(f'저장되었습니다. (section: {section}) — 설정 테이블 연동 후 영구 반영됩니다.')
    return redirect(url_for('about'))




# ══════════════════════════════════════════════════════════
# Routes - 프로필
# ══════════════════════════════════════════════════════════

@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def profile_edit():
    current_user = get_current_user()
    if request.method == 'POST':
        new_pwd    = request.form.get('new_password', '')
        cur_pwd    = request.form.get('current_password', '')

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
# Routes - 비밀번호 강제 변경 (최초 로그인)
# ══════════════════════════════════════════════════════════

@app.route('/pwd/force-change', methods=['GET', 'POST'])
@login_required
def force_pwd_change():
    """최초 로그인(초기비번) 시 강제 변경 페이지"""
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
            current_user.pwd_hash     = hashed
            current_user.pwd_chg_dt   = date.today()
            current_user.pwd_init_yn  = 'N'   # 강제변경 완료
            current_user.mod_dt       = datetime.now()
            db.session.commit()
            session.pop('force_pwd_change', None)
            flash('비밀번호가 변경되었습니다. 서비스를 이용하실 수 있습니다.', 'success')
            return redirect(url_for('main'))

    return render_template('force_pwd_change.html', current_user=current_user)


@app.route('/admin/user/reset-pwd', methods=['POST'])
@level_required(1)
def admin_reset_pwd():
    """관리자: 특정 사용자 비밀번호 초기화 (사번으로 리셋)"""
    target_emp_no = request.form.get('emp_no', '').strip()
    target_user   = User.query.filter_by(emp_no=target_emp_no, use_yn='Y').first()

    if not target_user:
        return jsonify({'ok': False, 'msg': f'사번 {target_emp_no} 사용자를 찾을 수 없습니다.'})

    hashed = bcrypt.hashpw(target_emp_no.encode(), bcrypt.gensalt()).decode()
    target_user.pwd_hash    = hashed
    target_user.pwd_init_yn = 'Y'          # 다음 로그인 시 강제변경 요구
    target_user.pwd_chg_dt  = None
    target_user.pwd_fail_cnt = 0
    target_user.acct_lock_yn = 'N'         # 잠금도 함께 해제
    target_user.mod_dt       = datetime.now()
    db.session.commit()

    return jsonify({'ok': True, 'msg': f'{target_user.emp_nm}({target_emp_no}) 비밀번호가 사번으로 초기화되었습니다.'})


@app.route('/admin/user/list')
@level_required(1)
def admin_user_list():
    """관리자: 사용자 목록 조회 (비번 초기화 포함)"""
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
# DB 초기화
# ══════════════════════════════════════════════════════════

def init_db():
    """DB 테이블 생성 + 테스트용 목데이터 삽입 (최초 1회)"""
    db.create_all()

    if User.query.first():
        print("✅ DB 이미 초기화됨 - 목데이터 삽입 스킵")
        return

    print("📦 목데이터 삽입 중...")

    def make_pw(raw):
        return bcrypt.hashpw(raw.encode(), bcrypt.gensalt()).decode()

    # ── 공통코드 ──────────────────────────────────
    db.session.add_all([
        Code(code_grp='EMP_TYPE', code_cd='01', code_nm='종합직', sort_order=1),
        Code(code_grp='EMP_TYPE', code_cd='02', code_nm='일반직', sort_order=2),
        Code(code_grp='EMP_TYPE', code_cd='03', code_nm='기술직', sort_order=3),
        Code(code_grp='RANK', code_cd='R01', code_nm='부장',  sort_order=1),
        Code(code_grp='RANK', code_cd='R02', code_nm='차장',  sort_order=2),
        Code(code_grp='RANK', code_cd='R03', code_nm='과장',  sort_order=3),
        Code(code_grp='RANK', code_cd='R04', code_nm='대리',  sort_order=4),
        Code(code_grp='RANK', code_cd='R05', code_nm='사원',  sort_order=5),
    ])

    # ── 조합 분회 ─────────────────────────────────
    db.session.add_all([
        UnionDept(union_dept_cd='UD01', union_dept_nm='서울본사분회',   sort_order=1),
        UnionDept(union_dept_cd='UD02', union_dept_nm='강남지점분회',   sort_order=2),
        UnionDept(union_dept_cd='UD03', union_dept_nm='부산지역분회',   sort_order=3),
        UnionDept(union_dept_cd='UD04', union_dept_nm='대구지역분회',   sort_order=4),
    ])

    # ── 사용자 (비밀번호 = 사번) ──────────────────
    # LV0:관리자 / LV1:집행위원 / LV2:대의원 / LV3:분회장 / LV4:조합원
    users = [
        User(emp_no='EMP001', emp_nm='김관리', gender='M',
             birth_dt=date(1975, 3, 15), phone_no='010-1111-0001',
             email='admin@yuanta.com', dept_cd='D001', union_dept_cd='UD01',
             emp_type_cd='01', rank_cd='R01', user_level=0,
             term_start=date(2024,1,1), term_end=date(2025,12,31),
             pwd_hash=make_pw('EMP001'), pwd_chg_dt=date.today(), pwd_init_yn='N', use_yn='Y'),
        User(emp_no='EMP002', emp_nm='이집행', gender='M',
             birth_dt=date(1978, 6, 20), phone_no='010-1111-0002',
             email='exec@yuanta.com', dept_cd='D002', union_dept_cd='UD01',
             emp_type_cd='01', rank_cd='R02', user_level=1,
             term_start=date(2024,1,1), term_end=date(2025,12,31),
             pwd_hash=make_pw('EMP002'), pwd_init_yn='Y', use_yn='Y'),
        User(emp_no='EMP003', emp_nm='박대의', gender='F',
             birth_dt=date(1982, 9, 5), phone_no='010-1111-0003',
             email='delegate@yuanta.com', dept_cd='D003', union_dept_cd='UD02',
             emp_type_cd='01', rank_cd='R03', user_level=2,
             term_start=date(2024,1,1), term_end=date(2025,12,31),
             pwd_hash=make_pw('EMP003'), pwd_init_yn='Y', use_yn='Y'),
        User(emp_no='EMP004', emp_nm='최분회', gender='M',
             birth_dt=date(1980, 12, 1), phone_no='010-1111-0004',
             email='chair@yuanta.com', dept_cd='D004', union_dept_cd='UD03',
             emp_type_cd='02', rank_cd='R03', user_level=3,
             term_start=date(2024,1,1), term_end=date(2025,12,31),
             pwd_hash=make_pw('EMP004'), pwd_init_yn='Y', use_yn='Y'),
        User(emp_no='EMP005', emp_nm='정조합', gender='F',
             birth_dt=date(1990, 4, 18), phone_no='010-1111-0005',
             email='member@yuanta.com', dept_cd='D005', union_dept_cd='UD02',
             emp_type_cd='01', rank_cd='R04', user_level=4,
             pwd_hash=make_pw('EMP005'), pwd_init_yn='Y', use_yn='Y'),
        User(emp_no='EMP006', emp_nm='한조합', gender='M',
             birth_dt=date(1993, 7, 22), phone_no='010-1111-0006',
             email='member2@yuanta.com', dept_cd='D003', union_dept_cd='UD01',
             emp_type_cd='01', rank_cd='R05', user_level=4,
             pwd_hash=make_pw('EMP006'), pwd_init_yn='Y', use_yn='Y'),
    ]
    db.session.add_all(users)
    db.session.flush()

    # ── 공지사항 ──────────────────────────────────
    db.session.add_all([
        Notice(notice_type='FLASH', title='[노조속보] 2025년 임금협상 잠정합의 안내',
               content='2025년 임금협상 잠정합의가 완료되었습니다. 상세 내용은 첨부 파일을 참고해주시기 바랍니다.',
               is_push='Y', view_cnt=128, reg_user='EMP001'),
        Notice(notice_type='SCHEDULE', title='3월 분회장 간담회 일정 안내',
               content='3월 분회장 정기 간담회가 아래 일정으로 개최됩니다. 일시: 2025년 3월 20일(목) 오후 2시 / 장소: 본사 대회의실 2층',
               view_cnt=45, reg_user='EMP001'),
        Notice(notice_type='FLASH', title='[노조속보] 4월 대의원 대회 소집 공고',
               content='정기 대의원 대회 소집을 공고합니다.',
               view_cnt=67, reg_user='EMP002'),
        Notice(notice_type='ELECTION', title='제15대 집행위원회 선거 공고',
               content='제15대 집행위원회 임원 선거를 아래와 같이 공고합니다. 선거일: 2025년 5월 2일(금) / 후보등록: 4월 14일 ~ 4월 18일',
               view_cnt=203, reg_user='EMP001'),
        Notice(notice_type='SCHEDULE', title='2025 노동절 기념 행사 안내',
               content='5.1 노동절을 맞아 기념 행사를 진행합니다. 전 조합원의 참여를 부탁드립니다.',
               view_cnt=89, reg_user='EMP002'),
    ])

    # ── 일정 ──────────────────────────────────────
    db.session.add_all([
        Schedule(title='정기 대의원 대회', content='2025년 1분기 정기 대의원 대회',
                 start_dt=datetime(2025,3,20,14,0), end_dt=datetime(2025,3,20,17,0),
                 location='본사 대회의실 2층', schedule_type='MEETING', reg_user='EMP001'),
        Schedule(title='임금협상 교섭위원회',
                 start_dt=datetime(2025,4,5,10,0), end_dt=datetime(2025,4,5,12,0),
                 location='14층 소회의실', schedule_type='NEGOTIATION', reg_user='EMP001'),
        Schedule(title='노동절 기념 행사',
                 start_dt=datetime(2025,5,1,11,0), end_dt=datetime(2025,5,1,15,0),
                 location='여의도공원 잔디광장', schedule_type='EVENT', reg_user='EMP002'),
    ])

    # ── 게시판 ────────────────────────────────────
    db.session.add_all([
        Board(title='신입 조합원 가입 인사드립니다', emp_no='EMP005',
              content='안녕하세요! 이번에 조합에 가입하게 된 정조합입니다. 잘 부탁드립니다.', view_cnt=24),
        Board(title='콘도 이용 후기 - 설악산 한화리조트', emp_no='EMP006',
              content='지난 주 설악산 한화리조트 이용했는데 정말 좋았습니다. 다들 이용해보세요!', view_cnt=51),
        Board(title='도서 추천 - 노동법 관련 좋은 책 있으면 알려주세요', emp_no='EMP003',
              content='노동법 공부 하려는데 좋은 도서 추천 부탁드립니다.', view_cnt=18),
    ])

    # ── 투표 ──────────────────────────────────────
    vote = Vote(
        title='2025년 임금인상 잠정합의안 찬반 투표',
        content='2025년 임금협상 잠정합의안에 대한 전체 조합원 찬반 투표입니다. 찬성: 기본급 3.5% 인상 + 복지포인트 10만원 증액 / 반대: 재협상 요구',
        start_dt=datetime(2025,3,10,9,0),
        end_dt=datetime(2025,3,25,18,0),
        vote_status='OPEN',
        total_cnt=6,
        vote_cnt=3,
        reg_user='EMP001'
    )
    db.session.add(vote)
    db.session.flush()
    db.session.add_all([
        VoteItem(vote_seq=vote.vote_seq, item_nm='찬성', item_cnt=2, sort_order=1),
        VoteItem(vote_seq=vote.vote_seq, item_nm='반대', item_cnt=1, sort_order=2),
    ])

    # ── 콘도 시설 ─────────────────────────────────
    condos = [
        Condo(condo_nm='설악산 한화리조트', region_cd='GANGWON', brand_cd='HANWHA',
              location='강원 속초시', description='설악산 인근 4성급 리조트. 케이블카 5분 거리.', total_room=5),
        Condo(condo_nm='제주 소노벨', region_cd='JEOLLA', brand_cd='SONO',
              location='제주 서귀포시', description='제주 남쪽 바다 전망 프리미엄 콘도', total_room=3),
        Condo(condo_nm='지리산 대명비발디파크', region_cd='GYEONGSANG', brand_cd='LOTTE',
              location='경남 함양군', description='지리산 자락 휴양 콘도. 온천시설 완비.', total_room=4),
        Condo(condo_nm='수원 소노캄', region_cd='METRO', brand_cd='SONO',
              location='경기 수원시', description='수도권 접근 편리. 수원화성 인근.', total_room=3),
    ]
    db.session.add_all(condos)
    db.session.flush()

    # 객실 유형 등록
    room_data = [
        CondoRoom(condo_seq=condos[0].condo_seq, room_type='스탠다드룸', capacity=4,
                  description='기본형 객실. 더블베드 1개 + 소파베드 포함.', amenities='TV,냉장고,에어컨,욕조', total_cnt=3, avail_cnt=3),
        CondoRoom(condo_seq=condos[0].condo_seq, room_type='패밀리스위트', capacity=6,
                  description='가족형 대형 객실. 침대 2개 + 거실 분리형.', amenities='TV,냉장고,에어컨,욕조,주방', total_cnt=2, avail_cnt=2),
        CondoRoom(condo_seq=condos[1].condo_seq, room_type='오션뷰 디럭스', capacity=4,
                  description='바다 전망 프리미엄 객실. 발코니 포함.', amenities='TV,냉장고,에어컨,욕조,발코니', total_cnt=2, avail_cnt=2),
        CondoRoom(condo_seq=condos[1].condo_seq, room_type='마운틴뷰 스탠다드', capacity=4,
                  description='한라산 전망 기본 객실.', amenities='TV,냉장고,에어컨', total_cnt=1, avail_cnt=1),
        CondoRoom(condo_seq=condos[2].condo_seq, room_type='온천 스위트', capacity=4,
                  description='개인 온천 욕조 포함 프리미엄 객실.', amenities='TV,냉장고,에어컨,노천탕', total_cnt=2, avail_cnt=2),
        CondoRoom(condo_seq=condos[2].condo_seq, room_type='스탠다드룸', capacity=4,
                  description='기본형 객실.', amenities='TV,냉장고,에어컨', total_cnt=2, avail_cnt=2),
        CondoRoom(condo_seq=condos[3].condo_seq, room_type='시티뷰 스탠다드', capacity=4,
                  description='수원 시내 전망 기본 객실.', amenities='TV,냉장고,에어컨', total_cnt=3, avail_cnt=3),
    ]
    db.session.add_all(room_data)

    # ── 도서 ──────────────────────────────────────
    books = [
        Book(title='노동법 실무', author='김노동', publisher='법문사', isbn='9788901001', total_cnt=2, avail_cnt=1, is_new='Y'),
        Book(title='단체교섭의 이론과 실제', author='박교섭', publisher='노동출판', isbn='9788901002', total_cnt=1, avail_cnt=1),
        Book(title='조직문화 혁신', author='이문화', publisher='경영출판사', isbn='9788901003', total_cnt=1, avail_cnt=0),
        Book(title='협상의 기술', author='최협상', publisher='비즈북스', isbn='9788901004', total_cnt=2, avail_cnt=2, is_new='Y'),
        Book(title='직장인 법률 상식', author='정법률', publisher='법률신문사', isbn='9788901005', total_cnt=1, avail_cnt=1),
    ]
    db.session.add_all(books)

    db.session.commit()
    print("✅ 목데이터 삽입 완료!")
    print("=" * 40)
    print("테스트 계정 (비밀번호 = 사번)")
    print("  EMP001 / EMP001  →  관리자 (LV0)")
    print("  EMP002 / EMP002  →  집행위원 (LV1)")
    print("  EMP003 / EMP003  →  대의원 (LV2)")
    print("  EMP004 / EMP004  →  분회장 (LV3)")
    print("  EMP005 / EMP005  →  조합원 (LV4)")
    print("=" * 40)


if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
