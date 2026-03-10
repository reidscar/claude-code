#!/usr/bin/env python3
"""
Veston Campaign Tool
====================
Automates the cold email pipeline: pull leads from DropLeads,
deduplicate against a suppression list, create an Instantly campaign,
and load the leads in.

Usage:
    python veston_campaign.py              # Normal run
    python veston_campaign.py --dry-run    # Test without creating anything
"""

import argparse
import csv
import json
import os
import sys
import time
from datetime import date, datetime, timedelta

try:
    import requests
except ImportError:
    print("The 'requests' library is required. Install it with:")
    print("  pip install requests")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # If python-dotenv isn't installed, try loading .env manually
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()

# ---------------------------------------------------------------------------
# Configuration from environment
# ---------------------------------------------------------------------------
DROPLEADS_API_KEY = os.environ.get("DROPLEADS_API_KEY", "")
DROPLEADS_BASE_URL = os.environ.get("DROPLEADS_BASE_URL", "https://api.dropleads.io/v1")
INSTANTLY_API_KEY = os.environ.get("INSTANTLY_API_KEY", "")
INSTANTLY_BASE_URL = os.environ.get("INSTANTLY_BASE_URL", "https://api.instantly.ai/api/v2")

SUPPRESSION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "suppression_list.csv")

# ---------------------------------------------------------------------------
# Blocked countries
# ---------------------------------------------------------------------------
BLOCKED_COUNTRIES = {"germany", "france", "pakistan", "south africa", "nigeria"}
BLOCKED_MSG = (
    "This country is excluded from Veston campaigns. Active markets are: "
    "UK, Netherlands, Canada, Australia, New Zealand, and rest of Europe "
    "excluding Germany and France."
)

# ---------------------------------------------------------------------------
# Vertical definitions — filters for each vertical + country combo
# ---------------------------------------------------------------------------
VERTICALS = {
    "recruitment": {
        "label": "Recruitment",
        "filters": {
            "united kingdom": {
                "industry": "staffing/recruiting",
                "headcount_min": 10, "headcount_max": 60,
                "titles": ["Founder", "CEO", "Managing Director", "Owner"],
            },
            "netherlands": {
                "industry": "staffing/recruiting",
                "headcount_min": 10, "headcount_max": 40,
                "titles": ["Oprichter", "CEO", "Directeur", "DGA"],
            },
        },
    },
    "agencies": {
        "label": "Agencies",
        "filters": {
            "united kingdom": {
                "industry": "marketing/advertising/creative",
                "headcount_min": 20, "headcount_max": 80,
                "titles": ["Founder", "CEO", "Managing Director", "Owner"],
            },
            "netherlands": {
                "industry": "marketing/advertising",
                "headcount_min": 15, "headcount_max": 60,
                "titles": ["Oprichter", "CEO", "Directeur", "Eigenaar"],
            },
        },
    },
    "ecommerce": {
        "label": "Ecommerce",
        "filters": {
            "united kingdom": {
                "industry": "retail/e-commerce",
                "headcount_min": 15, "headcount_max": 80,
                "titles": ["Founder", "CEO", "Managing Director", "Owner"],
            },
            "netherlands": {
                "industry": "retail/e-commerce",
                "headcount_min": 10, "headcount_max": 60,
                "titles": ["Oprichter", "CEO", "Directeur", "Eigenaar"],
            },
        },
    },
    "saas": {
        "label": "SaaS",
        "filters": {
            "united kingdom": {
                "industry": "software/SaaS",
                "headcount_min": 10, "headcount_max": 60,
                "titles": ["Founder", "CEO", "CTO"],
            },
            "netherlands": {
                "industry": "software/SaaS",
                "headcount_min": 10, "headcount_max": 50,
                "titles": ["Oprichter", "CEO", "Founder"],
            },
        },
    },
    "consulting": {
        "label": "Consulting",
        "filters": {
            "united kingdom": {
                "industry": "consulting/professional services",
                "headcount_min": 5, "headcount_max": 30,
                "titles": ["Founder", "Managing Partner", "CEO"],
            },
            "netherlands": {
                "industry": "consulting",
                "headcount_min": 5, "headcount_max": 30,
                "titles": ["Oprichter", "Directeur", "Managing Partner"],
            },
        },
    },
    "it_services": {
        "label": "IT Services",
        "filters": {
            "united kingdom": {
                "industry": "IT services/managed services",
                "headcount_min": 20, "headcount_max": 100,
                "titles": ["Founder", "CEO", "Managing Director"],
            },
        },
    },
    "content_media": {
        "label": "Content/Media",
        "filters": {
            "united kingdom": {
                "industry": "media/education/publishing",
                "headcount_min": 5, "headcount_max": 30,
                "titles": ["Founder", "CEO", "Creator"],
            },
        },
    },
}

