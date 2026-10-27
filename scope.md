# MVP Scope

## In scope
### Account and profile
- Sign up / login / logout
- University email required
- Skills
- Availability + Flexible / Negotiable
- Preferred role
- Working style
- Project goal / effort level

### Competition flow
- Seeded list
- Competition search
- Competition selection

### Join a Team
- Explainable compatibility score
- Recommendation explanation
- Shortlist
- Apply
- Recommendation Accept/Reject feedback
- Optional feedback reason/comment

### Recruit a Team
- Create recruiting post
- Define team needs
- View and accept/reject applicants

### Session 7 learning loop
- Store recommendation feedback snapshots
- User opt-out for learning use
- Acceptance/rejection metrics
- Rejection reason counts
- Transparent reason -> matching-factor mapping
- Minimum 5-repeat threshold for a factor
- Normalized +5 percentage-point weight proposal
- Human Approve/Reject safety step
- Approved weights used by future recommendations
- Weight history
- Clearly labelled demo feedback

## Out of scope
- Real email verification
- OAuth
- Messaging
- Payments
- Real-time notifications
- Calendar integration
- External competition APIs
- LLM/model fine-tuning
- Permanent teammate reputation/quality scores
- Sensitive-characteristic inference
- Skill-development recommendations
- Actual post-project teamwork-success measurement

## Definition of Done
A user can use the original TeamMatch flow and can submit recommendation feedback. Founder review can summarize eligible feedback, generate a qualifying proposal, require human approval, update active normalized weights only after approval, and use the approved weights in later recommendations.
