from app.database import engine
from sqlalchemy import text

with engine.begin() as conn:
    cols = [r[0] for r in conn.execute(text("SHOW COLUMNS FROM users"))]
    print("users cols", cols)
    if "is_admin" not in cols:
        conn.execute(text("ALTER TABLE users ADD COLUMN is_admin TINYINT(1) NOT NULL DEFAULT 0"))
    if "status" not in cols:
        conn.execute(text("ALTER TABLE users ADD COLUMN status VARCHAR(16) NOT NULL DEFAULT 'active'"))
    conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS reports (
              id INT AUTO_INCREMENT PRIMARY KEY,
              post_id INT NOT NULL,
              circle_id INT NOT NULL,
              reporter_id INT NOT NULL,
              report_type VARCHAR(32) NOT NULL,
              reason TEXT,
              status VARCHAR(16) NOT NULL DEFAULT 'pending',
              handle_reason VARCHAR(255),
              created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
              handled_at DATETIME NULL,
              INDEX ix_reports_status (status),
              INDEX ix_reports_post (post_id),
              INDEX ix_reports_circle (circle_id)
            )
            """
        )
    )
    conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS audit_logs (
              id INT AUTO_INCREMENT PRIMARY KEY,
              admin_id INT NULL,
              action VARCHAR(64) NOT NULL,
              target VARCHAR(128) NOT NULL,
              reason VARCHAR(255),
              created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    )
    print("migrated")
