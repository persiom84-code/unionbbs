"""
migrate.py  ·  유안타증권 노동조합 UnionBBS
================================================================
기존 인사 DB → TB_USER 마이그레이션 스크립트

사용법:
    python migrate.py --help
    python migrate.py preview            # 변환 결과만 미리보기 (DB 반영 없음)
    python migrate.py run                # 실제 삽입 실행
    python migrate.py run --reset        # 기존 TB_USER 전부 삭제 후 재삽입
    python migrate.py reset-pwd EMP001   # 특정 사번 비밀번호만 초기화
    python migrate.py condo              # TB_CONDO 컬럼 변경 + 초기 데이터 INSERT
    python migrate.py condo_reset        # TB_CONDO 데이터만 초기화 후 재INSERT

입력 파일:
    migration_input.csv  (이 파일과 같은 디렉터리에 위치)

CSV 컬럼 순서 (헤더 필수):
    emp_no, emp_nm, gender, birth_dt, phone_no, email,
    dept_cd, union_dept_cd, emp_type_cd, rank_cd, user_level

    * user_level: 0=관리자 1=집행위원 2=대의원 3=분회장 4=조합원 5=명예 99=비조합원
    * 없는 컬럼은 비워두면 기본값 적용
    * 초기 비밀번호는 모두 사번으로 설정되며, 최초 로그인 시 강제 변경 요구

결과:
    - migration_result.csv  (성공/실패 상세 결과)
================================================================
"""

import csv
import sys
import os
import argparse
from datetime import date, datetime

# Flask 앱 컨텍스트 로드
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import app, db, User, CondoBrand, CondoResort, CondoFacility
import bcrypt


# ──────────────────────────────────────────────
# 헬퍼
# ──────────────────────────────────────────────

def make_pw(raw: str) -> str:
    """bcrypt 해시 생성"""
    return bcrypt.hashpw(raw.encode(), bcrypt.gensalt()).decode()


def parse_date(val: str):
    """YYYY-MM-DD 또는 YYYYMMDD → date 객체"""
    if not val or not val.strip():
        return None
    val = val.strip().replace('/', '-').replace('.', '-')
    for fmt in ('%Y-%m-%d', '%Y%m%d'):
        try:
            return datetime.strptime(val, fmt).date()
        except ValueError:
            continue
    return None


LEVEL_NAMES = {
    '0': '관리자', '1': '집행위원', '2': '대의원',
    '3': '분회장', '4': '조합원', '5': '명예조합원', '99': '비조합원'
}

INPUT_FILE  = os.path.join(os.path.dirname(__file__), 'migration_input.csv')
RESULT_FILE = os.path.join(os.path.dirname(__file__), 'migration_result.csv')


# ──────────────────────────────────────────────
# CSV 읽기 및 변환
# ──────────────────────────────────────────────

def load_csv() -> list[dict]:
    if not os.path.exists(INPUT_FILE):
        print(f"❌ 입력 파일 없음: {INPUT_FILE}")
        print("   migration_input.csv 파일을 준비해주세요.")
        print("   필수 컬럼: emp_no, emp_nm, gender")
        sys.exit(1)

    rows = []
    with open(INPUT_FILE, encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=2):  # 2행부터 (1행=헤더)
            rows.append({'_line': i, **{k.strip(): v.strip() for k, v in row.items()}})
    return rows


def validate_row(row: dict) -> tuple[bool, str]:
    """기본 유효성 검사 → (통과여부, 에러메시지)"""
    emp_no = row.get('emp_no', '').strip()
    emp_nm = row.get('emp_nm', '').strip()
    gender = row.get('gender', '').strip().upper()

    if not emp_no:
        return False, '사번(emp_no) 누락'
    if not emp_nm:
        return False, '이름(emp_nm) 누락'
    if gender not in ('M', 'F', '남', '여', ''):
        return False, f'성별값 오류: {gender} (M/F 또는 남/여)'

    level = row.get('user_level', '4').strip()
    if level not in LEVEL_NAMES:
        return False, f'user_level 값 오류: {level} (0~5,99 중 하나)'

    return True, ''


