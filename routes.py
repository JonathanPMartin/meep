from os import link

from flask import Flask, app, redirect, render_template, request
from models import ThownCompany, ThrownKeyword, ninjaSearch, person, Jobs
from sqlalchemy import or_
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
    def serpapi_bulk_requests(cursor, title, location,pages):
        jobs_to_add = []
        set_of_companies = set([c.company for c in ThownCompany.query.all()])
        
        url = f"https://serpapi.com/search.json?engine=google_jobs&q=graduate+{title}&location={location}+England+United+Kingdom&google_domain=google.co.uk&gl=gb&hl=en&api_key=64799739b1492af6e528b392a9fdef00550e29a78a5758e6e7a0953a3b493357"
        for i in range(pages):
            urlwith_cursor=url;
            if cursor != "":
                urlwith_cursor += f"&next_page_token={cursor}"
            
            response = requests.get(url)
            if response.status_code != 200:
                break

            jsonData = response.json()
            jobs = jsonData.get('jobs_results', [])
            cursor = jsonData.get('next_page_token', '');

            for j in jobs:
                jobDescription = j.get("description", "")
                jobdesbreak = jobDescription.split(".")
                if len(jobdesbreak) > 3:
                    jobDescription = ".".join(jobdesbreak[:3]) + "...."

                jobpoststed=j.get("detected_extensions", "")
                jobpoststed=jobpoststed.get("posted_at", "")
                if not jobpoststed:
                    jobpoststed=datetime.utcnow().isoformat()
                    dt = datetime.utcnow();
                else:
                    jobpoststed=jobpoststed.split(" ")[0];
                    print(jobpoststed)
                    jobpoststed=int(jobpoststed)
                    dt = datetime.utcnow() - timedelta(days=jobpoststed)

                existing_job = Jobs.query.filter_by(job_url=j.get("share_link")).first()
                if existing_job or j.get("company_name") in set_of_companies or "senior" in j.get("title", "").lower():
                    continue

                jobs_to_add.append(Jobs(
                    title=j.get("title", ""),
                    discription=jobDescription,
                    max_salary=0,
                    min_salary=0,
                    job_url=j.get("share_link", ""),
                    company=j.get("company_name", ""),
                    location=location,
                    visable=True,
                    created_at=dt,
                    api_source="SerpApi"
                ))
        db.session.add_all(jobs_to_add)
        db.session.commit()
    def ninja_bulk_requests(cursor, title, location,pages):
        jobs_to_add = []
        set_of_companies = set([c.company for c in ThownCompany.query.all()])
        for i in range(pages):
            if cursor != "":
                url = f"https://api.openwebninja.com/jsearch/search-v2?query=graduate {title} in {location}&cursor={cursor}"
            else:
                url = f"https://api.openwebninja.com/jsearch/search-v2?query=graduate {title} in {location}"

            headers = {
                "x-api-key": "ak_5hhjr48p66bsh7lhexbflu2zlvuo05b8kh2necknz5dqzqy"
            }
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                break

            jsonData = response.json()
            data = jsonData.get('data', {})
            jobs = data.get('jobs', [])
            cursor = data.get('cursor', '')

            for j in jobs:
                jobDescription = j.get("job_description", "")
                jobdesbreak = jobDescription.split(".")
                if len(jobdesbreak) > 3:
                    jobDescription = ".".join(jobdesbreak[:3]) + "...."

                jobpoststed=j["job_posted_at_datetime_utc"]
                if type(jobpoststed)!=str:
                    jobpoststed=datetime.utcnow().isoformat()
                    # print(j["job_apply_link"])
                dt = datetime.fromisoformat(jobpoststed.replace("Z", "+00:00"))
                

                existing_job = Jobs.query.filter_by(job_url=j.get("job_apply_link")).first()
                if existing_job or j.get("company_name") in set_of_companies or "senior" in j.get("job_title", "").lower():
                    continue

                jobs_to_add.append(Jobs(
                    title=j.get("job_title", ""),
                    discription=jobDescription,
                    max_salary=0,
                    min_salary=0,
                    job_url=j.get("job_apply_link", ""),
                    company=j.get("company_name", ""),
                    location=location,
                    visable=True,
                    created_at=dt,
                    api_source="OpenWebNinja"
                ))
        existingrequest = ninjaSearch.query.filter_by(keyword=title, location=location).first()
        if existingrequest:
            existingrequest.cursor = cursor
            existingrequest.timestamp = datetime.utcnow()
            db.session.commit()
        return jobs_to_add

    # -------------------------
    # HOME
    # -------------------------
    @app.route('/')
    def index():
        #delete_serpapi_jobs()
        #serpapi_bulk_requests(cursor="", title="software engineer", location="London", pages=2)
        delete_old_jobs()
        delete_thrown_companies()
        print(delete_thrown_keywordsinName())
        cookie = request.cookies.get('api_source')
        if not cookie:
            response = app.make_response(render_template('index.html', jobs=Jobs.query.filter_by(visable=True).all()))
            response.set_cookie('api_source', 'all')
            return response
        else:
            if cookie == 'Reed':
                jobs = Jobs.query.filter_by(api_source="Reed", visable=True).all()
            elif cookie == 'Adzuna':
                jobs = Jobs.query.filter_by(api_source="Adzuna", visable=True).all()
            elif cookie == 'OpenWebNinja':
                jobs = Jobs.query.filter_by(api_source="OpenWebNinja", visable=True).all()
            else:
                jobs = Jobs.query.filter_by(visable=True).all()
            return render_template('index.html', jobs=jobs)
    @app.route('/set_source/<string:source>')
    def set_source(source):
        response = redirect('/')
        response.set_cookie('api_source', source)
        return response
    # -------------------------
    # PERSON: ADD
    # -------------------------
    

    # -------------------------
    # JOB: ADD (FIXED VERSION)
    # -------------------------
    @app.route('/ninja')
    def ninja():
        return render_template('ninja.html')
    @app.route("/ninja_jobs", methods=['POST'])
    def ninja_jobs():
        title = quote(request.form['keyword'])
        location = request.form['location']
        pages = int(request.form.get('pages', 2))  # Default to 2 pages if not provided
        existingrequest = ninjaSearch.query.filter_by(keyword=title, location=location).first()
        if not existingrequest:
            db.session.add(ninjaSearch(keyword=title, location=location, timestamp=datetime.utcnow(), cursor=""))
            db.session.commit()
            cursor = ""
        else:
            cursor = existingrequest.cursor if existingrequest.cursor else ""
            if existingrequest.timestamp < datetime.utcnow() - timedelta(days=3):
                existingrequest.timestamp = datetime.utcnow()
                db.session.commit()
                cursor = ""
        
        jobs_to_add = ninja_bulk_requests(cursor, title, location, pages)

        if jobs_to_add:
            db.session.add_all(jobs_to_add)
            db.session.commit()

        return redirect('/')
    @app.route("/add_job", methods=['POST'])
    def add_job():
        page = 1
        seen_urls = set()
        jobs_to_add = []
        jobs_to_add2 = []

        title = quote(request.form['title'])
        max_salary = request.form['max_salary']
        min_salary = request.form['min_salary']
        location = request.form['location']
        set_of_companies = set([c.company for c in ThownCompany.query.all()])
        cursor=""
        for i in range(0,2):
            if cursor!="":
                url=f"https://api.openwebninja.com/jsearch/search-v2?query=graduate {title} in {location}&cursor={cursor}"
            else:
                url=f"https://api.openwebninja.com/jsearch/search-v2?query=graduate {title} in {location}"
            headers = {
                "x-api-key": "ak_5hhjr48p66bsh7lhexbflu2zlvuo05b8kh2necknz5dqzqy"
            }
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                 jsonData=response.json()
                 
                 data=jsonData['data']
                 print(f"Cursor: {data['cursor']}")
                 jobs=data['jobs']
                 if 'data' not in jsonData or 'jobs' not in jsonData['data']:
                     break
                 
                 for j in jobs:
                    #print("START OF JOB")
                   # print(j["job_title"])
                    
                    jobDescription=j["job_description"]
                    jobdesbreak=jobDescription.split(".")
                    if len(jobdesbreak)>3:
                        jobDescription=jobdesbreak[0]+"."+jobdesbreak[1]+"."+jobdesbreak[2]+"...."
                    #print(jobDescription)
                    #print(j["employer_name"])
                    #print(j["job_posted_at_datetime_utc"])
                    jobpoststed=j["job_posted_at_datetime_utc"]
                    if type(jobpoststed)!=str:
                        jobpoststed=datetime.utcnow().isoformat()
                   # print(j["job_apply_link"])
                    dt = datetime.fromisoformat(jobpoststed.replace("Z", "+00:00"))
                    existing_job = Jobs.query.filter_by(job_url=url).first()
                    if existing_job:
                        continue
                    if j["employer_name"] not in set_of_companies and "senior" not in j["job_title"].lower():
                        jobs_to_add.append(Jobs(
                            title=j["job_title"],
                            discription=jobDescription,
                            max_salary=0,
                            min_salary=0,
                            job_url=j["job_apply_link"],
                            company=j["employer_name"],
                            location=location,
                            visable=True,
                            created_at=dt,
                            api_source="OpenWebNinja"
                        ))
                 cursor=data['cursor']
                
                
                    
                    
                
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
                if company not in set_of_companies and "senior" not in job_title.lower():
                    jobs_to_add.append(Jobs(
                        title=job_title,
                        discription=description,
                        max_salary=max_sal,
                        min_salary=min_sal,
                        job_url=url,
                        company=company,
                        location=location_name,
                        visable=True,
                        created_at=dt,
                        api_source="Adzuna"
                    ))

            page += 1
        
        
        link='https://www.reed.co.uk/api/1.0/search?keywords='+title+'&locationName='+location+'&postedByDirectEmployer=true&minimumSalary='+min_salary+'&maximumSalary='+max_salary
        link_response = requests.get(link,auth=("619f5ac8-2fbd-4a77-86b9-bb3facc3a793",""))
        start_filter=link_response.json()
        start_filter=start_filter['results']
        for jobs in start_filter:
            url=clean_url(jobs.get("jobUrl", "/"))
            if url in seen_urls:
                continue
            seen_urls.add(url)
            jobDescription=jobs.get("jobDescription", "No description provided")
            jobTitle=jobs.get("jobTitle", "No title provided")
            employerName=jobs.get("employerName", "Unknown")
            locationName=jobs.get("locationName", "Unknown")
            maxSal=jobs.get("maxSalary", 0)
            minSal=jobs.get("minSalary", 0)
            expiryDate=jobs.get("expirationDate", None)
            if type(jobDescription)!=str:
                jobDescription="No description provided"
            if type(jobTitle)!=str:
                jobTitle="No title provided"
            if type(employerName)!=str:
                employerName="Unknown"
            if type(locationName)!=str:
                locationName="Unknown"
            if type(maxSal)!=int:
                maxSal=0
            if type(minSal)!=int:
                minSal=0
            if type(expiryDate)!=str:
                print("TEST")
                expiryDate=datetime.utcnow().isoformat()
            else:
                
                expiryDateparts=expiryDate.split("/");
                expiryDate=expiryDateparts[2]+"-"+expiryDateparts[1]+"-"+expiryDateparts[0]+"T00:00:00Z"
                #2026-04-30T00:21:43Z
                #expiryDate=expiryDate+"T00:00:00Z"
                print(expiryDate)
                
                
            checkjob = Jobs.query.filter(Jobs.job_url.ilike(f"%{url}%")).all()
            existing_job = Jobs.query.filter_by(job_url=url).first()
            if existing_job:
                continue
            else:
                print(f"Adding job: {jobTitle} at {employerName} with URL: {url}  and expiry date: {expiryDate}")
                if company not in set_of_companies and "senior" not in job_title.lower():
                    """
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
                    )) """

                    jobs_to_add.append(Jobs(
                        title=jobTitle,
                        discription=jobDescription,
                        max_salary=maxSal,
                        min_salary=minSal,
                        job_url=url,
                        company=employerName,
                        location=locationName,
                        visable=True,
                        created_at=datetime.fromisoformat(expiryDate.replace("Z", "+00:00")) if expiryDate else datetime.utcnow(),
                        api_source="Reed"
                    ))
                
            #print(jobs_to_add2)

    
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
    
    @app.route("/keywords")
    def KeywordManager():
        keywords = ThrownKeyword.query.all()
        return render_template('keywords.html', keywords=keywords)
    
    @app.route("/add_keyword", methods=['POST'])
    def add_keyword():
        keyword = request.form['keyword']
        existing_keyword = ThrownKeyword.query.filter_by(keyword=keyword).first()
        if not existing_keyword:
            db.session.add(ThrownKeyword(keyword=keyword))
            db.session.commit()
        return redirect('/keywords')
    @app.route("/delete_keyword/<int:kid>", methods=['POST'])
    def delete_keyword(kid):
        keyword_to_delete = ThrownKeyword.query.get(kid)

        if keyword_to_delete:
            db.session.delete(keyword_to_delete)
            db.session.commit()
            return redirect('/keywords')
        return 'Keyword not found!', 404
    # -------------------------
    # DELETE OLD JOBS
    # -------------------------
    def delete_serpapi_jobs():
        try:
            cutoff_date = datetime.now() - timedelta(days=18)

            old_jobs = Jobs.query.filter(
                
                Jobs.api_source == "SerpApi"
            ).all()

            for job in old_jobs:
                db.session.delete(job)

            db.session.commit()
            return "Old SerpApi jobs deleted successfully!"

        except Exception as e:
            db.session.rollback()
            return f'Error: {str(e)}', 500
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
    
    def delete_thrown_companies():
        try:
            set_of_companies = set([c.company for c in ThownCompany.query.all()])
            jobs_to_hide = Jobs.query.filter(Jobs.company.in_(set_of_companies)).all()
            for job in jobs_to_hide:
                job.visable = False
            db.session.commit()
            return "Old jobs deleted successfully!"
        except Exception as e:
            db.session.rollback()
            return f'Error: {str(e)}', 500
    def delete_thrown_keywordsinName():
            try:
                keywords = [k.keyword.strip() for k in ThrownKeyword.query.all() if k.keyword]

                if not keywords:
                    return "No keywords found."

                # Build OR conditions for partial case-insensitive matching
                conditions = [
                    Jobs.title.ilike(f"%{keyword}%")
                    for keyword in keywords
                ]

                jobs_to_hide = Jobs.query.filter(or_(*conditions)).all()

                for job in jobs_to_hide:
                    job.visable = False

                db.session.commit()

                return f"{len(jobs_to_hide)} jobs hidden successfully!"

            except Exception as e:
                db.session.rollback()
                return f"Error: {str(e)}", 500
    @app.route("/remove")
    def remove():
     all_companies = ThownCompany.query.all()
     return render_template('removecompany.html', companies=all_companies)
    # -------------------------
    # HIDE JOB
    # -------------------------

    @app.route("/remove_company", methods=['POST'])
    def remove_company():
        company_name = request.form['company']
        company = ThownCompany.query.filter_by(company=company_name).first()
        if not company:
           db.session.add(ThownCompany(company=company_name))
           db.session.commit()
        return redirect('/remove')
    @app.route("/undoemovedcompany/<int:cid>", methods=['POST'])
    def undo_removed_company(cid):
        company = ThownCompany.query.get(cid)
        if company:
            db.session.delete(company)
            db.session.commit()
        return redirect('/remove')

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
    @app.route("/index")
    def routes():
        return render_template('routes.html')