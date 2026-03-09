# UnionBBS 배포 가이드

## 프로젝트 구조

```
unionbbs/
├── app.py                  # Flask 메인 앱 (라우터 + 모델 통합)
├── requirements.txt        # 패키지 목록
├── .env.example            # 환경변수 예시
├── templates/              # Jinja2 HTML 템플릿
│   ├── main.html
│   ├── login.html
│   ├── about.html
│   ├── notice.html
│   ├── schedule.html
│   ├── board.html
│   ├── vote.html
│   ├── vote_admin.html
│   ├── condo.html
│   ├── condo_admin.html
│   ├── book.html
│   └── book_admin.html
├── static/                 # 정적 파일 (폐쇄망용 로컬 리소스)
│   ├── css/
│   │   └── tailwind.min.css
│   ├── fonts/
│   │   ├── Pretendard-Regular.woff2
│   │   ├── Pretendard-SemiBold.woff2
│   │   └── Pretendard-Bold.woff2
│   └── font-awesome/
│       ├── css/all.min.css
│       └── webfonts/
└── data/                   # 목데이터 CSV (참고용)
    ├── tb_user.csv
    ├── tb_notice.csv
    ├── tb_vote.csv
    ├── tb_condo_reserve.csv
    └── tb_book_rental.csv
```

---

## STEP 1. 로컬 테스트 환경 구성 (Windows / Linux 공통)

### 1-1. Python 설치 확인

```bash
python --version   # 3.10 이상 권장
pip --version
```

### 1-2. 가상환경 생성 및 활성화

```bash
# 프로젝트 폴더로 이동
cd unionbbs

# 가상환경 생성
python -m venv venv

# 활성화 (Windows)
venv\Scripts\activate

# 활성화 (Linux / Mac)
source venv/bin/activate
```

### 1-3. 패키지 설치

```bash
pip install -r requirements.txt
```

### 1-4. 환경변수 설정

```bash
# .env.example 복사
cp .env.example .env

# .env 파일 편집 (SECRET_KEY 변경 필수)
SECRET_KEY=복잡한-랜덤-문자열-변경하세요
DATABASE_URL=sqlite:///unionbbs.db
```

### 1-5. 서버 실행 (목데이터 자동 삽입)

```bash
python app.py
```

브라우저에서 `http://localhost:5000` 접속

**테스트 계정**

| 사번    | 비밀번호 | 레벨      |
|---------|----------|-----------|
| EMP001  | EMP001   | 관리자(0) |
| EMP002  | EMP002   | 집행위원(1)|
| EMP003  | EMP003   | 대의원(2) |
| EMP004  | EMP004   | 분회장(3) |
| EMP005  | EMP005   | 일반조합원(4)|

---

## STEP 2. 폐쇄망 대응 (CDN → 로컬 리소스 교체)

현재 about.html / notice.html 등 일부 템플릿은 CDN을 사용 중입니다.
폐쇄망 운영 시 아래 리소스를 static 폴더에 저장하고 경로를 교체해야 합니다.

### 2-1. 다운로드 목록

| 리소스 | 다운로드 URL | 저장 경로 |
|--------|-------------|----------|
| Tailwind CSS | https://cdn.tailwindcss.com 빌드 또는 Play CDN 출력 저장 | static/css/tailwind.min.css |
| Font Awesome | https://fontawesome.com/download | static/font-awesome/ |
| Pretendard | https://github.com/orioncactus/pretendard/releases | static/fonts/ |
| FullCalendar | https://fullcalendar.io/docs/initialize-globals | static/js/fullcalendar.min.js |

### 2-2. 템플릿 CDN 경로 교체

CDN 사용 중인 템플릿(about, notice, schedule, vote, board, condo, book)에서

```html
<!-- 변경 전 (CDN) -->
<script src="https://cdn.tailwindcss.com"></script>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/.../font-awesome/...">

<!-- 변경 후 (로컬) -->
<link rel="stylesheet" href="{{ url_for('static', filename='css/tailwind.min.css') }}">
<link rel="stylesheet" href="{{ url_for('static', filename='font-awesome/css/all.min.css') }}">
```

---

## STEP 3. 리눅스 서버 배포 (운영 환경)

### 3-1. 서버 패키지 설치

```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv nginx -y
```

### 3-2. 프로젝트 업로드

```bash
# SCP로 파일 전송
scp -r ./unionbbs user@서버IP:/home/user/

# 또는 Git 사용
git clone https://your-repo/unionbbs.git
cd unionbbs
```

### 3-3. 가상환경 및 패키지 설치

```bash
cd /home/user/unionbbs
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn   # WSGI 서버
```

### 3-4. 환경변수 설정

```bash
cp .env.example .env
nano .env
# SECRET_KEY 반드시 변경
```

### 3-5. Gunicorn 서비스 등록

```bash
sudo nano /etc/systemd/system/unionbbs.service
```

```ini
[Unit]
Description=UnionBBS Flask App
After=network.target

[Service]
User=user
WorkingDirectory=/home/user/unionbbs
Environment="PATH=/home/user/unionbbs/venv/bin"
EnvironmentFile=/home/user/unionbbs/.env
ExecStart=/home/user/unionbbs/venv/bin/gunicorn \
    --workers 2 \
    --bind 0.0.0.0:5000 \
    app:app

Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable unionbbs
sudo systemctl start unionbbs
sudo systemctl status unionbbs   # 상태 확인
```

### 3-6. Nginx 리버스 프록시 설정

```bash
sudo nano /etc/nginx/sites-available/unionbbs
```

```nginx
server {
    listen 80;
    server_name 서버IP 또는 도메인;

    location /static/ {
        alias /home/user/unionbbs/static/;
    }

    location / {
        proxy_pass         http://127.0.0.1:5000;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/unionbbs /etc/nginx/sites-enabled/
sudo nginx -t       # 설정 검증
sudo systemctl restart nginx
```

브라우저에서 `http://서버IP` 접속 확인

---

## STEP 4. Oracle 전환 방법

테스트가 완료되고 Oracle 장비가 준비되면 아래 2가지만 변경합니다.

### 4-1. requirements.txt

```
oracledb==2.3.0   # 주석 해제
```

### 4-2. .env

```
DATABASE_URL=oracle+oracledb://user:password@host:1521/service_name
```

```bash
pip install oracledb
sudo systemctl restart unionbbs
```

모델 코드는 변경 없이 그대로 사용 가능합니다.

---

## STEP 5. 운영 체크리스트

| 항목 | 확인 |
|------|------|
| SECRET_KEY 변경 | ☐ |
| debug=False 확인 (app.py 마지막 줄) | ☐ |
| CDN → 로컬 리소스 교체 | ☐ |
| Nginx HTTPS 설정 (내부망이라도 권장) | ☐ |
| DB 백업 스케줄 설정 | ☐ |
| 관리자(EMP001) 초기 비밀번호 변경 | ☐ |

---

## 주요 URL 목록

| URL | 설명 | 최소 레벨 |
|-----|------|-----------|
| /login | 로그인 | 없음 |
| / | 메인 대시보드 | 4 |
| /about | 조합소개 / 조직도 | 4 |
| /notice | 공지사항 | 4 |
| /schedule | 일정 캘린더 | 4 |
| /board | 자유게시판 | 4 |
| /vote | 투표 | 4 |
| /condo | 콘도 신청 | 4 |
| /book | 도서 대출 | 4 |
| /notice/save | 공지 작성 | 1 |
| /admin/vote/create | 투표 생성 | 1 |
| /admin/condo/save | 콘도 승인 | 1 |
| /admin/book/save | 도서 등록 | 1 |