def row_to_user(row: dict) -> User:
    emp_no = row['emp_no'].strip()
    gender = row.get('gender', 'M').strip()
    gender = 'M' if gender in ('M', '남') else 'F'
    level  = int(row.get('user_level', '4').strip() or '4')

    return User(
        emp_no        = emp_no,
        emp_nm        = row['emp_nm'].strip(),
        gender        = gender,
        birth_dt      = parse_date(row.get('birth_dt', '')),
        phone_no      = row.get('phone_no', '').strip() or None,
        email         = row.get('email', '').strip() or None,
        dept_cd       = row.get('dept_cd', '').strip() or None,
        union_dept_cd = row.get('union_dept_cd', '').strip() or None,
        emp_type_cd   = row.get('emp_type_cd', '').strip() or None,
        rank_cd       = row.get('rank_cd', '').strip() or None,
        user_level    = level,
        pwd_hash      = make_pw(emp_no),   # 초기 비밀번호 = 사번
        pwd_init_yn   = 'Y',               # 최초 로그인 시 강제 변경
        pwd_chg_dt    = None,
        use_yn        = 'Y',
    )


# ──────────────────────────────────────────────
# 커맨드: preview
# ──────────────────────────────────────────────

def cmd_preview():
    rows = load_csv()
    print(f"\n{'='*60}")
    print(f"  📋 마이그레이션 미리보기  ({len(rows)}행)")
    print(f"{'='*60}")
    print(f"{'행':<5} {'사번':<12} {'이름':<10} {'레벨':<10} {'상태'}")
    print('-' * 60)

    ok_cnt = err_cnt = 0
    for row in rows:
        valid, msg = validate_row(row)
        level_nm = LEVEL_NAMES.get(row.get('user_level', '4'), '?')
        if valid:
            ok_cnt += 1
            status = '✅ OK'
        else:
            err_cnt += 1
            status = f'❌ {msg}'
        print(f"{row['_line']:<5} {row.get('emp_no',''):<12} {row.get('emp_nm',''):<10} {level_nm:<10} {status}")

    print('-' * 60)
    print(f"  삽입 예정: {ok_cnt}건   오류: {err_cnt}건")
    if err_cnt > 0:
        print(f"\n  ⚠  오류 항목은 건너뜁니다. CSV 수정 후 다시 실행하세요.")
    print()


# ──────────────────────────────────────────────
# 커맨드: run
# ──────────────────────────────────────────────

def cmd_run(reset: bool = False):
    rows = load_csv()

    with app.app_context():
        if reset:
            deleted = User.query.delete()
            db.session.commit()
            print(f"🗑  기존 TB_USER {deleted}건 삭제 완료")

        results = []
        ok_cnt = skip_cnt = err_cnt = 0

        for row in rows:
            valid, err_msg = validate_row(row)
            emp_no = row.get('emp_no', '').strip()

            if not valid:
                results.append({**row, '_status': 'ERROR', '_msg': err_msg})
                err_cnt += 1
                print(f"  ❌ {emp_no} — {err_msg}")
                continue

            # 중복 체크
            exists = User.query.filter_by(emp_no=emp_no).first()
            if exists and not reset:
                results.append({**row, '_status': 'SKIP', '_msg': '이미 존재하는 사번'})
                skip_cnt += 1
                print(f"  ⏭  {emp_no} ({row.get('emp_nm','')}) — 이미 존재, 건너뜀")
                continue

            try:
                user = row_to_user(row)
                db.session.add(user)
                db.session.flush()
                results.append({**row, '_status': 'OK', '_msg': '삽입 성공'})
                ok_cnt += 1
                level_nm = LEVEL_NAMES.get(row.get('user_level', '4'), '?')
                print(f"  ✅ {emp_no} {row.get('emp_nm','')} ({level_nm})")
            except Exception as e:
                db.session.rollback()
                results.append({**row, '_status': 'ERROR', '_msg': str(e)})
                err_cnt += 1
                print(f"  ❌ {emp_no} — DB 오류: {e}")

        db.session.commit()

    # 결과 CSV 저장
    if results:
        fieldnames = list(results[0].keys())
        with open(RESULT_FILE, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)

    print(f"\n{'='*60}")
    print(f"  ✅ 삽입 성공: {ok_cnt}건")
    print(f"  ⏭  건너뜀:   {skip_cnt}건")
    print(f"  ❌ 오류:      {err_cnt}건")
    print(f"\n  📄 결과 파일: {RESULT_FILE}")
    print(f"\n  초기 비밀번호: 사번 (최초 로그인 시 강제 변경)")
    print(f"{'='*60}\n")


