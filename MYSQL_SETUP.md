# TurtleShip MySQL 설정

## 1. MySQL 설치

macOS Homebrew 기준:

```bash
brew install mysql
brew services start mysql
```

MySQL 접속 확인:

```bash
mysql -u root
```

## 2. DB와 테이블 생성

프로젝트 루트에서:

```bash
mysql -u root < database/schema.sql
```

이미 예전 테이블을 만든 상태라면 아래 컬럼을 한 번만 추가하세요:

```sql
USE turtleship;

ALTER TABLE users
  ADD COLUMN profile_image_data MEDIUMBLOB NULL,
  ADD COLUMN profile_image_mime VARCHAR(32) NULL;
```

최신 코드로 실행하면 누락된 프로필 이미지 컬럼은 자동으로도 추가합니다.

별도 계정을 만들고 싶다면 MySQL 콘솔에서:

```sql
CREATE USER 'turtleship_app'@'%' IDENTIFIED BY '강한비밀번호';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER
ON turtleship.*
TO 'turtleship_app'@'%';
FLUSH PRIVILEGES;
```

## 3. 파이썬 패키지 설치

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

## 4. 게임 실행 전 환경변수 설정

로컬 MySQL root 계정을 그대로 쓸 때:

```bash
export TURTLESHIP_DB_HOST=127.0.0.1
export TURTLESHIP_DB_PORT=3306
export TURTLESHIP_DB_USER=root
export TURTLESHIP_DB_PASSWORD=
export TURTLESHIP_DB_NAME=turtleship
```

앱 계정을 따로 만든 경우:

```bash
export TURTLESHIP_DB_USER=turtleship_app
export TURTLESHIP_DB_PASSWORD=강한비밀번호
```

## 5. 저장되는 데이터

- `users`: ID, 닉네임, 비밀번호 해시, 프로필 이미지 PNG 데이터, 캠페인 해금 단계, 클리어 단계, 본인 최고점수
- `score_entries`: 점수 경쟁 모드 상위 10개 랭킹

비밀번호는 원문이 아니라 PBKDF2-SHA256 해시와 salt로 저장됩니다.
