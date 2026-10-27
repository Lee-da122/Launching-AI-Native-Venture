# TeamMatch MVP

A Flask + SQLite MVP for university teammate matching with an explainable human-controlled feedback learning loop.

## Flow
**Sign Up + Profile -> Login -> Join or Recruit -> Search/Select Competition -> Matching -> Human final decision**

Learning loop:
**Recommendation -> Accept/Reject -> optional reason -> summary -> proposed weight change -> founder review -> approval -> future matching uses approved weights**

## Development-friendly structure
```text
TeamMatch/
├─ app.py                 # routes and page flow
├─ db.py                  # SQLite schema / connection
├─ matching.py            # compatibility scoring
├─ learning.py            # feedback loop / weight proposals
├─ requirements.txt
├─ templates/
│  ├─ base.html
│  ├─ login.html
│  ├─ signup.html
│  ├─ dashboard.html
│  ├─ competitions.html
│  ├─ teams.html
│  ├─ recruit.html
│  ├─ applicants.html
│  └─ learning.html
├─ static/
│  └─ style.css
├─ architecturedoc.md
├─ scope.md
└─ BUILD_NOTE.txt
```

This keeps the existing Flask MVP while separating the parts most likely to change in future sessions.

## Initial matching weights
- Skills: 35%
- Availability: 20%
- Preferred role: 20%
- Working style: 10%
- Project goals: 15%

Approved proposals can update these weights. The total remains 100%.

## Session 7 feedback
Recommendation cards include Accept/Reject plus optional reason/comment.
Reasons: Availability, Skill fit, Preferred role, Working style, Project goals, Other.

Feedback used for learning stores the score, factor scores and weight snapshot from the time of the recommendation.
Users can turn off use of their recommendation feedback for TeamMatch learning without losing normal product functionality.

## Proposal rule
A mapped rejection reason must occur at least 5 times before it can trigger a proposal.
The relevant weight is proposed at +5 percentage points and other weights are proportionally reduced.
The proposal is Pending until a human explicitly Approves or Rejects it.

## Run on Windows / VS Code
Open this project folder in VS Code -> Terminal -> New Terminal.

```powershell
py -m pip install -r requirements.txt
py app.py
```

If `py` does not work:
```powershell
python -m pip install -r requirements.txt
python app.py
```

Open: `http://127.0.0.1:5000`

## Demo logins
Join/recommendation demo: `demo.student@university.edu` / `demo1234`

Recruiter demo: `demo.recruiter@university.edu` / `demo1234`

## Important safety boundary
TeamMatch never creates a permanent good/bad teammate score. Feedback changes compatibility-factor weights only.