# ──────────────────────────────────────────────
# 커맨드: reset-pwd
# ──────────────────────────────────────────────

def cmd_reset_pwd(emp_no: str):
    with app.app_context():
        user = User.query.filter_by(emp_no=emp_no).first()
        if not user:
            print(f"❌ 사번 {emp_no} 를 찾을 수 없습니다.")
            sys.exit(1)

        user.pwd_hash    = make_pw(emp_no)
        user.pwd_init_yn = 'Y'
        user.pwd_chg_dt  = None
        user.pwd_fail_cnt = 0
        user.acct_lock_yn = 'N'
        db.session.commit()
        print(f"✅ {user.emp_nm}({emp_no}) 비밀번호 초기화 완료")
        print(f"   초기 비밀번호: {emp_no}  (다음 로그인 시 강제 변경)")


# ──────────────────────────────────────────────
# 콘도 초기 데이터
# ──────────────────────────────────────────────

CONDO_DATA = [
    # (condo_nm, brand_group_cd, resort_cd, location, sort_order)
    # ── 소노 / 대명리조트
    ('거제',             'SONO', 'DAEMYUNG',        '경상남도 거제시',          10),
    ('경주',             'SONO', 'DAEMYUNG',        '경상북도 경주시',          20),
    ('단양',             'SONO', 'DAEMYUNG',        '충청북도 단양군',          30),
    ('변산',             'SONO', 'DAEMYUNG',        '전라북도 부안군',          40),
    ('양평',             'SONO', 'DAEMYUNG',        '경기도 양평군',            50),
    ('천안',             'SONO', 'DAEMYUNG',        '충청남도 천안시',          60),
    ('청송',             'SONO', 'DAEMYUNG',        '경상북도 청송군',          70),
    ('여수엠블',         'SONO', 'DAEMYUNG',        '전라남도 여수시',          80),
    ('일산KINTEX엠블',   'SONO', 'DAEMYUNG',        '경기도 고양시 일산',       90),
    ('설악델피노',       'SONO', 'DAEMYUNG',        '강원도 고성군',           100),
    # ── 소노 / 소노펠리체
    ('비발디(홍천)',     'SONO', 'SONOFELLICE',      '강원도 홍천군',            10),
    # ── 소노 / 쏠비치
    ('남해',             'SONO', 'SOLBEACH',         '경상남도 남해군',          10),
    ('삼척',             'SONO', 'SOLBEACH',         '강원도 삼척시',            20),
    ('양양',             'SONO', 'SOLBEACH',         '강원도 양양군',            30),
    ('진도',             'SONO', 'SOLBEACH',         '전라남도 진도군',          40),
    # ── 한화 / 한화리조트
    ('거제',             'HANWHA', 'HANWHA_RESORT',  '경상남도 거제시',          10),
    ('경주',             'HANWHA', 'HANWHA_RESORT',  '경상북도 경주시',          20),
    ('대천',             'HANWHA', 'HANWHA_RESORT',  '충청남도 보령시',          30),
    ('산정호수',         'HANWHA', 'HANWHA_RESORT',  '경기도 포천시',            40),
    ('설악쏘라노',       'HANWHA', 'HANWHA_RESORT',  '강원도 속초시',            50),
    ('용인',             'HANWHA', 'HANWHA_RESORT',  '경기도 용인시',            60),
    ('제주도',           'HANWHA', 'HANWHA_RESORT',  '제주특별자치도',           70),
    ('평창',             'HANWHA', 'HANWHA_RESORT',  '강원도 평창군',            80),
    ('해운대',           'HANWHA', 'HANWHA_RESORT',  '부산광역시 해운대구',      90),
    # ── 한화 / 한화호텔
    ('벨메르(여수)',     'HANWHA', 'HANWHA_HOTEL',   '전라남도 여수시',          10),
    # ── 한화 / 안토
    ('서울(북한산)',     'HANWHA', 'ANTO',            '서울특별시 강북구',        10),
    # ── 보광 / 휘닉스아일랜드
    ('제주도',           'BOGWANG', 'PHOENIX_ISLAND', '제주특별자치도',           10),
    # ── 보광 / 휘닉스파크
    ('평창',             'BOGWANG', 'PHOENIX_PARK',   '강원도 평창군',            10),
    # ── 켄싱턴 / 켄싱턴리조트
    ('가평',             'KENSINGTON', 'KENSINGTON',  '경기도 가평군',            10),
    ('경주',             'KENSINGTON', 'KENSINGTON',  '경상북도 경주시',          20),
    ('설악비치',         'KENSINGTON', 'KENSINGTON',  '강원도 속초시',            30),
    ('설악밸리',         'KENSINGTON', 'KENSINGTON',  '강원도 속초시',            40),
    ('지리산(남원)',     'KENSINGTON', 'KENSINGTON',  '전라북도 남원시',          50),
    ('지리산(하동)',     'KENSINGTON', 'KENSINGTON',  '경상남도 하동군',          60),
    ('충주',             'KENSINGTON', 'KENSINGTON',  '충청북도 충주시',          70),
    # ── 켄싱턴 / 켄싱턴리조트(제주)
    ('한림',             'KENSINGTON', 'KENSINGTON_JEJU', '제주특별자치도 한림읍',    10),
    ('서귀포',           'KENSINGTON', 'KENSINGTON_JEJU', '제주특별자치도 서귀포시',  20),
    ('중문',             'KENSINGTON', 'KENSINGTON_JEJU', '제주특별자치도 서귀포시',  30),
    # ── 기타 / 리솜리조트
    ('덕산(스플라스)',   'ETC', 'RISOM',             '충청남도 예산군',          10),
    ('안면도(아일랜드)', 'ETC', 'RISOM',             '충청남도 태안군',          20),
    ('제천',             'ETC', 'RISOM',             '충청북도 제천시',          30),
    # ── 기타 / 용평리조트
    ('용평',             'ETC', 'YONGPYONG',         '강원도 평창군',            10),
]


