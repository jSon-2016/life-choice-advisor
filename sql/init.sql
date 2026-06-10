-- Life Choice Advisor 报告表（在 test1 库执行，可与 ai-agent / langchain-learn 共用库）
USE test1;

CREATE TABLE IF NOT EXISTS t_advisory_report (
    report_id     VARCHAR(36)  NOT NULL PRIMARY KEY,
    user_id       VARCHAR(64)  NOT NULL,
    report_type   VARCHAR(16)  NOT NULL COMMENT 'gaokao | career',
    title         VARCHAR(128) NULL,
    summary       VARCHAR(512) NULL,
    input_json    MEDIUMTEXT   NOT NULL,
    result_json   MEDIUMTEXT   NOT NULL,
    created_at    DATETIME(6)  NOT NULL,
    INDEX idx_report_user_created (user_id, created_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
