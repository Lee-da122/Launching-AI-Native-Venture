# TeamMatch MVP

A functional Flask + SQLite MVP for university teammate matching.

## Final agreed flow

**Sign Up + Profile -> Login -> Join or Recruit -> Search/Select Competition -> Matching -> Human final decision**

### Sign Up + Profile
Users create an account and matching profile together:
- Name
- University
- University email
- Password
- Skills
- Availability, including Flexible / Negotiable
- Preferred role
- Working style
- Project goal / effort level

### Join a Team
1. Search/select a competition
2. View recruiting teams
3. Teams are sorted by compatibility with the saved user profile
4. The app explains why each match was suggested
5. User can shortlist or apply

### Recruit a Team
1. Search/select a competition
2. Create a recruiting post
3. Specify needed skills, role, availability, working style, effort level, and team size
4. View applicants
5. Applicants are sorted by compatibility
6. Recruiter decides who to accept or reject

## Stack

- Frontend: Jinja HTML + CSS
- Backend: Flask
- Database: SQLite
- Authentication: Flask session + Werkzeug password hashing
- Matching: transparent rule-based compatibility baseline

## Important MVP boundary

The matching system does not label students as good or bad teammates.
It only compares compatibility signals and explains them.
The human user always makes the final decision.

## Intentionally out of scope

- Real university email verification
- Google/OAuth login
- Chat
- Payments
- Real-time notifications
- Calendar integration
- External competition APIs
- Complex AI agents / LLM matching
- Automatic participation scoring
- Post-project participation monitoring

## Run on Windows / VS Code

Open this folder in VS Code, then open Terminal -> New Terminal.

```powershell
py -m pip install -r requirements.txt
py app.py
```

If `py` does not work:

```powershell
python -m pip install -r requirements.txt
python app.py
```

Open:

`http://127.0.0.1:5000`

## Demo login

Email: `demo.recruiter@university.edu`

Password: `demo1234`

## Database tables

- users
- competitions
- teams
- applications
- shortlists

The SQLite file is created and seeded automatically if it does not exist.