# 브랜드 코드 → 표시명 매핑
BRAND_NAME_MAP = {
    'SONO':       '소노',
    'HANWHA':     '한화',
    'BOGWANG':    '보광',
    'KENSINGTON': '켄싱턴',
    'ETC':        '기타',
}

# 리조트 코드 → 표시명 매핑
RESORT_NAME_MAP = {
    'SOLBEACH':       '소노 솔비치',
    'HANWHA_RESORT':  '한화리조트',
    'HANWHA_HOTEL':   '한화호텔',
    'ANTO':           '안토',
    'PHOENIX_ISLAND': '휘닉스아일랜드',
    'PHOENIX_PARK':   '휘닉스파크',
    'KENSINGTON':     '켄싱턴리조트',
    'KENSINGTON_JEJU':'켄싱턴리조트(제주)',
    'RISOM':          '리솜리조트',
    'YONGPYONG':      '용평리조트',
}

# ──────────────────────────────────────────────
# 커맨드: condo  (신규 스키마 BRAND/RESORT/FACILITY 기반 seeding)
# ──────────────────────────────────────────────

def cmd_condo():
    """TB_CONDO_BRAND / TB_CONDO_RESORT / TB_CONDO_FACILITY duplicate-check INSERT"""

    with app.app_context():
        inserted_b = inserted_r = inserted_f = skipped = 0

        # ── 1. 브랜드 ──
        seen_brands = {}  # brand_group_cd → brand_id
        brand_sort = {}
        for _, bg_cd, _, _, so in CONDO_DATA:
            if bg_cd not in brand_sort:
                brand_sort[bg_cd] = so  # 첫 등장 sort_order 사용

        for bg_cd, b_sort in brand_sort.items():
            b_name = BRAND_NAME_MAP.get(bg_cd, bg_cd)
            existing = CondoBrand.query.filter_by(brand_name=b_name).first()
            if existing:
                seen_brands[bg_cd] = existing.brand_id
            else:
                b = CondoBrand(brand_name=b_name, sort_order=b_sort, use_yn='Y')
                db.session.add(b)
                db.session.flush()
                seen_brands[bg_cd] = b.brand_id
                inserted_b += 1
                print(f"  [브랜드 신규] {b_name}")

        # ── 2. 리조트 ──
        seen_resorts = {}  # (bg_cd, rc_cd) → resort_id
        resort_sort = {}
        for _, bg_cd, rc_cd, _, so in CONDO_DATA:
            key = (bg_cd, rc_cd)
            if key not in resort_sort:
                resort_sort[key] = so

        for (bg_cd, rc_cd), r_sort in resort_sort.items():
            r_name = RESORT_NAME_MAP.get(rc_cd, rc_cd)
            brand_id = seen_brands[bg_cd]
            existing = CondoResort.query.filter_by(
                brand_id=brand_id, resort_name=r_name
            ).first()
            if existing:
                seen_resorts[(bg_cd, rc_cd)] = existing.resort_id
            else:
                r = CondoResort(brand_id=brand_id, resort_name=r_name,
                                sort_order=r_sort, use_yn='Y')
                db.session.add(r)
                db.session.flush()
                seen_resorts[(bg_cd, rc_cd)] = r.resort_id
                inserted_r += 1
                print(f"  [리조트 신규] {r_name}")

        # ── 3. 시설 ──
        for facility_nm, bg_cd, rc_cd, location, sort_order in CONDO_DATA:
            resort_id = seen_resorts[(bg_cd, rc_cd)]
            existing = CondoFacility.query.filter_by(
                resort_id=resort_id, facility_name=facility_nm
            ).first()
            if existing:
                skipped += 1
            else:
                db.session.add(CondoFacility(
                    resort_id     = resort_id,
                    facility_name = facility_nm,
                    location      = location,
                    sort_order    = sort_order,
                    use_yn        = 'Y',
                ))
                inserted_f += 1
                print(f"  [시설 신규] {facility_nm}")

        db.session.commit()
        print(f"\n✅ 완료! 브랜드 {inserted_b}개, 리조트 {inserted_r}개, 시설 {inserted_f}개 신규 등록 / {skipped}개 건너뜀")


