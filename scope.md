# TeamMatch MVP Scope — Demo Day Candidate

## In scope

### Account / profile
- Sign up, login, logout
- Lightweight profile view
- Name, university, skills, availability, preferred role, working style, project goal
- Hashed passwords and feedback-learning preference

### Competition → team journey
- Current Korean competition discovery from TeamMatch PostgreSQL
- Keyword/category/status/deadline filters
- Original source links and real last-fetched timestamp
- Clear Join and Recruit actions
- Stable competition IDs and external-source provenance

### Matching / team decisions
- Existing five-factor compatibility model and active approved weights
- Session 8 mismatch penalties and 0–100 clamp
- Same-university-only filter on Join and Recruit
- University displayed as context, not compatibility
- Explainable factor breakdown derived from the real factor values
- Shortlist / Apply to Team
- Recruiter Accept applicant / Reject applicant

### Learning / safety
- Recommendation feedback kept visually and semantically separate from applications
- Session 7 rejection-reason learning loop and human approval
- Session 8 search guardrail
- No permanent teammate reputation

### Production
- Flask + Jinja + SQLAlchemy
- Railway PostgreSQL
- Gunicorn, `/healthz`, CSRF, secure cookies, env-based secrets/admin authorization
- Separate competition sync job; no crawler calls during page rendering

## Out of scope after Phase 4

- Global competition scraping
- Chat / messaging / real-time notifications
- Calendar or payments
- OAuth
- Personality testing
- University as a matching weight
- Fuzzy university inference such as `KU -> Korea University`
- Permanent teammate reputation or blacklist
- AI/LLM teammate scoring
- Automatic matching-weight approval
- Post-project surveillance/evaluation

After Phase 4 the product is feature-frozen for Demo Day; only bugs, broken deployment, misleading text and serious UX issues should be fixed.
