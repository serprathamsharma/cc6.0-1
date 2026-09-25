"""Fixture loader for DEMO MODE record-and-replay."""
from __future__ import annotations

import json
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent.parent.parent.parent / "fixtures"

ENTITY_TO_SCENARIO: dict[str, str] = {
    "job_posting": "scenario_a",
    "sponsor": "scenario_b",
    "pricing_plan": "scenario_c",
}


def load_fixture(entity_type: str) -> list[dict]:
    """Load fixture records for an entity type."""
    scenario = ENTITY_TO_SCENARIO.get(entity_type, "scenario_a")
    path = FIXTURES_DIR / scenario / "records.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    # Fallback: return embedded minimal fixtures
    return _builtin_fixtures(entity_type)


def _builtin_fixtures(entity_type: str) -> list[dict]:
    if entity_type == "job_posting":
        return _jobs_fixture()
    elif entity_type == "sponsor":
        return _sponsors_fixture()
    else:
        return _pricing_fixture()


def _jobs_fixture() -> list[dict]:
    companies = [
        ("Swiggy", "Bangalore", "ML Platform"), ("Razorpay", "Bangalore", "Data Science"),
        ("CRED", "Bangalore", "AI Research"), ("Zepto", "Mumbai", "Machine Learning"),
        ("Groww", "Bangalore", "NLP Engineering"), ("PhonePe", "Bangalore", "Computer Vision"),
        ("Meesho", "Bangalore", "Recommendation Systems"), ("Ola", "Bangalore", "Autonomous AI"),
        ("Zomato", "Gurugram", "Personalization ML"), ("Paytm", "Noida", "Fraud Detection AI"),
        ("BrowserStack", "Mumbai", "MLOps"), ("Freshworks", "Chennai", "NLP"),
        ("Chargebee", "Chennai", "Data Engineering"), ("Postman", "Bangalore", "AI Features"),
        ("HasuraDB", "Bangalore", "LLM Engineering"), ("Setu", "Bangalore", "Data Science"),
        ("Juspay", "Bangalore", "ML Infra"), ("Darwinbox", "Hyderabad", "NLP"),
        ("Leadsquared", "Bangalore", "AI Product"), ("Unacademy", "Bangalore", "Personalized Learning AI"),
        ("Vedantu", "Bangalore", "Computer Vision"), ("Byju's", "Bangalore", "Adaptive AI"),
        ("Nykaa", "Mumbai", "Recommendation ML"), ("Mamaearth", "Gurugram", "Data Analyst AI"),
        ("ShareChat", "Bangalore", "Content AI"), ("Dailyhunt", "Bangalore", "NLP"),
        ("InMobi", "Bangalore", "Ad ML"), ("CleverTap", "Mumbai", "Predictive ML"),
        ("MoEngage", "Bangalore", "ML Engineering"), ("WebEngage", "Mumbai", "Data Science"),
        ("Lenskart", "Gurugram", "Computer Vision"), ("Boat", "Delhi", "AI Analytics"),
        ("Cars24", "Gurugram", "Pricing ML"), ("OLX", "Gurugram", "NLP Search"),
        ("Quikr", "Bangalore", "ML Platform"), ("Urban Company", "Gurugram", "ML Ops"),
        ("HealthifyMe", "Bangalore", "Health AI"), ("Practo", "Bangalore", "Medical NLP"),
        ("Pristyn Care", "Gurugram", "Healthcare AI"), ("Innovaccer", "Noida", "Healthcare ML"),
        ("Druva", "Pune", "Cloud ML"), ("Icertis", "Pune", "Contract AI"),
        ("Whatfix", "Bangalore", "AI Guidance"), ("Kissflow", "Chennai", "Process AI"),
        ("Zoho", "Chennai", "AI Tools"), ("Infosys BPM", "Bangalore", "Gen AI"),
        ("Persistent", "Pune", "AI Research"), ("Mphasis", "Bangalore", "ML Consulting"),
        ("WNS", "Mumbai", "Data Science"), ("EXL", "Noida", "Advanced Analytics"),
    ]
    records = []
    for i, (company, city, role) in enumerate(companies):
        src_url = f"https://internshala.com/internship/detail/ai-ml-intern-{company.lower().replace(' ', '-')}-{i}"
        stipend = f"₹{8000 + i * 500}/month"
        skills = "Python, TensorFlow, PyTorch, SQL"
        apply_link = f"https://internshala.com/apply/{1000 + i}"
        records.append({
            "title": f"{role} Intern",
            "company": company,
            "location": f"{city}, India",
            "stipend": stipend,
            "skills": skills,
            "apply_link": apply_link,
            "posted_at": "2024-01-15",
            "_source_url": src_url,
            "_quality_score": 82.0 + (i % 15),
            "_extraction_method": "fixture",
            f"_evidence_title": f"{role} Intern at {company}",
            f"_evidence_company": f"Posted by {company}",
            f"_evidence_stipend": f"Stipend: {stipend}",
            "_verified_title": True,
            "_verified_company": True,
        })
    return records


