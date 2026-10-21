# Architecture Document

## Product

TeamMatch helps university students form teams for competitions and projects using structured compatibility information.

## User flow

Sign Up + Profile -> Login -> Join / Recruit -> Search Competition -> Matching -> Human Final Decision

## Current architecture

Browser
-> Flask routes and business logic
-> SQLite database

### Main backend responsibilities

1. Create accounts and matching profiles
2. Authenticate users with hashed passwords and sessions
3. Search and display competitions
4. Create recruiting posts
5. Calculate compatibility between a user and a recruiting team
6. Rank teams for joiners
7. Rank applicants for recruiters
8. Store applications and shortlist actions

## Matching baseline

The current MVP uses an explainable rule-based baseline:

- Skills: up to 35 points
- Availability: 20 points
- Preferred role: 20 points
- Working style: 10 points
- Project goal / effort level: 15 points

The score is not a measure of human quality. It is only a compatibility signal against a specific team's stated needs.

## Human-in-the-loop rule

AI or matching logic can suggest and explain.
Students make the final choice.

## Security choices

- Passwords are hashed using Werkzeug
- Authentication state uses Flask sessions
- SQLite queries use parameterized values
- The MVP does not ask for payment information or other highly sensitive data

## Deliberate tradeoffs

- University email is required, but real verification email is not implemented
- Competition data is seeded locally instead of using an external API
- No chat or real-time notification system
- No complex AI agent or LLM matching yet
- Matching depends on self-reported profile data

## Open assumptions

- Compatibility at team formation matters to later collaboration
- Students are willing to provide structured profile information
- The selected criteria are useful enough for initial matching
- Explainable matching is more useful than unstructured teammate selection

## Next architecture step if the hypothesis survives

Add real university verification, richer team preferences, and a learned or LLM-assisted matching layer while keeping explanations and human final control.
