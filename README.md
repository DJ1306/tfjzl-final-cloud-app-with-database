# Online Course Assessment Project

Adds Question, Choice and Submission models, Django administration, course exams,
submission persistence and detailed exam results to the IBM starter application.

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 manage.py makemigrations onlinecourse
python3 manage.py migrate
# Set DEMO_ADMIN_PASSWORD in your environment before running seed_demo.
python3 manage.py seed_demo
python3 manage.py test onlinecourse -v 2
python3 manage.py runserver 0.0.0.0:8000
```

Open `/admin/` to administer the course, then `/onlinecourse/` to take its exam.
The demo follows the lab's Learning Django example. The demo administrator's
password is read from the environment and is never included in this repository.

Question credit requires exactly the correct choices; selecting additional wrong
answers does not earn credit. Submissions require login, course enrollment and
POST. A learner can only read their own exam results.

The course dependencies are retained for this educational lab. This repository
is a development project, not a production deployment configuration.

Starter: https://github.com/ibm-developer-skills-network/tfjzl-final-cloud-app-with-database
