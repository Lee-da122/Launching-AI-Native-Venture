# TeamMatch Demo Day Plan

## Account strategy

Do not seed a known-password account automatically in production.

Use two manually created production accounts:

1. **Normal demo user** — a student account with a complete matching profile.
2. **Founder/admin account** — the email configured in Railway `ADMIN_EMAIL`, used only if the learning loop is shown.

Keep passwords outside this repository and public documentation.

## Recommended 2–3 minute flow

1. Open the public TeamMatch URL and log in as the normal demo user.
2. Dashboard: explain `Find the right competition. Build the right team.`
3. Click **Join a Team**.
4. Browse current Korean competitions and choose one that already has recruiting demo teams.
5. Show the compatibility score, real five-factor breakdown, and `Why this match?` explanations.
6. Toggle **Same university only** and point out that the score does not change.
7. Show one strong match and one weaker/mismatch example.
8. **Shortlist** or **Apply to Team**.
9. In the separate recommendation-feedback section, choose Accept/Reject recommendation and an optional reason.
10. Briefly return to Dashboard or show the Recruit flow.
11. Optional only if time remains: admin Learning page → feedback summary → proposal → human approval.

## Recommended profile for the normal demo user

- University: Korea University
- Skills: Coding, Data analysis
- Availability: Weekday evenings
- Preferred role: Data / Coding
- Working style: Structured and planned
- Project goal: High quality / ambitious

Create demo/test team owners manually with clearly labelled test names. Include at least:

- one Korea University team with strong overlap;
- one different-university team with similar compatibility;
- one team with a real Session 8 mismatch, such as no required-skill overlap or a non-flexible role conflict.

Do not hard-code these records into the matching algorithm.