# ──────────────────────────────────────────────
# 커맨드: condo_reset
# ──────────────────────────────────────────────

def cmd_condo_reset():
    """TB_CONDO 데이터만 초기화 후 재INSERT (컬럼 변경 없음)"""
    from sqlalchemy import text
    from app import db as _db

    with app.app_context():
        conn = _db.engine.connect()
        trans = conn.begin()
        try:
            print("▶ 데이터 초기화")
            conn.execute(text('DELETE FROM "TB_CONDO_RESERVE"'))
            conn.execute(text('DELETE FROM "TB_CONDO_ROOM"'))
            conn.execute(text('DELETE FROM "TB_CONDO"'))
            conn.execute(text('ALTER SEQUENCE "TB_CONDO_condo_seq_seq" RESTART WITH 1'))

            print("▶ 콘도 재INSERT")
            for row in CONDO_DATA:
                conn.execute(text("""
                    INSERT INTO "TB_CONDO"
                        (condo_nm, brand_group_cd, resort_cd, location, sort_order, use_yn)
                    VALUES (:nm, :bg, :rc, :loc, :so, 'Y')
                """), {"nm": row[0], "bg": row[1], "rc": row[2], "loc": row[3], "so": row[4]})
            print(f"  {len(CONDO_DATA)}개 INSERT 완료")

            trans.commit()
        except Exception as e:
            trans.rollback()
            print(f"\n❌ 오류 발생, 롤백: {e}")
            sys.exit(1)
        finally:
            conn.close()

    print("\n✅ 콘도 데이터 리셋 완료!")