# Countries where ALL verticals share the same generic filters
GENERIC_COUNTRY_FILTERS = {
    "canada": {
        "headcount_min": 10, "headcount_max": 60,
        "titles": ["Founder", "CEO", "Owner", "President"],
    },
    "australia": {
        "headcount_min": 10, "headcount_max": 60,
        "titles": ["Founder", "CEO", "Managing Director", "Owner"],
    },
    "new zealand": {
        "headcount_min": 10, "headcount_max": 60,
        "titles": ["Founder", "CEO", "Managing Director", "Owner"],
    },
}

# Country display name -> DropLeads country value
COUNTRY_MAP = {
    "uk": "United Kingdom",
    "united kingdom": "United Kingdom",
    "netherlands": "Netherlands",
    "nl": "Netherlands",
    "canada": "Canada",
    "ca": "Canada",
    "australia": "Australia",
    "au": "Australia",
    "new zealand": "New Zealand",
    "nz": "New Zealand",
}

# Timezone per country
COUNTRY_TIMEZONE = {
    "united kingdom": "Europe/London",
    "netherlands": "Europe/Amsterdam",
    "canada": "America/Toronto",
    "australia": "Australia/Sydney",
    "new zealand": "Pacific/Auckland",
}

# Demonym and savings range per country (for email templates)
COUNTRY_DEMONYM = {
    "united kingdom": "UK",
    "netherlands": "Dutch",
    "canada": "Canadian",
    "australia": "Australian",
    "new zealand": "New Zealand",
}

COUNTRY_SAVINGS = {
    "united kingdom": "GBP 68,000-94,000",
    "netherlands": "EUR 80,000-200,000",
    "canada": "CAD 90,000-250,000",
    "australia": "AUD 90,000-200,000",
    "new zealand": "NZD 80,000-180,000",
}


# ---------------------------------------------------------------------------
# Helper: ask user a question with numbered options
# ---------------------------------------------------------------------------
def ask_choice(prompt, options):
    """Display numbered options and return the user's choice."""
    print(f"\n{prompt}")
    for i, opt in enumerate(options, 1):
        print(f"  {i}. {opt}")
    while True:
        raw = input("\nYour choice (number or text): ").strip()
        # Try as a number first
        try:
            idx = int(raw)
            if 1 <= idx <= len(options):
                return options[idx - 1]
        except ValueError:
            pass
        # Try as text match
        lower = raw.lower()
        for opt in options:
            if lower == opt.lower() or lower in opt.lower():
                return opt
        print(f"  Please pick a number from 1-{len(options)} or type the name.")


def ask_text(prompt, default=None):
    """Ask for free text input with an optional default."""
    suffix = f" [{default}]" if default else ""
    raw = input(f"\n{prompt}{suffix}: ").strip()
    return raw if raw else default


# ---------------------------------------------------------------------------
# Suppression list management
# ---------------------------------------------------------------------------
def load_suppression_list():
    """Load all previously contacted emails from the suppression file."""
    emails = set()
    if os.path.exists(SUPPRESSION_FILE):
        with open(SUPPRESSION_FILE, "r", newline="") as f:
            reader = csv.reader(f)
            for row in reader:
                if row:
                    emails.add(row[0].strip().lower())
    return emails


