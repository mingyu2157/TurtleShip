CREATE DATABASE IF NOT EXISTS turtleship
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE turtleship;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
