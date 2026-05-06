# account_store.py
# 역할:
#   MySQL 계정 저장소를 다룹니다.
#   로그인/회원가입, 캠페인 진행도, 점수 경쟁 최고점수와 랭킹 저장을 이 파일에 모읍니다.
import hashlib
from io import BytesIO
import os
import secrets
import time
from datetime import datetime

from PIL import Image, ImageOps

from stages import STAGE_MAX


try:
    import mysql.connector
    from mysql.connector import Error as MySQLError
except ModuleNotFoundError:
    mysql = None
    MySQLError = Exception


DEFAULT_PROFILE_IMAGE_KEY = "account_profile_icon"
PASSWORD_ITERATIONS = 200_000
MIN_LOGIN_ID_LENGTH = 3
MIN_PASSWORD_LENGTH = 4
MAX_LOGIN_ID_LENGTH = 32
MAX_NICKNAME_LENGTH = 12
PROFILE_IMAGE_SIZE = 512
MAX_PROFILE_IMAGE_BYTES = 5 * 1024 * 1024

_schema_ready = False
_last_error = ""
_schema_retry_after = 0.0


class AccountStoreError(Exception):
    pass


def set_last_error(message):
    global _last_error
    _last_error = message


def get_last_error():
    return _last_error


def get_db_config():
    return {
        "host": os.getenv("TURTLESHIP_DB_HOST", "127.0.0.1"),
        "port": int(os.getenv("TURTLESHIP_DB_PORT", "3306")),
        "user": os.getenv("TURTLESHIP_DB_USER", "root"),
        "password": os.getenv("TURTLESHIP_DB_PASSWORD", ""),
        "database": os.getenv("TURTLESHIP_DB_NAME", "turtleship"),
    }


def quote_identifier(name):
    if not name.replace("_", "").isalnum():
        raise AccountStoreError("DB 이름은 영문/숫자/언더스코어만 사용할 수 있습니다.")
    return f"`{name}`"


def connect(use_database=True):
    if mysql is None:
        raise AccountStoreError("mysql-connector-python 패키지가 설치되어 있지 않습니다.")

    config = get_db_config()
    kwargs = {
        "host": config["host"],
        "port": config["port"],
        "user": config["user"],
        "password": config["password"],
        "autocommit": False,
        "charset": "utf8mb4",
        "collation": "utf8mb4_unicode_ci",
    }
    if use_database:
        kwargs["database"] = config["database"]
    return mysql.connector.connect(**kwargs)


def ensure_schema():
    global _schema_ready, _schema_retry_after
    if _schema_ready:
        return True
    if _schema_retry_after and time.monotonic() < _schema_retry_after:
        return False

    try:
        config = get_db_config()
        db_name = quote_identifier(config["database"])
        with connect(False) as connection:
            cursor = connection.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            connection.commit()

        with connect(True) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                    login_id VARCHAR(32) NOT NULL,
                    nickname VARCHAR(12) NOT NULL,
                    password_salt VARBINARY(16) NOT NULL,
                    password_hash VARBINARY(32) NOT NULL,
                    profile_image_key VARCHAR(64) NOT NULL DEFAULT 'account_profile_icon',
                    profile_image_data MEDIUMBLOB NULL,
                    profile_image_mime VARCHAR(32) NULL,
                    unlocked_stage_count TINYINT UNSIGNED NOT NULL DEFAULT 1,
                    cleared_stage_count TINYINT UNSIGNED NOT NULL DEFAULT 0,
                    best_score INT UNSIGNED NOT NULL DEFAULT 0,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    PRIMARY KEY (id),
                    UNIQUE KEY uq_users_login_id (login_id),
                    KEY idx_users_best_score (best_score DESC)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            )
            ensure_column(cursor, "users", "profile_image_data", "MEDIUMBLOB NULL")
            ensure_column(cursor, "users", "profile_image_mime", "VARCHAR(32) NULL")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS score_entries (
                    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                    user_id BIGINT UNSIGNED NULL,
                    nickname VARCHAR(12) NOT NULL,
                    score INT UNSIGNED NOT NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (id),
                    KEY idx_score_entries_score (score DESC, created_at ASC),
                    KEY idx_score_entries_user (user_id),
                    CONSTRAINT fk_score_entries_user
                        FOREIGN KEY (user_id) REFERENCES users(id)
                        ON DELETE SET NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            )
            connection.commit()
        _schema_ready = True
        set_last_error("")
        return True
    except (AccountStoreError, MySQLError, OSError, ValueError) as error:
        set_last_error(str(error))
        _schema_retry_after = time.monotonic() + 5.0
        return False