def _sponsors_fixture() -> list[dict]:
    sponsors = [
        ("Google", "Google I/O Extended Delhi 2024", "Title Sponsor", "https://developers.google.com/contact"),
        ("Microsoft", "HackCBS 7.0", "Gold Sponsor", "https://microsoft.com/contact"),
        ("Amazon", "HackDelhi", "Title Sponsor", "https://aws.amazon.com/contact-us"),
        ("Flipkart", "HackWithInfy", "Silver Sponsor", "https://www.flipkart.com/about"),
        ("Infosys", "SIH 2024 Regional", "Platinum Sponsor", "https://infosys.com/contact"),
        ("TCS", "TCS Codathon", "Title Sponsor", "https://tcs.com/contact"),
        ("Wipro", "Wipro Techathon", "Gold Sponsor", "https://wipro.com/contact"),
        ("HCL", "HCL HackIIIT Delhi", "Silver Sponsor", "https://hcltech.com/contact"),
        ("PhonePe", "AngelHack Delhi", "Gold Sponsor", "https://phonepe.com/business"),
        ("Paytm", "HackNCR 2024", "Fintech Sponsor", "https://paytm.com/business"),
        ("Razorpay", "ETHIndia Delhi", "Gold Sponsor", "https://razorpay.com/contact"),
        ("CRED", "Delhi Open Source Summit", "Community Sponsor", "https://cred.club"),
        ("Swiggy", "Build for Bharat", "Bronze Sponsor", "https://swiggy.com"),
        ("Zomato", "Hack4Good Delhi", "Food Sponsor", "https://zomato.com"),
        ("OLA", "Mobility Hackathon NCR", "Title Sponsor", "https://olaelectric.com"),
        ("Uber", "Uber HackTag Delhi", "Gold Sponsor", "https://uber.com/contact"),
        ("Myntra", "Fashion Tech Hack", "Silver Sponsor", "https://myntra.com"),
        ("Nykaa", "Beauty Tech Summit", "Bronze Sponsor", "https://nykaa.com"),
        ("Cars24", "AutoTech Hack", "Title Sponsor", "https://cars24.com/contact"),
        ("PolicyBazaar", "InsureTech Hackathon", "Gold Sponsor", "https://policybazaar.com"),
        ("MakeMyTrip", "TravelTech Hack", "Silver Sponsor", "https://makemytrip.com"),
        ("Yatra", "Tourism Innovation Hack", "Bronze Sponsor", "https://yatra.com"),
        ("BharatPe", "BharatPe HackFest", "Title Sponsor", "https://bharatpe.com/contact"),
        ("Slice", "FinHack NCR", "Gold Sponsor", "https://sliceit.com"),
        ("Jupiter", "NeoBank Hackathon", "Silver Sponsor", "https://jupiter.money"),
        ("Fi Money", "Fi HackFest", "Gold Sponsor", "https://fi.money"),
        ("Groww", "InvestTech Hack", "Bronze Sponsor", "https://groww.in"),
        ("Zerodha", "FinTech Conclave", "Community Sponsor", "https://zerodha.com"),
        ("Upstox", "Trading Hack Delhi", "Silver Sponsor", "https://upstox.com"),
        ("AngelOne", "AngelHack Noida", "Gold Sponsor", "https://angelone.in"),
        ("ITC Infotech", "ITC Codeathon", "Title Sponsor", "https://itcinfotech.com"),
        ("Publicis Sapient", "PS Hackathon NCR", "Gold Sponsor", "https://publicissapient.com"),
        ("Genpact", "DataHack Gurugram", "Silver Sponsor", "https://genpact.com"),
        ("EXL", "Analytics Hackathon", "Bronze Sponsor", "https://exlservice.com"),
        ("WNS", "BPO Hack", "Community Sponsor", "https://wns.com"),
        ("Mphasis", "CloudHack Delhi", "Gold Sponsor", "https://mphasis.com"),
        ("Persistent", "Open Source Fest", "Silver Sponsor", "https://persistent.com"),
        ("NIIT", "EdTech Hackathon", "Bronze Sponsor", "https://niit.com"),
        ("upGrad", "upGrad Hack", "Title Sponsor", "https://upgrad.com"),
        ("Coursera", "LearnTech Hack", "Global Sponsor", "https://coursera.org"),
        ("Indeed", "HireHack Delhi", "Hiring Sponsor", "https://indeed.com"),
        ("LinkedIn", "LinkedIn HackDay NCR", "Title Sponsor", "https://linkedin.com"),
        ("Naukri", "Naukri Hack", "Gold Sponsor", "https://naukri.com"),
        ("Internshala", "InternHack", "Community Sponsor", "https://internshala.com"),
        ("Unstop", "D2C Hack", "Bronze Sponsor", "https://unstop.com"),
        ("HackerEarth", "HackerEarth Sprint", "Platform Sponsor", "https://hackerearth.com"),
        ("HackerRank", "HackerRank Hackathon", "Platform Sponsor", "https://hackerrank.com"),
        ("CodeChef", "Lunchtime Hack", "Community Sponsor", "https://codechef.com"),
        ("Codeforces", "CF Hack NCR", "Community Sponsor", "https://codeforces.com"),
        ("GeeksforGeeks", "GFG Hacks", "Content Sponsor", "https://geeksforgeeks.org"),
    ]
    records = []
    for i, (company, event, tier, contact) in enumerate(sponsors):
        src = f"https://devfolio.co/hackathons/{event.lower().replace(' ', '-')}-{i}"
        records.append({
            "company_name": company,
            "event_name": event,
            "sponsorship_tier": tier,
            "contact_page": contact,
            "event_date": "2024-01-20",
            "location": "Delhi/NCR",
            "_source_url": src,
            "_quality_score": 78.0 + (i % 20),
            "_extraction_method": "fixture",
            "_evidence_company_name": f"Sponsored by {company}",
            "_evidence_sponsorship_tier": f"{tier}: {company}",
            "_verified_company_name": True,
            "_verified_sponsorship_tier": True,
        })
    return records


