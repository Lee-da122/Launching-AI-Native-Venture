import re


def normalize_university(value):
    """Safe comparison normalization only: trim, collapse whitespace, casefold."""
    return re.sub(r"\s+", " ", (value or "").strip()).casefold()


def same_university(left, right):
    a = normalize_university(left)
    b = normalize_university(right)
    return bool(a and b and a == b)


def filter_teams_same_university(user_university, teams):
    return [team for team in teams if same_university(user_university, team.get("owner_university"))]


def filter_applicants_same_university(owner_university, applicants):
    return [applicant for applicant in applicants if same_university(owner_university, applicant.get("university"))]