def ensure_column(cursor, table_name, column_name, definition):
    try:
        cursor.execute(f"ALTER TABLE {quote_identifier(table_name)} ADD COLUMN {quote_identifier(column_name)} {definition}")
    except MySQLError as error:
        if getattr(error, "errno", None) != 1060:
            raise


def load_profile_image(path):
    if not path:
        return None, ""

    try:
        raw_size = os.path.getsize(path)
        if raw_size > MAX_PROFILE_IMAGE_BYTES:
            return None, "프로필 이미지는 5MB 이하만 가능합니다."

        with Image.open(path) as image:
            image = ImageOps.exif_transpose(image).convert("RGBA")
            return image.copy(), ""
    except (OSError, ValueError) as error:
        return None, f"이미지를 불러오지 못했습니다: {error}"


def load_profile_image_preview(path):
    image, message = load_profile_image(path)
    if image is None:
        return None, None, message
    return image.tobytes("raw", "RGBA"), image.size, ""


def normalize_profile_crop_box(crop_box, width, height):
    width = max(1, int(width))
    height = max(1, int(height))
    max_side = min(width, height)

    if crop_box:
        left, top, side = crop_box
        side = int(max(1, min(float(side), max_side)))
        left = int(max(0, min(float(left), width - side)))
        top = int(max(0, min(float(top), height - side)))
        return left, top, side

    side = max_side
    return (width - side) // 2, (height - side) // 2, side


def prepare_profile_image(path, crop_box=None):
    image, message = load_profile_image(path)
    if image is None:
        return None, None, message

    width, height = image.size
    left, top, side = normalize_profile_crop_box(crop_box, width, height)
    image = image.crop((left, top, left + side, top + side))
    image = image.resize((PROFILE_IMAGE_SIZE, PROFILE_IMAGE_SIZE), Image.Resampling.LANCZOS)

    output = BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue(), "image/png", ""


def clean_login_id(login_id):
    text = str(login_id or "").strip()
    text = "".join(char for char in text if char.isalnum() or char in "._-")
    return text[:MAX_LOGIN_ID_LENGTH]


def clean_nickname(nickname):
    text = str(nickname or "").strip()
    text = " ".join(text.split())
    return text[:MAX_NICKNAME_LENGTH]


def validate_credentials(login_id, password, nickname=None):
    login_id = clean_login_id(login_id)
    password = str(password or "")
    nickname = clean_nickname(nickname) if nickname is not None else None
    if len(login_id) < MIN_LOGIN_ID_LENGTH:
        return None, None, None, "ID는 3자 이상이어야 합니다."
    if len(password) < MIN_PASSWORD_LENGTH:
        return None, None, None, "PW는 4자 이상이어야 합니다."
    if nickname is not None and not nickname:
        return None, None, None, "닉네임을 입력하세요."
    return login_id, password, nickname, ""


