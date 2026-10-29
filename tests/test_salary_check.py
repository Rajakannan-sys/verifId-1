import os, sys
import pytest

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from model.salary_check import extract_salary, get_seniority, check_salary_anomaly, SALARY_BENCHMARKS


class TestAnnualSalaryExtraction:
    """Test annual salary formats, shorthands, and plain amounts."""

    @pytest.mark.parametrize("text,expected", [
        ("$85000", 85000.0),
        ("$85,000", 85000.0),
        ("Starting at $85000 per year", 85000.0),
        ("$80k", 80000.0),
        ("80k/year", 80000.0),
        ("Salary: 85000", 85000.0),
        ("Base pay of 75000", 75000.0),
        ("Earn 90000 annually", 90000.0),
        ("Compensation is 95000 usd", 95000.0),
        ("Annual stipend: 45000", 45000.0),
        ("CTC 85000", 85000.0),
    ])
    def test_single_annual_salaries(self, text, expected):
        assert extract_salary(text) == expected


class TestAnnualSalaryRanges:
    """Test annual salary range parsing."""

    @pytest.mark.parametrize("text,expected", [
        ("$80k-$100k", 90000.0),
        ("$80k to $100k", 90000.0),
        ("80k to 100k", 90000.0),
        ("$80,000 - $100,000", 90000.0),
        ("$80000 to 100000", 90000.0),
        ("Salary: 80000 - 100000", 90000.0),
        ("80000 - 100000 / year", 90000.0),
        ("Compensation: 70000 to 90000", 80000.0),
    ])
    def test_annual_ranges(self, text, expected):
        assert extract_salary(text) == expected


class TestHourlySalaryAnnualization:
    """Test hourly wage conversion (rate * 40 * 52)."""

    @pytest.mark.parametrize("text,expected", [
        ("$25/hr", 52000.0),
        ("$25 per hour", 52000.0),
        ("$25/hour", 52000.0),
        ("$25 hourly", 52000.0),
        ("Hourly pay: $30", 62400.0),
        ("$25 - $35/hr", 62400.0),
        ("$20 to $30 per hour", 52000.0),
    ])
    def test_hourly_rates(self, text, expected):
        assert extract_salary(text) == expected


class TestWeeklySalaryAnnualization:
    """Test weekly compensation conversion (rate * 52)."""

    @pytest.mark.parametrize("text,expected", [
        ("$5,000 weekly", 260000.0),
        ("$5000/week", 260000.0),
        ("$5000 per week", 260000.0),
        ("$5000/wk", 260000.0),
        ("Weekly pay: $1,000", 52000.0),
        ("Weekly salary of $1200", 62400.0),
        ("Earn $5k weekly", 260000.0),
        ("$1000 - $1500 weekly", 65000.0),
        ("$1000 to $1500/week", 65000.0),
    ])
    def test_weekly_rates(self, text, expected):
        assert extract_salary(text) == expected


class TestMonthlySalaryAnnualization:
    """Test monthly compensation conversion (rate * 12)."""

    @pytest.mark.parametrize("text,expected", [
        ("$3,000 monthly", 36000.0),
        ("$3000/month", 36000.0),
        ("$3000 per month", 36000.0),
        ("$3000/mo", 36000.0),
        ("Monthly stipend: $2,500", 30000.0),
        ("Monthly salary of $4000", 48000.0),
        ("Stipend $3k/month", 36000.0),
        ("$3000 - $4000 monthly", 42000.0),
        ("$3000 to $4000/month", 42000.0),
    ])
    def test_monthly_rates(self, text, expected):
        assert extract_salary(text) == expected


class TestFalsePositivePrevention:
    """Ensure years, zip codes, addresses, and other numbers are not treated as salaries."""

    @pytest.mark.parametrize("text", [
        "Company founded in 2022 and growing rapidly.",
        "Office located in ZIP code 10001.",
        "Headquarters at 12345 Main Street, Suite 400.",
        "Established in 1999 with over 15000 satisfied clients.",
        "Job ID 54321 - please mention this reference in your email.",
        "Work experience between 2018 and 2022 is preferred.",
        "Benefits include 401k matching and generous PTO.",
        "401(k) retirement plan with 5% employer match.",
        "Team of 5000 engineers worldwide.",
        "Call 18005550199 for inquiries.",
    ])
    def test_unrelated_numbers_return_none(self, text):
        assert extract_salary(text) is None


class TestSeniorityDetection:
    """Test role seniority keyword extraction."""

    @pytest.mark.parametrize("text,expected", [
        ("We are hiring a Summer Intern", "intern"),
        ("Fresher Software Engineer Opening", "fresher"),
        ("Junior Web Developer", "junior"),
        ("Mid level Data Scientist", "mid"),
        ("Senior Python Engineer", "senior"),
        ("Engineering Manager role", "manager"),
        ("Director of Engineering", "director"),
        ("Full Stack Developer", "default"),
    ])
    def test_seniority_benchmark_lookup(self, text, expected):
        assert get_seniority(text) == expected


class TestSalaryAnomalyDetection:
    """Test salary anomaly detection behavior and risk scores."""

    def test_no_salary_found(self):
        result = check_salary_anomaly("Software engineer role with python experience. Founded in 2020.")
        assert result["is_anomaly"] is False
        assert result["salary"] is None
        assert result["risk_score"] == 0.0
        assert "No salary information found" in result["reason"]

    def test_unrealistically_high_salary_weekly_intern_scam(self):
        # $5000 weekly = $260,000/year, intern benchmark max is $60,000 (high * 2.5 = 150,000)
        text = "Intern position. Earn $5,000 weekly guaranteed. No experience needed."
        result = check_salary_anomaly(text)
        assert result["is_anomaly"] is True
        assert result["salary"] == 260000.0
        assert result["risk_score"] == 0.8
        assert "unrealistically high" in result["reason"]
        assert "intern" in result["reason"]

    def test_unrealistically_high_salary_junior_role(self):
        # Junior max benchmark is $100,000 (high * 2.5 = $250,000)
        text = "Junior developer role with $300,000/yr base salary."
        result = check_salary_anomaly(text)
        assert result["is_anomaly"] is True
        assert result["salary"] == 300000.0
        assert result["risk_score"] == 0.8
        assert "unrealistically high" in result["reason"]

    def test_suspiciously_low_salary(self):
        # Senior min benchmark is $110,000 (low * 0.4 = $44,000)
        text = "Senior Software Architect with $20,000 annual salary."
        result = check_salary_anomaly(text)
        assert result["is_anomaly"] is True
        assert result["salary"] == 20000.0
        assert result["risk_score"] == 0.5
        assert "suspiciously low" in result["reason"]

    def test_normal_salary_senior_role(self):
        # Senior benchmark range: $110,000 - $220,000
        text = "Senior DevOps Engineer. Salary: $160,000 per year."
        result = check_salary_anomaly(text)
        assert result["is_anomaly"] is False
        assert result["salary"] == 160000.0
        assert result["risk_score"] == 0.0
        assert "looks normal" in result["reason"]

    def test_normal_salary_monthly_intern_stipend(self):
        # $3,000 monthly = $36,000/yr, which falls nicely within intern benchmark (15k - 60k)
        text = "Internship opportunity. Stipend is $3,000 monthly."
        result = check_salary_anomaly(text)
        assert result["is_anomaly"] is False
        assert result["salary"] == 36000.0
        assert result["risk_score"] == 0.0
        assert "looks normal" in result["reason"]