# ──────────────────────────────────────────────
# 샘플 CSV 생성
# ──────────────────────────────────────────────

def cmd_sample():
    sample_path = os.path.join(os.path.dirname(__file__), 'migration_input_sample.csv')
    rows = [
        ['emp_no','emp_nm','gender','birth_dt','phone_no','email','dept_cd','union_dept_cd','emp_type_cd','rank_cd','user_level'],
        ['A10001','홍길동','M','1985-03-15','010-1234-5678','hong@yuanta.com','D001','UD01','01','R03','4'],
        ['A10002','김영희','F','1990-07-22','010-9876-5432','kim@yuanta.com','D002','UD02','01','R04','4'],
        ['A10003','이대의','M','1978-11-05','010-1111-2222','lee@yuanta.com','D003','UD01','01','R02','2'],
        ['A10004','박집행','F','1975-06-30','010-3333-4444','park@yuanta.com','D001','UD01','01','R01','1'],
    ]
    with open(sample_path, 'w', newline='', encoding='utf-8-sig') as f:
        csv.writer(f).writerows(rows)
    print(f"✅ 샘플 파일 생성: {sample_path}")
    print("   이 파일을 migration_input.csv로 복사 후 실제 데이터로 수정하세요.")


# ──────────────────────────────────────────────
# 진입점
# ──────────────────────────────────────────────

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='UnionBBS 마이그레이션 도구',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python migrate.py sample            샘플 CSV 생성
  python migrate.py preview           미리보기 (DB 변경 없음)
  python migrate.py run               실제 삽입 실행
  python migrate.py run --reset       전체 초기화 후 재삽입
  python migrate.py reset-pwd A10001  특정 사번 비밀번호 초기화
  python migrate.py condo             TB_CONDO 컬럼변경 + 초기데이터 INSERT
  python migrate.py condo_reset       TB_CONDO 데이터만 초기화 후 재INSERT
        """
    )
    sub = parser.add_subparsers(dest='cmd')

    sub.add_parser('preview', help='변환 결과 미리보기')
    sub.add_parser('sample',  help='샘플 migration_input.csv 생성')
    sub.add_parser('condo',       help='TB_CONDO 컬럼 변경 + 초기 데이터 INSERT')
    sub.add_parser('condo_reset', help='TB_CONDO 데이터만 초기화 후 재INSERT')

    p_run = sub.add_parser('run', help='실제 삽입 실행')
    p_run.add_argument('--reset', action='store_true', help='기존 TB_USER 삭제 후 재삽입')

    p_reset = sub.add_parser('reset-pwd', help='특정 사번 비밀번호 초기화')
    p_reset.add_argument('emp_no', help='초기화할 사번')

    args = parser.parse_args()

    if args.cmd == 'preview':
        cmd_preview()
    elif args.cmd == 'sample':
        cmd_sample()
    elif args.cmd == 'run':
        cmd_run(reset=args.reset)
    elif args.cmd == 'reset-pwd':
        cmd_reset_pwd(args.emp_no)
    elif args.cmd == 'condo':
        cmd_condo()
    elif args.cmd == 'condo_reset':
        cmd_condo_reset()
    else:
        parser.print_help()