def save_to_suppression_list(new_emails):
    """Append new emails to the suppression file."""
    with open(SUPPRESSION_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        for email in new_emails:
            writer.writerow([email.lower()])


# ---------------------------------------------------------------------------
# DropLeads API
# ---------------------------------------------------------------------------
def dropleads_search(filters, country, limit, dry_run=False):
    """
    Search the DropLeads database for leads matching the given filters.

    DropLeads API uses a POST /search endpoint for database queries.
    If that endpoint isn't available, falls back to a GET /leads endpoint.
    The exact parameter names are mapped from our filter config.
    """
    if dry_run:
        print("\n[DRY RUN] Would search DropLeads with these filters:")
        print(f"  Country: {country}")
        print(f"  Industry: {filters.get('industry', 'any')}")
        print(f"  Headcount: {filters.get('headcount_min', '?')}-{filters.get('headcount_max', '?')}")
        print(f"  Titles: {', '.join(filters.get('titles', []))}")
        print(f"  Limit: {limit}")
        # Return sample data for dry run
        return _generate_sample_leads(limit, country)

    headers = {
        "Authorization": f"Bearer {DROPLEADS_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    # Build the search payload — try the POST /search or /people/search endpoint
    # DropLeads' database search likely uses these field names based on their
    # website descriptions of filtering by industry, headcount, titles, etc.
    payload = {
        "country": country,
        "limit": limit,
    }

    # Add industry filter if present
    if "industry" in filters:
        payload["industry"] = filters["industry"]

    # Add headcount range
    if "headcount_min" in filters:
        payload["employee_count_min"] = filters["headcount_min"]
        payload["headcount_min"] = filters["headcount_min"]
    if "headcount_max" in filters:
        payload["employee_count_max"] = filters["headcount_max"]
        payload["headcount_max"] = filters["headcount_max"]

    # Add job title filters
    if "titles" in filters:
        payload["job_titles"] = filters["titles"]
        payload["titles"] = filters["titles"]

    # Try multiple possible endpoint patterns that DropLeads might use
    endpoints_to_try = [
        ("POST", f"{DROPLEADS_BASE_URL}/search"),
        ("POST", f"{DROPLEADS_BASE_URL}/people/search"),
        ("POST", f"{DROPLEADS_BASE_URL}/leads/search"),
        ("GET",  f"{DROPLEADS_BASE_URL}/leads"),
        ("GET",  f"{DROPLEADS_BASE_URL}/people"),
        ("GET",  f"{DROPLEADS_BASE_URL}/database/search"),
    ]

    last_error = None
    for method, url in endpoints_to_try:
        try:
            if method == "POST":
                resp = requests.request(method, url, headers=headers, json=payload, timeout=30)
            else:
                # For GET, convert payload to query params
                params = {}
                for k, v in payload.items():
                    if isinstance(v, list):
                        params[k] = ",".join(v)
                    else:
                        params[k] = v
                resp = requests.request(method, url, headers=headers, params=params, timeout=30)

            if resp.status_code == 200:
                data = resp.json()
                # Handle various response formats
                if isinstance(data, list):
                    leads = data
                elif isinstance(data, dict):
                    # Look for common response wrappers
                    leads = (
                        data.get("data")
                        or data.get("results")
                        or data.get("leads")
                        or data.get("people")
                        or data.get("records")
                        or []
                    )
                else:
                    leads = []
                return _normalize_leads(leads)
            elif resp.status_code == 404:
                # Endpoint doesn't exist, try next one
                last_error = f"{url} returned 404"
                continue
            elif resp.status_code == 401:
                print(f"\nERROR: DropLeads authentication failed (401). Check your API key.")
                return []
            elif resp.status_code == 403:
                print(f"\nERROR: DropLeads access denied (403). Your plan may not include API access.")
                return []
            else:
                last_error = f"{url} returned {resp.status_code}: {resp.text[:200]}"
                continue

        except requests.exceptions.RequestException as e:
            last_error = f"Request to {url} failed: {e}"
            continue

    # If none of the endpoints worked, show the error and return empty
    print(f"\nERROR: Could not find a working DropLeads search endpoint.")
    print(f"Last error: {last_error}")
    print(f"\nThe DropLeads API may only support email-finder lookups (by name + domain),")
    print(f"not database searching. You may need to:")
    print(f"  1. Check your DropLeads dashboard for API documentation")
    print(f"  2. Contact DropLeads support to confirm database search API access")
    print(f"  3. Export leads manually from the DropLeads web interface and use the")
    print(f"     --csv-import flag to load them (see below)")
    return []


def _normalize_leads(raw_leads):
    """Normalize lead data from DropLeads into a consistent format."""
    normalized = []
    for lead in raw_leads:
        if not isinstance(lead, dict):
            continue
        # Map common field name variations to our standard format
        email = (
            lead.get("email")
            or lead.get("work_email")
            or lead.get("verified_email")
            or lead.get("business_email")
            or ""
        )
        if not email:
            # Skip leads without an email
            continue
        normalized.append({
            "email": email.strip().lower(),
            "first_name": lead.get("first_name") or lead.get("firstName") or "",
            "last_name": lead.get("last_name") or lead.get("lastName") or "",
            "company_name": (
                lead.get("company_name")
                or lead.get("company")
                or lead.get("organization")
                or ""
            ),
            "website": (
                lead.get("website")
                or lead.get("company_website")
                or lead.get("domain")
                or ""
            ),
            "title": lead.get("title") or lead.get("job_title") or "",
        })
    return normalized


def _generate_sample_leads(count, country):
    """Generate sample leads for --dry-run testing."""
    sample_count = min(count, 10)  # Show max 10 in dry run
    leads = []
    first_names = ["James", "Sarah", "Michael", "Emma", "David",
                   "Lisa", "Robert", "Anna", "Thomas", "Maria"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones",
                  "Wilson", "Taylor", "Davies", "Evans", "Clark"]
    for i in range(sample_count):
        leads.append({
            "email": f"{first_names[i].lower()}.{last_names[i].lower()}@example-{i}.com",
            "first_name": first_names[i],
            "last_name": last_names[i],
            "company_name": f"Sample Co {i+1}",
            "website": f"https://example-{i}.com",
            "title": "CEO",
        })
    return leads


# ---------------------------------------------------------------------------
# CSV import (fallback if DropLeads search isn't available)
# ---------------------------------------------------------------------------
def import_leads_from_csv(filepath):
    """
    Import leads from a CSV file as a fallback.
    Expected columns: email, first_name, last_name, company_name, website
    """
    leads = []
    with open(filepath, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            email = row.get("email", "").strip()
            if not email:
                continue
            leads.append({
                "email": email.lower(),
                "first_name": row.get("first_name", ""),
                "last_name": row.get("last_name", ""),
                "company_name": row.get("company_name", row.get("company", "")),
                "website": row.get("website", row.get("domain", "")),
                "title": row.get("title", row.get("job_title", "")),
            })
    return leads


# ---------------------------------------------------------------------------
# Instantly API V2
# ---------------------------------------------------------------------------
def build_email_sequences(country_key):
    """Build the 4-email sequence with country-specific variables."""
    demonym = COUNTRY_DEMONYM.get(country_key, "")
    savings = COUNTRY_SAVINGS.get(country_key, "")

    # Email 1 — Day 0
    email1_subject = "{{firstName}}, international structuring question"
    email1_body = (
        "Hi {{firstName}},\n\n"
        f"I work with {demonym} business owners who want to restructure their "
        "profit centre under UAE management.\n\n"
        "Through a properly governed structure, it is possible to operate at an "
        "effective corporate rate of 9% without relocating, changing your business "
        "model, or disrupting operations.\n\n"
        "The UAE has 137 double tax treaties that provide the legal basis. "
        "Worth a 15-minute consultation?\n\n"
        "Reid, Veston Partners\n\n"
        "This email is a commercial communication from Veston Partners. "
        "If you do not wish to receive further correspondence, please reply "
        "with 'unsubscribe' and we will remove you immediately."
    )

    # Email 2 — Day 3 (wait 3 days after email 1)
    email2_subject = "Re: international structuring"
    email2_body = (
        "{{firstName}}, the difference between a compliant structure and an "
        "exposed one is governance.\n\n"
        "We provide a UAE-based management committee, documented decision authority, "
        "monthly management minutes, and annual substance certification.\n\n"
        "Our clients do not just have a Dubai company. They have an institutionally "
        "managed, treaty-compliant structure.\n\n"
        "Happy to explain in 15 minutes.\n\n"
        "Reid"
    )

    # Email 3 — Day 7 (wait 4 days after email 2)
    email3_subject = "potential improvement in retained capital"
    email3_body = (
        "{{firstName}}, for a " + demonym + " business at your scale, the difference "
        "between the current position and a managed UAE structure is typically "
        + savings + " per year in retained capital.\n\n"
        "Subject to individual circumstances. Worth a conversation?\n\n"
        "Reid"
    )

    # Email 4 — Day 14 (wait 7 days after email 3)
    email4_subject = "closing your file"
    email4_body = (
        "Have not heard back. Closing your file. If this becomes relevant, "
        "reply any time.\n\n"
        "Reid"
    )

    sequences = [
        {
            "steps": [
                {
                    "type": "email",
                    "delay": 0,
                    "variants": [{"subject": email1_subject, "body": email1_body}],
                },
                {
                    "type": "email",
                    "delay": 3,
                    "variants": [{"subject": email2_subject, "body": email2_body}],
                },
                {
                    "type": "email",
                    "delay": 4,
                    "variants": [{"subject": email3_subject, "body": email3_body}],
                },
                {
                    "type": "email",
                    "delay": 7,
                    "variants": [{"subject": email4_subject, "body": email4_body}],
                },
            ]
        }
    ]
    return sequences


def create_instantly_campaign(name, country_key, dry_run=False):
    """
    Create a new campaign in Instantly with the correct schedule and email sequence.
    Returns the campaign ID on success, or None on failure.
    """
    timezone = COUNTRY_TIMEZONE.get(country_key, "Europe/London")
    today = date.today().strftime("%Y-%m-%d")
    end_date = (date.today() + timedelta(days=365)).strftime("%Y-%m-%d")

    # Two send windows: 08:00-11:00 and 14:00-16:00, Mon-Thu
    schedules = [
        {
            "name": "Morning Window",
            "timezone": timezone,
            "days": {
                "monday": True,
                "tuesday": True,
                "wednesday": True,
                "thursday": True,
                "friday": False,
                "saturday": False,
                "sunday": False,
            },
            "timing": {"from": "08:00", "to": "11:00"},
        },
        {
            "name": "Afternoon Window",
            "timezone": timezone,
            "days": {
                "monday": True,
                "tuesday": True,
                "wednesday": True,
                "thursday": True,
                "friday": False,
                "saturday": False,
                "sunday": False,
            },
            "timing": {"from": "14:00", "to": "16:00"},
        },
    ]

    sequences = build_email_sequences(country_key)

    payload = {
        "name": name,
        "campaign_schedule": {
            "start_date": today,
            "end_date": end_date,
            "schedules": schedules,
        },
        "sequences": sequences,
        "daily_limit": 40,
        "text_only": True,
        "stop_on_reply": True,
        "open_tracking": True,
        "link_tracking": False,
    }

    if dry_run:
        print("\n[DRY RUN] Would create Instantly campaign:")
        print(f"  Name: {name}")
        print(f"  Timezone: {timezone}")
        print(f"  Schedule: Mon-Thu, 08:00-11:00 & 14:00-16:00")
        print(f"  Daily limit: 40")
        print(f"  Text only: Yes")
        print(f"  Stop on reply: Yes")
        print(f"  Open tracking: Yes")
        print(f"  Link tracking: No")
        print(f"  Emails in sequence: 4")
        return "DRY-RUN-CAMPAIGN-ID"

    headers = {
        "Authorization": f"Bearer {INSTANTLY_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(
            f"{INSTANTLY_BASE_URL}/campaigns",
            headers=headers,
            json=payload,
            timeout=30,
        )
        if resp.status_code in (200, 201):
            data = resp.json()
            campaign_id = data.get("id", "unknown")
            print(f"\n  Campaign created successfully! ID: {campaign_id}")
            return campaign_id
        else:
            print(f"\nERROR: Instantly campaign creation failed ({resp.status_code})")
            print(f"  Response: {resp.text[:500]}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"\nERROR: Could not reach Instantly API: {e}")
        return None


def add_leads_to_instantly(campaign_id, leads, vertical, dry_run=False):
    """
    Add leads to an Instantly campaign via the V2 API.
    Sends leads one at a time (Instantly V2 /leads endpoint).
    Returns count of successfully added leads.
    """
    if dry_run:
        print(f"\n[DRY RUN] Would load {len(leads)} leads into campaign {campaign_id}")
        for lead in leads[:3]:
            print(f"  - {lead['first_name']} {lead['last_name']} <{lead['email']}> ({lead['company_name']})")
        if len(leads) > 3:
            print(f"  ... and {len(leads) - 3} more")
        return len(leads)

    headers = {
        "Authorization": f"Bearer {INSTANTLY_API_KEY}",
        "Content-Type": "application/json",
    }

    success_count = 0
    failed_leads = []

    for i, lead in enumerate(leads):
        payload = {
            "campaign": campaign_id,
            "email": lead["email"],
            "first_name": lead.get("first_name", ""),
            "last_name": lead.get("last_name", ""),
            "company_name": lead.get("company_name", ""),
            "website": lead.get("website", ""),
            "custom_variables": {
                "companyName": lead.get("company_name", ""),
                "vertical": vertical,
            },
            "skip_if_in_workspace": True,
            "skip_if_in_campaign": True,
        }

        try:
            resp = requests.post(
                f"{INSTANTLY_BASE_URL}/leads",
                headers=headers,
                json=payload,
                timeout=15,
            )
            if resp.status_code in (200, 201):
                success_count += 1
            else:
                failed_leads.append(lead)
        except requests.exceptions.RequestException:
            failed_leads.append(lead)

        # Print progress every 50 leads
        if (i + 1) % 50 == 0:
            print(f"  Loaded {i + 1}/{len(leads)} leads...")

    # Save failed leads to CSV if any
    if failed_leads:
        failed_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            f"failed_upload_{date.today().strftime('%Y-%m-%d')}.csv",
        )
        with open(failed_file, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["email", "first_name", "last_name", "company_name", "website"])
            writer.writeheader()
            for lead in failed_leads:
                writer.writerow({k: lead.get(k, "") for k in ["email", "first_name", "last_name", "company_name", "website"]})
        print(f"\n  WARNING: {len(failed_leads)} leads failed to upload.")
        print(f"  Saved to: {failed_file}")
        print(f"  You can manually upload this CSV in Instantly.")

    return success_count


# ---------------------------------------------------------------------------
# Main workflow
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Veston Campaign Tool — cold email pipeline automation")
    parser.add_argument("--dry-run", action="store_true", help="Test without creating campaigns or loading leads")
    parser.add_argument("--csv-import", type=str, help="Import leads from a CSV file instead of DropLeads")
    args = parser.parse_args()

    print("=" * 60)
    print("  VESTON CAMPAIGN TOOL")
    print("  Automated cold email pipeline")
    print("=" * 60)

    if args.dry_run:
        print("\n  ** DRY RUN MODE — no campaigns will be created **")

    # Check API keys
    if not DROPLEADS_API_KEY and not args.csv_import:
        print("\nWARNING: DROPLEADS_API_KEY not found in .env file.")
        print("You can still use --csv-import to load leads from a file.")
    if not INSTANTLY_API_KEY:
        print("\nWARNING: INSTANTLY_API_KEY not found in .env file.")

    # -----------------------------------------------------------------------
    # Step 1: Ask the user what they want
    # -----------------------------------------------------------------------
    vertical_options = [
        "Recruitment", "Agencies", "Ecommerce", "SaaS",
        "Consulting", "IT Services", "Content/Media",
    ]
    vertical_label = ask_choice("What vertical are you targeting?", vertical_options)
    vertical_key = vertical_label.lower().replace("/", "_").replace(" ", "_")

    country_options = [
        "UK", "Netherlands", "Canada", "Australia", "New Zealand",
        "Other EU country (type it)",
    ]
    country_label = ask_choice("What country?", country_options)

    # Handle "other EU country"
    if "other" in country_label.lower():
        country_label = ask_text("Type the EU country name")

    # Check blocked countries
    if country_label.lower() in BLOCKED_COUNTRIES:
        print(f"\n{BLOCKED_MSG}")
        sys.exit(1)

    # Resolve country name
    country_key = COUNTRY_MAP.get(country_label.lower(), country_label)
    country_lower = country_key.lower()

    # How many leads?
    lead_count_str = ask_text("How many leads?", default="500")
    try:
        lead_count = int(lead_count_str)
    except ValueError:
        lead_count = 500

    # Campaign name
    default_name = f"{country_label.replace(' ', '_')}_{vertical_label.replace(' ', '_').replace('/', '_')}_{date.today().strftime('%Y-%m-%d')}"
    campaign_name = ask_text("Campaign name?", default=default_name)

    # -----------------------------------------------------------------------
    # Step 2: Determine search filters
    # -----------------------------------------------------------------------
    print("\n" + "-" * 60)
    print("  PULLING LEADS")
    print("-" * 60)

    # Get filters for this vertical + country combo
    if country_lower in GENERIC_COUNTRY_FILTERS:
        # Canada, Australia, NZ use generic filters for all verticals
        filters = GENERIC_COUNTRY_FILTERS[country_lower].copy()
        # Add industry from vertical if it's defined for UK (as a proxy)
        vertical_def = VERTICALS.get(vertical_key, {})
        uk_filters = vertical_def.get("filters", {}).get("united kingdom", {})
        if "industry" in uk_filters:
            filters["industry"] = uk_filters["industry"]
    else:
        # Look up specific filters for this vertical + country
        vertical_def = VERTICALS.get(vertical_key, {})
        filters = vertical_def.get("filters", {}).get(country_lower, {})
        if not filters:
            # For EU countries not specifically defined, use UK filters as base
            filters = vertical_def.get("filters", {}).get("united kingdom", {})
            if filters:
                filters = filters.copy()
                print(f"  Note: Using standard filters for {country_key} (based on UK template)")
            else:
                print(f"  WARNING: No specific filters defined for {vertical_label} in {country_key}")
                print(f"  Using broad search with country filter only.")
                filters = {"headcount_min": 10, "headcount_max": 60}

    # -----------------------------------------------------------------------
    # Step 3: Pull leads (from DropLeads or CSV)
    # -----------------------------------------------------------------------
    if args.csv_import:
        print(f"\n  Importing leads from: {args.csv_import}")
        leads = import_leads_from_csv(args.csv_import)
        print(f"  Imported {len(leads)} leads from CSV")
    else:
        print(f"\n  Searching DropLeads for {vertical_label} leads in {country_key}...")
        leads = dropleads_search(filters, country_key, lead_count, dry_run=args.dry_run)

    total_pulled = len(leads)

    if total_pulled == 0 and not args.dry_run:
        print("\n  No leads found! Try:")
        print("  - Broadening your filters (larger headcount range)")
        print("  - Trying a different vertical")
        print("  - Using --csv-import to load leads from a file")
        print("  - Exporting leads from the DropLeads web dashboard")
        sys.exit(1)

    print(f"\n  Total leads pulled: {total_pulled}")

    # -----------------------------------------------------------------------
    # Step 4: Deduplicate against suppression list
    # -----------------------------------------------------------------------
    print("\n" + "-" * 60)
    print("  DEDUPLICATING")
    print("-" * 60)

    suppressed = load_suppression_list()
    print(f"  Suppression list size: {len(suppressed)} emails")

    clean_leads = [lead for lead in leads if lead["email"] not in suppressed]
    dedup_removed = total_pulled - len(clean_leads)
    print(f"  Removed {dedup_removed} duplicates")
    print(f"  Clean leads remaining: {len(clean_leads)}")

    if len(clean_leads) == 0:
        print("\n  All leads were already in the suppression list. Nothing to send.")
        sys.exit(0)

    # -----------------------------------------------------------------------
    # Step 5: Create Instantly campaign
    # -----------------------------------------------------------------------
    print("\n" + "-" * 60)
    print("  CREATING INSTANTLY CAMPAIGN")
    print("-" * 60)

    # Use a default timezone for EU countries not in our map
    if country_lower not in COUNTRY_TIMEZONE:
        COUNTRY_TIMEZONE[country_lower] = "Europe/London"
    if country_lower not in COUNTRY_DEMONYM:
        COUNTRY_DEMONYM[country_lower] = country_key
    if country_lower not in COUNTRY_SAVINGS:
        COUNTRY_SAVINGS[country_lower] = "EUR 50,000-150,000"

    campaign_id = create_instantly_campaign(campaign_name, country_lower, dry_run=args.dry_run)

    if campaign_id is None:
        # Campaign creation failed — save leads to CSV for manual upload
        failed_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            f"failed_upload_{date.today().strftime('%Y-%m-%d')}.csv",
        )
        with open(failed_file, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["email", "first_name", "last_name", "company_name", "website"])
            writer.writeheader()
            for lead in clean_leads:
                writer.writerow({k: lead.get(k, "") for k in ["email", "first_name", "last_name", "company_name", "website"]})
        print(f"\n  Campaign creation failed. Leads saved to: {failed_file}")
        print(f"  You can create the campaign manually in Instantly and upload this CSV.")
        _print_summary(total_pulled, dedup_removed, 0, campaign_name, None, "FAILED")
        sys.exit(1)

    # -----------------------------------------------------------------------
    # Step 6: Load leads into Instantly
    # -----------------------------------------------------------------------
    print("\n" + "-" * 60)
    print("  LOADING LEADS INTO INSTANTLY")
    print("-" * 60)

    loaded_count = add_leads_to_instantly(
        campaign_id, clean_leads, vertical_label, dry_run=args.dry_run
    )

    # -----------------------------------------------------------------------
    # Step 7: Update suppression list with newly loaded leads
    # -----------------------------------------------------------------------
    new_emails = [lead["email"] for lead in clean_leads]
    if not args.dry_run:
        save_to_suppression_list(new_emails)
        print(f"\n  Added {len(new_emails)} emails to suppression list")
    else:
        print(f"\n[DRY RUN] Would add {len(new_emails)} emails to suppression list")

    # -----------------------------------------------------------------------
    # Step 8: Print summary
    # -----------------------------------------------------------------------
    status = "ACTIVE" if loaded_count > 0 else "FAILED"
    if args.dry_run:
        status = "DRY RUN — NOT CREATED"
    _print_summary(total_pulled, dedup_removed, loaded_count, campaign_name, campaign_id, status)


def _print_summary(total_pulled, dedup_removed, loaded, campaign_name, campaign_id, status):
    """Print the final summary report."""
    print("\n" + "=" * 60)
    print("  CAMPAIGN SUMMARY")
    print("=" * 60)
    print(f"  Total leads pulled:      {total_pulled}")
    print(f"  Leads removed (dedup):   {dedup_removed}")
    print(f"  Leads loaded:            {loaded}")
    print(f"  Campaign name:           {campaign_name}")
    print(f"  Campaign ID:             {campaign_id or 'N/A'}")
    print(f"  Status:                  {status}")
    print("=" * 60)


if __name__ == "__main__":
    main()
