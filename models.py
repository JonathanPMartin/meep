from app import db
class person(db.Model):
    __tabelname__ = 'people'
    pid = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    def __repr__(self):
         return f'<person {self.name}>' 

class Jobs(db.Model):
    __tablename__ = 'jobs'
    jid = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    discription = db.Column(db.Text, nullable=False)
    max_salary = db.Column(db.Integer, nullable=False)
    min_salary = db.Column(db.Integer, nullable=False)
    job_url = db.Column(db.Text, nullable=False)
    company = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    visable = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    def __repr__(self):
        return f'<Job {self.title} at {self.company}>'