def hash_password(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    password_hash = hashlib.pbkdf2_hmac("sha256", str(password).encode("utf-8"), salt, PASSWORD_ITERATIONS)
    return salt, password_hash


def normalize_profile(row):
    if not row:
        return None
    unlocked = max(1, min(STAGE_MAX, int(row.get("unlocked_stage_count", 1))))
    cleared = max(0, min(STAGE_MAX, int(row.get("cleared_stage_count", 0))))
    unlocked = max(unlocked, min(STAGE_MAX, cleared + 1 if cleared < STAGE_MAX else STAGE_MAX))
    image_data = row.get("profile_image_data")
    if image_data is not None:
        image_data = bytes(image_data)
    return {
        "id": int(row["id"]),
        "login_id": str(row["login_id"]),
        "nickname": str(row["nickname"]),
        "profile_image_key": row.get("profile_image_key") or DEFAULT_PROFILE_IMAGE_KEY,
        "profile_image_data": image_data,
        "profile_image_mime": row.get("profile_image_mime") or "image/png",
        "unlocked_stage_count": unlocked,
        "cleared_stage_count": cleared,
        "best_score": int(row.get("best_score", 0)),
    }


def fetch_user_by_login_id(cursor, login_id):
    cursor.execute(
        """
        SELECT id, login_id, nickname, password_salt, password_hash,
               profile_image_key, profile_image_data, profile_image_mime,
               unlocked_stage_count, cleared_stage_count, best_score
        FROM users
        WHERE login_id = %s
        """,
        (login_id,),
    )
    return cursor.fetchone()


def login_user(login_id, password):
    login_id, password, _, message = validate_credentials(login_id, password)
    if message:
        return None, message
    if not ensure_schema():
        return None, f"MySQL 연결 실패: {get_last_error()}"

    connection = None
    try:
        with connect(True) as connection:
            cursor = connection.cursor(dictionary=True)
            row = fetch_user_by_login_id(cursor, login_id)
            if not row:
                return None, "계정 정보를 찾을 수 없습니다."
            _, expected_hash = hash_password(password, bytes(row["password_salt"]))
            if not secrets.compare_digest(expected_hash, bytes(row["password_hash"])):
                return None, "비밀번호가 맞지 않습니다."
            return normalize_profile(row), ""
    except (AccountStoreError, MySQLError, OSError) as error:
        set_last_error(str(error))
        return None, f"MySQL 연결 실패: {error}"


def signup_user(login_id, password, nickname, profile_image_data=None, profile_image_mime=None):
    login_id, password, nickname, message = validate_credentials(login_id, password, nickname)
    if message:
        return None, message
    if not ensure_schema():
        return None, f"MySQL 연결 실패: {get_last_error()}"

    salt, password_hash = hash_password(password)
    connection = None
    try:
        with connect(True) as connection:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                """
                INSERT INTO users (
                    login_id, nickname, password_salt, password_hash,
                    profile_image_key, profile_image_data, profile_image_mime
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (login_id, nickname, salt, password_hash, DEFAULT_PROFILE_IMAGE_KEY, profile_image_data, profile_image_mime),
            )
            connection.commit()
            row_id = cursor.lastrowid
            cursor.execute(
                """
                SELECT id, login_id, nickname, profile_image_key, profile_image_data, profile_image_mime,
                       unlocked_stage_count, cleared_stage_count, best_score
                FROM users
                WHERE id = %s
                """,
                (row_id,),
            )
            return normalize_profile(cursor.fetchone()), ""
    except MySQLError as error:
        if connection is not None:
            connection.rollback()
        if getattr(error, "errno", None) == 1062:
            return None, "이미 사용 중인 ID입니다."
        set_last_error(str(error))
        return None, f"MySQL 저장 실패: {error}"
    except (AccountStoreError, OSError) as error:
        set_last_error(str(error))
        return None, f"MySQL 연결 실패: {error}"


def update_user_profile(user_id, login_id, password, nickname, profile_image_data=None, profile_image_mime=None, update_profile_image=False):
    login_id = clean_login_id(login_id)
    nickname = clean_nickname(nickname)
    if len(login_id) < MIN_LOGIN_ID_LENGTH:
        return None, "ID는 3자 이상이어야 합니다."
    if not nickname:
        return None, "닉네임을 입력하세요."
    if password and len(password) < MIN_PASSWORD_LENGTH:
        return None, "새 PW는 4자 이상이어야 합니다."
    if not ensure_schema():
        return None, f"MySQL 연결 실패: {get_last_error()}"

    connection = None
    try:
        with connect(True) as connection:
            cursor = connection.cursor(dictionary=True)
            if password:
                salt, password_hash = hash_password(password)
                image_sql = ", profile_image_data = %s, profile_image_mime = %s" if update_profile_image else ""
                image_args = (profile_image_data, profile_image_mime) if update_profile_image else ()
                cursor.execute(
                    f"""
                    UPDATE users
                    SET login_id = %s, nickname = %s, password_salt = %s, password_hash = %s{image_sql}
                    WHERE id = %s
                    """,
                    (login_id, nickname, salt, password_hash, *image_args, user_id),
                )
            else:
                image_sql = ", profile_image_data = %s, profile_image_mime = %s" if update_profile_image else ""
                image_args = (profile_image_data, profile_image_mime) if update_profile_image else ()
                cursor.execute(
                    f"""
                    UPDATE users
                    SET login_id = %s, nickname = %s{image_sql}
                    WHERE id = %s
                    """,
                    (login_id, nickname, *image_args, user_id),
                )
            connection.commit()
            cursor.execute(
                """
                SELECT id, login_id, nickname, profile_image_key, profile_image_data, profile_image_mime,
                       unlocked_stage_count, cleared_stage_count, best_score
                FROM users
                WHERE id = %s
                """,
                (user_id,),
            )
            return normalize_profile(cursor.fetchone()), ""
    except MySQLError as error:
        if connection is not None:
            connection.rollback()
        if getattr(error, "errno", None) == 1062:
            return None, "이미 사용 중인 ID입니다."
        set_last_error(str(error))
        return None, f"MySQL 저장 실패: {error}"
    except (AccountStoreError, OSError) as error:
        set_last_error(str(error))
        return None, f"MySQL 연결 실패: {error}"


def apply_profile_to_game(game, profile):
    game.account_user = profile
    game.score_nickname = profile["nickname"]
    game.unlocked_stage_count = profile["unlocked_stage_count"]
    game.cleared_stage_count = profile["cleared_stage_count"]
    game.stage_select_index = max(0, min(getattr(game, "stage_select_index", 0), game.unlocked_stage_count - 1))
    game.account_profile_upload_bytes = None
    game.account_profile_upload_mime = None
    game.account_profile_upload_changed = False
    game._account_profile_surface_key = None
    game._account_profile_surface = None


def current_user(game):
    return getattr(game, "account_user", None)


def load_current_user_progress(game):
    user = current_user(game)
    if not user:
        return None
    return {
        "unlocked_stage_count": user["unlocked_stage_count"],
        "cleared_stage_count": user["cleared_stage_count"],
    }


def save_current_user_progress(game, progress):
    user = current_user(game)
    if not user or not ensure_schema():
        return False

    unlocked = max(1, min(STAGE_MAX, int(progress.get("unlocked_stage_count", 1))))
    cleared = max(0, min(STAGE_MAX, int(progress.get("cleared_stage_count", 0))))
    connection = None
    try:
        with connect(True) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                UPDATE users
                SET unlocked_stage_count = %s, cleared_stage_count = %s
                WHERE id = %s
                """,
                (unlocked, cleared, user["id"]),
            )
            connection.commit()
        user["unlocked_stage_count"] = unlocked
        user["cleared_stage_count"] = cleared
        return True
    except (AccountStoreError, MySQLError, OSError) as error:
        set_last_error(str(error))
        return False