def _pricing_fixture() -> list[dict]:
    tools = [
        ("Asana", "Free", "$0", None, "Basic tasks, 15 users", "https://asana.com/pricing"),
        ("Asana", "Starter", "$10.99", "$131.88", "Timeline, dashboards", "https://asana.com/pricing"),
        ("Asana", "Advanced", "$24.99", "$299.88", "Portfolios, goals", "https://asana.com/pricing"),
        ("Notion", "Free", "$0", None, "Basic blocks, 1 guest", "https://notion.so/pricing"),
        ("Notion", "Plus", "$10", "$96", "Unlimited blocks, 100 guests", "https://notion.so/pricing"),
        ("Notion", "Business", "$18", "$180", "SAML SSO, audit log", "https://notion.so/pricing"),
        ("Monday.com", "Free", "$0", None, "2 seats", "https://monday.com/pricing"),
        ("Monday.com", "Basic", "$9", "$108", "5 GB storage", "https://monday.com/pricing"),
        ("Monday.com", "Standard", "$12", "$144", "Timeline, Gantt", "https://monday.com/pricing"),
        ("Monday.com", "Pro", "$19", "$228", "Time tracking, automations", "https://monday.com/pricing"),
        ("ClickUp", "Free", "$0", None, "100MB storage", "https://clickup.com/pricing"),
        ("ClickUp", "Unlimited", "$7", "$84", "Unlimited storage", "https://clickup.com/pricing"),
        ("ClickUp", "Business", "$12", "$144", "Advanced automations", "https://clickup.com/pricing"),
        ("Linear", "Free", "$0", None, "250 issues", "https://linear.app/pricing"),
        ("Linear", "Standard", "$8", "$80", "Unlimited issues", "https://linear.app/pricing"),
        ("Linear", "Plus", "$16", "$160", "Admin features", "https://linear.app/pricing"),
        ("Trello", "Free", "$0", None, "10 boards", "https://trello.com/pricing"),
        ("Trello", "Standard", "$5", "$60", "Custom fields", "https://trello.com/pricing"),
        ("Trello", "Premium", "$10", "$120", "Dashboard view", "https://trello.com/pricing"),
        ("Basecamp", "Basecamp", "$15/user", "$180/user", "Full features", "https://basecamp.com/pricing"),
        ("Basecamp", "Basecamp Pro Unlimited", "$299/month", "$3,588/year", "Unlimited users", "https://basecamp.com/pricing"),
        ("Jira", "Free", "$0", None, "10 users", "https://atlassian.com/software/jira/pricing"),
        ("Jira", "Standard", "$8.15", "$84", "Advanced permissions", "https://atlassian.com/software/jira/pricing"),
        ("Jira", "Premium", "$16", "$168", "AI features", "https://atlassian.com/software/jira/pricing"),
        ("Wrike", "Free", "$0", None, "5 users", "https://wrike.com/price"),
        ("Wrike", "Team", "$9.80", "$117.60", "Interactive Gantt", "https://wrike.com/price"),
        ("Wrike", "Business", "$24.80", "$297.60", "Advanced analytics", "https://wrike.com/price"),
        ("Smartsheet", "Pro", "$7", "$84", "20 sheets", "https://smartsheet.com/pricing"),
        ("Smartsheet", "Business", "$25", "$300", "Unlimited sheets", "https://smartsheet.com/pricing"),
        ("Airtable", "Free", "$0", None, "1,200 records", "https://airtable.com/pricing"),
        ("Airtable", "Team", "$20", "$240", "50,000 records", "https://airtable.com/pricing"),
        ("Airtable", "Business", "$45", "$540", "Advanced features", "https://airtable.com/pricing"),
        ("Teamwork", "Free", "$0", None, "5 users", "https://teamwork.com/pricing"),
        ("Teamwork", "Starter", "$5.99", "$71.88", "Task dependencies", "https://teamwork.com/pricing"),
        ("Teamwork", "Deliver", "$9.99", "$119.88", "Portfolio management", "https://teamwork.com/pricing"),
        ("Nifty", "Free", "$0", None, "2 projects", "https://niftypm.com/pricing"),
        ("Nifty", "Starter", "$39", "$468", "40 projects", "https://niftypm.com/pricing"),
        ("Nifty", "Pro", "$79", "$948", "Unlimited projects", "https://niftypm.com/pricing"),
        ("Hive", "Free", "$0", None, "10 users", "https://hive.com/pricing"),
        ("Hive", "Starter", "$5", "$60", "Core features", "https://hive.com/pricing"),
        ("Hive", "Teams", "$12", "$144", "Automations, time tracking", "https://hive.com/pricing"),
        ("ProofHub", "Essential", "$45", "$360", "40 projects", "https://proofhub.com/pricing"),
        ("ProofHub", "Ultimate Control", "$89", "$708", "Unlimited projects", "https://proofhub.com/pricing"),
        ("Zoho Projects", "Free", "$0", None, "3 users", "https://zoho.com/projects/pricing.html"),
        ("Zoho Projects", "Premium", "$5", "$60", "Time tracking", "https://zoho.com/projects/pricing.html"),
        ("Zoho Projects", "Enterprise", "$10", "$120", "Custom roles", "https://zoho.com/projects/pricing.html"),
        ("Todoist", "Free", "$0", None, "5 projects", "https://todoist.com/pricing"),
        ("Todoist", "Pro", "$4", "$48", "300 projects", "https://todoist.com/pricing"),
        ("Todoist", "Business", "$6", "$72", "Team workspace", "https://todoist.com/pricing"),
        ("Notion (AI)", "Plus+AI", "$16", "$160", "AI writing assistant", "https://notion.so/pricing"),
        ("Coda", "Free", "$0", None, "Limited docs", "https://coda.io/pricing"),
    ]
    records = []
    for i, (product, plan, monthly, annual, features, url) in enumerate(tools):
        records.append({
            "product_name": product,
            "plan_name": plan,
            "price_monthly": monthly,
            "price_annual": annual,
            "features": features,
            "pricing_url": url,
            "currency": "USD",
            "_source_url": url,
            "_quality_score": 88.0 + (i % 10),
            "_extraction_method": "fixture",
            "_evidence_plan_name": f"{plan} plan - {monthly}/month",
            "_evidence_price_monthly": f"{monthly} per user per month",
            "_verified_plan_name": True,
            "_verified_price_monthly": True,
        })
    return records
