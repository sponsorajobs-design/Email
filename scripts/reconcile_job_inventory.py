import sqlite3
from datetime import datetime

db_local = r'c:\Users\Sumit Raj\OneDrive\email marketing\data\sponsorajobs_local.db'
db_source = r'C:\Users\Sumit Raj\OneDrive\jobs\local.sqlite'

con_src = sqlite3.connect(f'file:{db_source}?mode=ro', uri=True)
cur_src = con_src.cursor()

cur_src.execute("""
    SELECT 
        j.id,
        j.title,
        COALESCE(c.name, 'SponsorAJobs Partner') AS company,
        COALESCE(j.city, j.location, 'United Kingdom') AS location,
        UPPER(COALESCE(j.country_code, 'GB')) AS country_code,
        COALESCE(j.category_id, 'cat_general') AS category_id,
        COALESCE(j.description_clean, j.description, '') AS description,
        COALESCE(j.remote_type, 'on-site') AS remote_type,
        COALESCE(j.employment_type, 'Full-time') AS employment_type,
        COALESCE(j.quality_score, 50) AS quality_score,
        COALESCE(j.is_featured, 0) AS is_featured,
        j.published_at,
        j.first_seen_at,
        COALESCE(j.sponsorship_label, 'Verified Sponsor') AS sponsorship_label,
        COALESCE(j.sponsorship_score, 50) AS sponsorship_score,
        j.apply_url,
        j.status
    FROM jobs j
    LEFT JOIN companies c ON j.company_id = c.id
    WHERE j.status = 'active'
""")
source_rows = cur_src.fetchall()
con_src.close()
print(f"Read {len(source_rows)} active jobs from upstream source.")

con_dst = sqlite3.connect(db_local)
cur_dst = con_dst.cursor()

# Map existing jobs in dst by source_job_id
cur_dst.execute("SELECT id, source_job_id FROM jobs")
existing_rows = cur_dst.fetchall()
existing_map = {r[1]: r[0] for r in existing_rows}

# Also delete any newly created jobs whose source_job_id was short source_job_id (not j.id)
# to keep exactly 12,933 canonical active jobs
cur_dst.execute("DELETE FROM jobs WHERE source_job_id NOT LIKE 'job_%' AND id NOT IN (SELECT job_id FROM email_queue) AND id NOT IN (SELECT job_id FROM candidate_job_history)")
print(f"Cleaned up {cur_dst.rowcount} non-canonical jobs.")

# Re-map
cur_dst.execute("SELECT id, source_job_id FROM jobs")
existing_rows = cur_dst.fetchall()
existing_map = {r[1]: r[0] for r in existing_rows}

updated = 0
inserted = 0

for r in source_rows:
    slug = r[0]
    title = r[1]
    company = r[2]
    location = r[3]
    country = r[4].strip().upper() if r[4] else 'GB'
    category = r[5].strip() if r[5] else 'cat_general'
    desc = r[6] or ''
    remote = r[7] or ''
    emp_type = r[8] or 'Full-time'
    q_score = int(r[9] or 50)
    featured = int(r[10] or 0)
    pub_date = r[11]
    first_seen = r[12]
    spons_label = r[13] or 'Verified Sponsor'
    spons_score = int(r[14] or 50)
    apply_url = r[15] or ''
    app_url = f"https://sponsorajobs.com/job/{slug}"
    status = r[16] or 'active'

    if slug in existing_map:
        job_id = existing_map[slug]
        cur_dst.execute("""
            UPDATE jobs SET
                title = ?,
                company = ?,
                location = ?,
                country_code = ?,
                category_id = ?,
                description = ?,
                remote_type = ?,
                employment_type = ?,
                quality_score = ?,
                is_featured = ?,
                published_at = ?,
                first_seen_at = ?,
                sponsorship_label = ?,
                sponsorship_score = ?,
                apply_url = ?,
                application_url = ?,
                source_status = ?,
                verification_status = 'LIVE'
            WHERE id = ?
        """, (title, company, location, country, category, desc, remote, emp_type,
              q_score, featured, pub_date, first_seen, spons_label, spons_score,
              apply_url, app_url, status, job_id))
        updated += 1
    else:
        cur_dst.execute("""
            INSERT INTO jobs (
                source_job_id, title, company, location, country_code, category_id,
                description, requirements, skills, experience, remote_type, employment_type,
                quality_score, is_featured, published_at, first_seen_at,
                sponsorship_label, sponsorship_score, apply_url, application_url,
                source_status, verification_status, created_at, updated_at
            ) VALUES (
                ?, ?, ?, ?, ?, ?,
                ?, '', '', 'As specified in listing', ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, 'LIVE', datetime('now'), datetime('now')
            )
        """, (slug, title, company, location, country, category,
              desc, remote, emp_type,
              q_score, featured, pub_date, first_seen,
              spons_label, spons_score, apply_url, app_url,
              status))
        inserted += 1

con_dst.commit()

cur_dst.execute("SELECT count(*), count(country_code), count(DISTINCT source_job_id) FROM jobs")
stats = cur_dst.fetchone()
print(f"Done! Updated: {updated}, Inserted: {inserted}")
print(f"Total jobs in email db: {stats[0]}, Populated country_code: {stats[1]}, Unique source_job_ids: {stats[2]}")

con_dst.close()
