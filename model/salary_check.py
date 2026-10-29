import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import re

# Annual USD salary benchmarks by seniority
SALARY_BENCHMARKS = {
    "intern":   (15_000,  60_000),
    "fresher":  (40_000,  80_000),
    "junior":   (55_000, 100_000),
    "mid":      (80_000, 140_000),
    "senior":   (110_000, 220_000),
    "manager":  (120_000, 280_000),
    "director": (150_000, 400_000),
    "default":  (40_000,  150_000),
}

def extract_salary(text: str) -> float | None:
    """
    Extracts annual salary in USD from job text.
    Handles:
      - Hourly: $25/hr, $25 per hour, $25-$35/hr (annualized: rate * 40 * 52)
      - Weekly: $5,000 weekly, $5000/week, $5000 per week, $5000/wk (annualized: rate * 52)
      - Monthly: $3,000 monthly, $3000/month, $3000 per month, $3000/mo (annualized: rate * 12)
      - Annual ranges: $80k-$100k, $80,000 - $100,000
      - Annual single: $80k, $85000, 80k/year
      - Plain numbers with compensation context: salary 85000, 85000/yr, 85000 usd
    Ignores non-salary numbers like years (2022), zip codes (10001), and street addresses (12345).
    Returns annual float or None.
    """
    if not text or not isinstance(text, str):
        return None

    text = text.lower().replace(",", "")

    # 1. Hourly rate range  e.g. "$25 - $35/hr", "$25 to $35 per hour"
    hourly_range = re.search(
        r"\$?\s*(\d+\.?\d*)\s*(?:-|to)\s*\$?\s*(\d+\.?\d*)\s*(?:\/\s*(?:hr|hour)|per hour|hourly)\b",
        text
    )
    if hourly_range:
        low = float(hourly_range.group(1))
        high = float(hourly_range.group(2))
        return ((low + high) / 2) * 40 * 52

    # 2. Hourly rate single  e.g. "$25/hr", "$25 per hour", "25/hr", "hourly pay: $25"
    hourly = re.search(r"\$?\s*(\d+\.?\d*)\s*(?:\/\s*(?:hr|hour)|per hour|hourly)\b", text)
    if not hourly:
        hourly = re.search(r"\bhourly\s*(?:rate|pay|salary|wage)?\s*(?:is|of|:|-)?\s*\$?\s*(\d+\.?\d*)\b", text)
    if hourly:
        return float(hourly.group(1)) * 40 * 52   # 40hrs/week, 52 weeks

    # 3. Weekly rate range  e.g. "$1000 - $1500 weekly", "$1000 to $1500/week"
    weekly_range = re.search(
        r"\$?\s*(\d+\.?\d*)\s*(k)?\s*(?:-|to)\s*\$?\s*(\d+\.?\d*)\s*(k)?\s*(?:\/\s*(?:wk|week)|per week|weekly|a week)\b",
        text
    )
    if weekly_range:
        low = float(weekly_range.group(1)) * (1_000 if weekly_range.group(2) else 1)
        high = float(weekly_range.group(3)) * (1_000 if weekly_range.group(4) else 1)
        return ((low + high) / 2) * 52

    # 4. Weekly rate single  e.g. "$5,000 weekly", "$5000/week", "$5000 per week", "$5000/wk", "weekly pay: $1000"
    weekly = re.search(
        r"\$?\s*(\d+\.?\d*)\s*(k)?\s*(?:\/\s*(?:wk|week)|per week|weekly|a week)\b",
        text
    )
    if not weekly:
        weekly = re.search(
            r"\bweekly\s*(?:salary|pay|compensation|stipend|package|income)?\s*(?:is|of|:|-)?\s*\$?\s*(\d+\.?\d*)\s*(k)?\b",
            text
        )
    if weekly:
        val = float(weekly.group(1)) * (1_000 if weekly.group(2) else 1)
        return val * 52

    # 5. Monthly rate range  e.g. "$3000 - $4000 monthly", "$3000 to $4000/month"
    monthly_range = re.search(
        r"\$?\s*(\d+\.?\d*)\s*(k)?\s*(?:-|to)\s*\$?\s*(\d+\.?\d*)\s*(k)?\s*(?:\/\s*(?:mo|month)|per month|monthly|a month)\b",
        text
    )
    if monthly_range:
        low = float(monthly_range.group(1)) * (1_000 if monthly_range.group(2) else 1)
        high = float(monthly_range.group(3)) * (1_000 if monthly_range.group(4) else 1)
        return ((low + high) / 2) * 12

    # 6. Monthly rate single  e.g. "$3,000 monthly", "$3000/month", "$3000 per month", "$3000/mo", "monthly stipend: $2500"
    monthly = re.search(
        r"\$?\s*(\d+\.?\d*)\s*(k)?\s*(?:\/\s*(?:mo|month)|per month|monthly|a month)\b",
        text
    )
    if not monthly:
        monthly = re.search(
            r"\bmonthly\s*(?:salary|pay|compensation|stipend|package|income)?\s*(?:is|of|:|-)?\s*\$?\s*(\d+\.?\d*)\s*(k)?\b",
            text
        )
    if monthly:
        val = float(monthly.group(1)) * (1_000 if monthly.group(2) else 1)
        return val * 12

    # 7. Annual range with k  e.g. "$80k-$100k", "80k to 100k"
    range_k = re.search(r"\$?\s*(\d+\.?\d*)\s*k\s*(?:-|to)\s*\$?\s*(\d+\.?\d*)\s*k\b", text)
    if range_k:
        low  = float(range_k.group(1)) * 1_000
        high = float(range_k.group(2)) * 1_000
        return (low + high) / 2   # use midpoint

    # 8. Annual range plain with explicit dollar sign  e.g. "$80000 - $100000", "$80000 to 100000"
    range_dollar = re.search(r"\$\s*(\d{4,6})\s*(?:-|to)\s*\$?\s*(\d{4,6})", text)
    if not range_dollar:
        range_dollar = re.search(r"\$?\s*(\d{4,6})\s*(?:-|to)\s*\$\s*(\d{4,6})", text)
    if range_dollar:
        low  = float(range_dollar.group(1))
        high = float(range_dollar.group(2))
        return (low + high) / 2

    # 9. Annual range plain with explicit compensation context (e.g. "salary: 80000 - 100000", "80000 - 100000 / year")
    range_ctx = re.search(
        r"(?:salary|pay|compensation|stipend|ctc|package|remuneration)\s*(?:is|of|:|-)?\s*(\d{4,6})\s*(?:-|to)\s*(\d{4,6})",
        text
    )
    if not range_ctx:
        range_ctx = re.search(
            r"\b(\d{4,6})\s*(?:-|to)\s*(\d{4,6})\s*(?:\/\s*(?:yr|year)|per year|annually|annual|per annum|p\.a\.|usd)\b",
            text
        )
    if range_ctx:
        low  = float(range_ctx.group(1))
        high = float(range_ctx.group(2))
        return (low + high) / 2

    # 10. k shorthand  e.g. "$80k", "80k/year", excluding 401k
    for m in re.finditer(r"\$?\s*(\d+\.?\d*)\s*k\b", text):
        val = float(m.group(1))
        if val == 401:  # 401k retirement plan benefit
            continue
        return val * 1_000

    # 11. Plain dollar amount  e.g. "$85000"
    dollar = re.search(r"\$\s*(\d{4,6})\b", text)
    if dollar:
        return float(dollar.group(1))

    # 12. Plain number fallback WITH REQUIRED COMPENSATION CONTEXT
    # Prevents false positives from non-salary numbers (e.g. "Founded in 2022", "ZIP code 10001", "12345 Main St")
    # Context before: 'salary: 85000', 'pay of 85000', 'stipend 50000', 'earn 75000', etc.
    ctx_before = re.search(
        r"(?:(?:base|starting|annual|competitive|minimum|maximum)?\s*(?:salary|pay|compensation|stipend|package|ctc|remuneration)|earn(?:ing|ings)?|income)\s*(?:is|of|:|-|\b)\s*(?:usd\s*)?(\d{4,6})\b",
        text
    )
    if ctx_before:
        return float(ctx_before.group(1))

    # Context after: '85000 usd', '85000/yr', '85000 per year', '85000 annually'
    ctx_after = re.search(
        r"\b(\d{4,6})\s*(?:\/\s*(?:yr|year)|per year|annually|annual|per annum|p\.a\.|usd)\b",
        text
    )
    if ctx_after:
        return float(ctx_after.group(1))

    return None


