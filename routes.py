from flask import Flask, app, redirect, render_template, request
from models import person, Jobs
from urllib.parse import quote, urlparse
import requests
from datetime import datetime, timedelta
import jsonify

# -----------------------------
# Helpers
# -----------------------------
def clean_url(url):
    if not url:
        return "/"
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"


# -----------------------------
# Routes registration
# -----------------------------
def register_route(app, db):

    # -------------------------
    # HOME
    # -------------------------
    @app.route('/')
    def index():
        delete_old_jobs()

        jobs = Jobs.query.filter_by(visable=True).all()
        return render_template('index.html', jobs=jobs)

    # -------------------------
    # PERSON: ADD
    # -------------------------
    

    # -------------------------
    # JOB: ADD (FIXED VERSION)
    # -------------------------
    @app.route("/add_job", methods=['POST'])
    def add_job():
        page = 1
        seen_urls = set()
        jobs_to_add = []

        title = quote(request.form['title'])
        max_salary = request.form['max_salary']
        min_salary = request.form['min_salary']
        location = request.form['location']

        while True:
            urlbase = (
                f"http://api.adzuna.com/v1/api/jobs/gb/search/{page}"
                f"?app_id=edd2d141&app_key=b0e855aede72a68b215f313ce404166c"
                f"&results_per_page=20"
                f"&salary_min={min_salary}&salary_max={max_salary}"
                f"&what={title}&where={location}"
                f"&max_days_old=18"
            )

            try:
                response = requests.get(urlbase, timeout=10)
                response.raise_for_status()
            except requests.RequestException:
                break

            data = response.json()
            results = data.get("results", [])

            if not results:
                break

            for j in results:
                url = clean_url(j.get("redirect_url", "/"))

                # prevent duplicates in same run
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                # safe parsing
                description = j.get("description", "No description provided")
                job_title = j.get("title", "No title provided")

                company = j.get("company", {}).get("display_name", "Unknown")
                location_name = j.get("location", {}).get("display_name", "Unknown")

                max_sal = j.get("salary_max", 0)
                min_sal = j.get("salary_min", 0)

                created_at = j.get("created")
                if created_at:
                    dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                else:
                    dt = datetime.utcnow()

                # DB duplicate check (safety net)
                checkjob = Jobs.query.filter(Jobs.job_url.ilike(f"%{url}%")).all()
                #print(checkjob)
                existing_job = Jobs.query.filter_by(job_url=url).first()
                if existing_job:
                    continue

                jobs_to_add.append(Jobs(
                    title=job_title,
                    discription=description,
                    max_salary=max_sal,
                    min_salary=min_sal,
                    job_url=url,
                    company=company,
                    location=location_name,
                    visable=True,
                    created_at=dt
                ))

            page += 1

        # single commit (IMPORTANT)
        if jobs_to_add:
            db.session.add_all(jobs_to_add)
            db.session.commit()

        return redirect('/')

    # -------------------------
    # DELETE JOB
    # -------------------------
    @app.route("/delete_job/<int:jid>", methods=['POST'])
    def delete_job(jid):
        job_to_delete = Jobs.query.get(jid)

        if job_to_delete:
            db.session.delete(job_to_delete)
            db.session.commit()
            return redirect('/')
        return 'Job not found!', 404

    # -------------------------
    # DELETE OLD JOBS
    # -------------------------
    def delete_old_jobs():
        try:
            cutoff_date = datetime.now() - timedelta(days=18)

            old_jobs = Jobs.query.filter(
                Jobs.created_at < cutoff_date
            ).all()

            for job in old_jobs:
                db.session.delete(job)

            db.session.commit()
            return "Old jobs deleted successfully!"

        except Exception as e:
            db.session.rollback()
            return f'Error: {str(e)}', 500
    @app.route("/get_all_jobs")
    def get_all_jobs():
        jobs = Jobs.query.all()
        list_of_jobs = []
        for job in jobs:
            job_data = {
                "jid": job.jid,
                "title": job.title,
                "discription": job.discription,
                "max_salary": job.max_salary,
                "min_salary": job.min_salary,
                "job_url": job.job_url,
                "company": job.company,
                "location": job.location,
                "visable": job.visable,
                "created_at": job.created_at.isoformat()
            }
            list_of_jobs.append(job_data)
        return list_of_jobs

    # -------------------------
    # HIDE JOB
    # -------------------------
    @app.route("/hide_job/<int:jid>", methods=['POST'])
    def hide_job(jid):
        job_to_hide = Jobs.query.get(jid)

        if job_to_hide:
            job_to_hide.visable = False
            db.session.commit()
            return redirect('/')
        return 'Job not found!', 404

    # -------------------------
    # DELETE ALL JOBS
    # -------------------------
    @app.route("/delete_all_jobs")
    def delete_all_jobs():
        try:
            db.session.query(Jobs).delete()
            db.session.commit()
            return redirect('/')
        except Exception as e:
            db.session.rollback()
            return f'Error: {str(e)}', 500
    @app.route("/add_test_job", methods=['GET', 'POST'])
    def add_test_job():
        if request.method == 'POST':
            new_job = Jobs(
                title="Test Job Should be Automatically Deleted should not be seen.",
                discription="This is a test job description.",
                max_salary=50000,
                min_salary=30000,
                job_url="http://example.com/test-job",
                company="Test Company",
                location="Test Location",
                visable=True,
                created_at=datetime.now() - timedelta(days=20)
            )
            db.session.add(new_job)
            db.session.commit()
            return redirect('/')
        return render_template('add_test_job.html')
    @app.route("/searchbyname/<string:name>")
    def search_by_name(name):
        jobs = Jobs.query.filter(Jobs.title.ilike(f"%{name}%")).all()
        list_of_jobs = []
        for job in jobs:
            job_data = {
                "jid": job.jid,
                "title": job.title,
                "discription": job.discription,
                "max_salary": job.max_salary,
                "min_salary": job.min_salary,
                "job_url": job.job_url,
                "company": job.company,
                "location": job.location,
                "visable": job.visable,
                "created_at": job.created_at.isoformat()
            }
            list_of_jobs.append(job_data)
        return list_of_jobs    
    
   