def load_scores():
    if not ensure_schema():
        return None

    try:
        with connect(True) as connection:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT nickname, score, DATE_FORMAT(created_at, '%Y-%m-%d %H:%i') AS date
                FROM score_entries
                ORDER BY score DESC, created_at ASC
                LIMIT 10
                """
            )
            return [
                {
                    "nickname": clean_nickname(row["nickname"]),
                    "score": int(row["score"]),
                    "date": str(row.get("date") or ""),
                }
                for row in cursor.fetchall()
            ]
    except (AccountStoreError, MySQLError, OSError) as error:
        set_last_error(str(error))
        return None


def submit_score(nickname, score, game=None):
    if not ensure_schema():
        return None

    try:
        score_value = max(0, int(score))
    except (TypeError, ValueError):
        score_value = 0

    user = current_user(game) if game is not None else None
    nickname = clean_nickname(user["nickname"] if user else nickname) or "무명"
    user_id = user["id"] if user else None

    connection = None
    try:
        with connect(True) as connection:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                """
                INSERT INTO score_entries (user_id, nickname, score, created_at)
                VALUES (%s, %s, %s, %s)
                """,
                (user_id, nickname, score_value, datetime.now()),
            )
            if user:
                cursor.execute(
                    """
                    UPDATE users
                    SET best_score = GREATEST(best_score, %s)
                    WHERE id = %s
                    """,
                    (score_value, user_id),
                )
                user["best_score"] = max(int(user.get("best_score", 0)), score_value)
            cursor.execute(
                """
                DELETE FROM score_entries
                WHERE id NOT IN (
                    SELECT id FROM (
                        SELECT id
                        FROM score_entries
                        ORDER BY score DESC, created_at ASC
                        LIMIT 10
                    ) AS keepers
                )
                """
            )
            connection.commit()

            entries = load_scores() or []
            rank = None
            for index, entry in enumerate(entries):
                if entry["nickname"] == nickname and entry["score"] == score_value:
                    rank = index + 1
                    break
            return entries, rank
    except (AccountStoreError, MySQLError, OSError) as error:
        try:
            connection.rollback()
        except Exception:
            pass
        set_last_error(str(error))
        return None