def get_seniority(text: str) -> str:
    text_lower = text.lower()
    for key in SALARY_BENCHMARKS:
        if key in text_lower:
            return key
    return "default"


def check_salary_anomaly(text: str) -> dict:
    """
    Returns:
        is_anomaly  (bool)
        salary      (float | None)
        reason      (str)
        risk_score  (0?1 float)
    """
    salary = extract_salary(text)

    if salary is None:
        return {
            "is_anomaly": False,
            "salary": None,
            "reason": "No salary information found in the posting.",
            "risk_score": 0.0
        }

    seniority = get_seniority(text)
    low, high = SALARY_BENCHMARKS[seniority]

    # Unrealistically high ? classic scam bait
    if salary > high * 2.5:
        return {
            "is_anomaly": True,
            "salary": salary,
            "reason": f"Salary ${salary:,.0f}/yr is unrealistically high for a {seniority} role (expected up to ${high:,}).",
            "risk_score": 0.8
        }

    # Suspiciously low ? possible exploitation
    if salary < low * 0.4:
        return {
            "is_anomaly": True,
            "salary": salary,
            "reason": f"Salary ${salary:,.0f}/yr is suspiciously low for a {seniority} role (expected at least ${low:,}).",
            "risk_score": 0.5
        }

    return {
        "is_anomaly": False,
        "salary": salary,
        "reason": f"Salary ${salary:,.0f}/yr looks normal for a {seniority} role.",
        "risk_score": 0.0
    }
