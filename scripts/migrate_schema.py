import sqlite3

db_path = r'c:\Users\Sumit Raj\OneDrive\email marketing\data\sponsorajobs_local.db'
con = sqlite3.connect(db_path)
cur = con.cursor()

def add_col_if_missing(table, col, col_type):
    cur.execute(f'PRAGMA table_info({table})')
    cols = [r[1] for r in cur.fetchall()]
    if col not in cols:
        print(f'Adding {col} ({col_type}) to {table}...')
        cur.execute(f'ALTER TABLE {table} ADD COLUMN {col} {col_type}')
    else:
        print(f'{table}.{col} already exists.')

# 1. jobs columns
add_col_if_missing('jobs', 'country_code', 'VARCHAR(10)')
add_col_if_missing('jobs', 'category_id', 'VARCHAR(50)')
add_col_if_missing('jobs', 'remote_type', 'VARCHAR(50)')
add_col_if_missing('jobs', 'quality_score', 'INTEGER')
add_col_if_missing('jobs', 'is_featured', 'INTEGER DEFAULT 0')
add_col_if_missing('jobs', 'published_at', 'DATETIME')
add_col_if_missing('jobs', 'first_seen_at', 'DATETIME')
add_col_if_missing('jobs', 'sponsorship_label', 'VARCHAR(100)')
add_col_if_missing('jobs', 'sponsorship_score', 'INTEGER')
add_col_if_missing('jobs', 'apply_url', 'VARCHAR(1000)')

# 2. subscribers columns
add_col_if_missing('subscribers', 'country_code', "VARCHAR(10) DEFAULT 'ALL'")
add_col_if_missing('subscribers', 'frequency', "VARCHAR(50) DEFAULT 'daily'")

# 3. email_queue columns
add_col_if_missing('email_queue', 'dispatch_date', 'VARCHAR(10)')
add_col_if_missing('email_queue', 'locked_at', 'DATETIME')
add_col_if_missing('email_queue', 'reconciliation_status', 'VARCHAR(50)')

# Create index on jobs for high performance role & country queries
cur.execute('CREATE INDEX IF NOT EXISTS idx_jobs_country_cat ON jobs(country_code, category_id)')
cur.execute('CREATE INDEX IF NOT EXISTS idx_jobs_published ON jobs(published_at DESC)')
cur.execute('CREATE INDEX IF NOT EXISTS idx_jobs_status_verif ON jobs(source_status, verification_status)')

# Populate existing email_queue rows with dispatch_date = DATE(created_at) if null
cur.execute("UPDATE email_queue SET dispatch_date = strftime('%Y-%m-%d', created_at) WHERE dispatch_date IS NULL")

# Clean duplicate existing queue rows for same subscriber on same date so unique index succeeds
cur.execute("""
    DELETE FROM email_queue 
    WHERE id NOT IN (
        SELECT MIN(id) 
        FROM email_queue 
        GROUP BY subscriber_id, dispatch_date
    )
""")

# Create unique index on (subscriber_id, dispatch_date)
cur.execute('CREATE UNIQUE INDEX IF NOT EXISTS uq_subscriber_dispatch_date ON email_queue(subscriber_id, dispatch_date)')
print('Created/verified unique index uq_subscriber_dispatch_date.')

con.commit()
con.close()
print('Schema migration completed successfully.')
