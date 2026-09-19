import sqlite3

db_eng = r'c:\Users\Sumit Raj\OneDrive\email marketing\data\sponsorajobs_local.db'
db_src = r'C:\Users\Sumit Raj\OneDrive\jobs\local.sqlite'
con_eng = sqlite3.connect(db_eng)
con_src = sqlite3.connect(db_src)

cur_src = con_src.cursor()
cur_src.execute("SELECT id, source_job_id, country_code, category_id, remote_type, quality_score, is_featured, published_at, apply_url FROM jobs WHERE status = 'active'")
rows = cur_src.fetchall()

cur_eng = con_eng.cursor()
for r in rows:
    source_id = str(r[1] or r[0])
    cur_eng.execute('''
        UPDATE jobs 
        SET country_code = UPPER(COALESCE(?, 'GB')),
            category_id = COALESCE(?, 'cat_general'),
            remote_type = ?,
            quality_score = ?,
            is_featured = ?,
            published_at = ?,
            apply_url = ?
        WHERE source_job_id = ?
    ''', (r[2], r[3], r[4], r[5], r[6], r[7], r[8], source_id))

con_eng.commit()
cur_eng.execute('SELECT count(*), count(country_code) FROM jobs')
print('Jobs total and populated country_code:', cur_eng.fetchone())
con_eng.close()
con_src.close()
