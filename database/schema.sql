-- ===================================================================
-- SMTAS Database Schema
-- Compatible with MySQL 8.0+ and SQLite (used by default in this build)
-- Matches ER Diagram (Figure 4.1) and Data Dictionary (Sec 4.2) of the SDD
-- ===================================================================

CREATE TABLE IF NOT EXISTS users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(30) DEFAULT 'Researcher',
    login_attempts INT DEFAULT 0,
    is_locked BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS trends (
    trend_id INT PRIMARY KEY AUTO_INCREMENT,
    keyword VARCHAR(100) NOT NULL,
    platform ENUM('YouTube', 'TikTok') NOT NULL,
    total_views BIGINT DEFAULT 0,
    growth_rate FLOAT DEFAULT 0.0,
    virality_score FLOAT DEFAULT 0.0,
    peak_date TIMESTAMP NULL,
    created_by INT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS metrics (
    id INT PRIMARY KEY AUTO_INCREMENT,
    trend_id INT NOT NULL,
    views BIGINT DEFAULT 0,
    likes BIGINT DEFAULT 0,
    shares BIGINT DEFAULT 0,
    comments_count BIGINT DEFAULT 0,
    recorded_date DATE NOT NULL,
    FOREIGN KEY (trend_id) REFERENCES trends(trend_id)
);

CREATE TABLE IF NOT EXISTS sentiment (
    id INT PRIMARY KEY AUTO_INCREMENT,
    trend_id INT NOT NULL,
    positive_score FLOAT DEFAULT 0.0,
    negative_score FLOAT DEFAULT 0.0,
    neutral_score FLOAT DEFAULT 0.0,
    dominant_sentiment VARCHAR(20),
    sample_comment TEXT,
    FOREIGN KEY (trend_id) REFERENCES trends(trend_id)
);

CREATE TABLE IF NOT EXISTS reports (
    report_id INT PRIMARY KEY AUTO_INCREMENT,
    trend_id INT NOT NULL,
    generated_by INT,
    format VARCHAR(10) DEFAULT 'PDF',
    file_path VARCHAR(255),
    gen_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (trend_id) REFERENCES trends(trend_id),
    FOREIGN KEY (generated_by) REFERENCES users(id)
);
