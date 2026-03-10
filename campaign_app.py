#!/usr/bin/env python3
"""
Veston Campaign Tool — Web App
===============================
A browser-based interface for the cold email campaign pipeline.

Run this file and it opens in your browser automatically.
Pick your options, click Launch, done.

Usage:
    python campaign_app.py
"""

import csv
import json
import os
import sys
import threading
import time
import webbrowser
from datetime import date, timedelta

try:
    from flask import Flask, jsonify, request, Response
except ImportError:
    print("\n  Flask is not installed. Run this command first:")
    print("    pip install flask")
    print()
    sys.exit(1)

try:
    import requests as http_requests
except ImportError:
    print("\n  The 'requests' library is not installed. Run this command first:")
    print("    pip install requests")
    print()
    sys.exit(1)

# Load .env manually (no dependency needed)
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DROPLEADS_API_KEY = os.environ.get("DROPLEADS_API_KEY", "")
DROPLEADS_BASE_URL = os.environ.get("DROPLEADS_BASE_URL", "https://api.dropleads.io/v1")
INSTANTLY_API_KEY = os.environ.get("INSTANTLY_API_KEY", "")
INSTANTLY_BASE_URL = os.environ.get("INSTANTLY_BASE_URL", "https://api.instantly.ai/api/v2")
SUPPRESSION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "suppression_list.csv")

BLOCKED_COUNTRIES = {"germany", "france", "pakistan", "south africa", "nigeria"}

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

COUNTRY_MAP = {
    "uk": "United Kingdom", "united kingdom": "United Kingdom",
    "netherlands": "Netherlands", "nl": "Netherlands",
    "canada": "Canada", "ca": "Canada",
    "australia": "Australia", "au": "Australia",
    "new zealand": "New Zealand", "nz": "New Zealand",
}

COUNTRY_TIMEZONE = {
    "united kingdom": "Europe/London",
    "netherlands": "Europe/Amsterdam",
    "canada": "America/Toronto",
    "australia": "Australia/Sydney",
    "new zealand": "Pacific/Auckland",
}

COUNTRY_DEMONYM = {
    "united kingdom": "UK", "netherlands": "Dutch",
    "canada": "Canadian", "australia": "Australian",
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
# Campaign logic (same as veston_campaign.py)
# ---------------------------------------------------------------------------
def load_suppression_list():
    emails = set()
    if os.path.exists(SUPPRESSION_FILE):
        with open(SUPPRESSION_FILE, "r", newline="") as f:
            reader = csv.reader(f)
            for row in reader:
                if row:
                    emails.add(row[0].strip().lower())
    return emails


def save_to_suppression_list(new_emails):
    with open(SUPPRESSION_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        for email in new_emails:
            writer.writerow([email.lower()])


def get_filters(vertical_key, country_lower):
    if country_lower in GENERIC_COUNTRY_FILTERS:
        filters = GENERIC_COUNTRY_FILTERS[country_lower].copy()
        vertical_def = VERTICALS.get(vertical_key, {})
        uk_filters = vertical_def.get("filters", {}).get("united kingdom", {})
        if "industry" in uk_filters:
            filters["industry"] = uk_filters["industry"]
        return filters

    vertical_def = VERTICALS.get(vertical_key, {})
    filters = vertical_def.get("filters", {}).get(country_lower, {})
    if not filters:
        filters = vertical_def.get("filters", {}).get("united kingdom", {})
        if filters:
            filters = filters.copy()
    if not filters:
        filters = {"headcount_min": 10, "headcount_max": 60}
    return filters


def dropleads_search(filters, country, limit):
    headers = {
        "Authorization": f"Bearer {DROPLEADS_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload = {"country": country, "limit": limit}
    if "industry" in filters:
        payload["industry"] = filters["industry"]
    if "headcount_min" in filters:
        payload["employee_count_min"] = filters["headcount_min"]
        payload["headcount_min"] = filters["headcount_min"]
    if "headcount_max" in filters:
        payload["employee_count_max"] = filters["headcount_max"]
        payload["headcount_max"] = filters["headcount_max"]
    if "titles" in filters:
        payload["job_titles"] = filters["titles"]
        payload["titles"] = filters["titles"]

    endpoints = [
        ("POST", f"{DROPLEADS_BASE_URL}/search"),
        ("POST", f"{DROPLEADS_BASE_URL}/people/search"),
        ("POST", f"{DROPLEADS_BASE_URL}/leads/search"),
        ("GET",  f"{DROPLEADS_BASE_URL}/leads"),
        ("GET",  f"{DROPLEADS_BASE_URL}/people"),
    ]

    for method, url in endpoints:
        try:
            if method == "POST":
                resp = http_requests.request(method, url, headers=headers, json=payload, timeout=30)
            else:
                params = {}
                for k, v in payload.items():
                    params[k] = ",".join(v) if isinstance(v, list) else v
                resp = http_requests.request(method, url, headers=headers, params=params, timeout=30)

            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    leads = data
                elif isinstance(data, dict):
                    leads = (data.get("data") or data.get("results") or
                             data.get("leads") or data.get("people") or
                             data.get("records") or [])
                else:
                    leads = []
                return normalize_leads(leads), None
            elif resp.status_code == 404:
                continue
            elif resp.status_code in (401, 403):
                return [], f"DropLeads authentication failed ({resp.status_code}). Check your API key."
            else:
                continue
        except http_requests.exceptions.RequestException:
            continue

    return [], "Could not reach DropLeads API. Check your API key and internet connection."


def normalize_leads(raw_leads):
    normalized = []
    for lead in raw_leads:
        if not isinstance(lead, dict):
            continue
        email = (lead.get("email") or lead.get("work_email") or
                 lead.get("verified_email") or lead.get("business_email") or "")
        if not email:
            continue
        normalized.append({
            "email": email.strip().lower(),
            "first_name": lead.get("first_name") or lead.get("firstName") or "",
            "last_name": lead.get("last_name") or lead.get("lastName") or "",
            "company_name": (lead.get("company_name") or lead.get("company") or
                             lead.get("organization") or ""),
            "website": (lead.get("website") or lead.get("company_website") or
                        lead.get("domain") or ""),
            "title": lead.get("title") or lead.get("job_title") or "",
        })
    return normalized


def build_email_sequences(country_key):
    demonym = COUNTRY_DEMONYM.get(country_key, "")
    savings = COUNTRY_SAVINGS.get(country_key, "")

    sequences = [{"steps": [
        {"type": "email", "delay": 0, "variants": [{"subject": "{{firstName}}, international structuring question", "body": (
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
        )}]},
        {"type": "email", "delay": 3, "variants": [{"subject": "Re: international structuring", "body": (
            "{{firstName}}, the difference between a compliant structure and an "
            "exposed one is governance.\n\n"
            "We provide a UAE-based management committee, documented decision authority, "
            "monthly management minutes, and annual substance certification.\n\n"
            "Our clients do not just have a Dubai company. They have an institutionally "
            "managed, treaty-compliant structure.\n\n"
            "Happy to explain in 15 minutes.\n\n"
            "Reid"
        )}]},
        {"type": "email", "delay": 4, "variants": [{"subject": "potential improvement in retained capital", "body": (
            f"{{{{firstName}}}}, for a {demonym} business at your scale, the difference "
            "between the current position and a managed UAE structure is typically "
            f"{savings} per year in retained capital.\n\n"
            "Subject to individual circumstances. Worth a conversation?\n\n"
            "Reid"
        )}]},
        {"type": "email", "delay": 7, "variants": [{"subject": "closing your file", "body": (
            "Have not heard back. Closing your file. If this becomes relevant, "
            "reply any time.\n\n"
            "Reid"
        )}]},
    ]}]
    return sequences


def create_instantly_campaign(name, country_key):
    timezone = COUNTRY_TIMEZONE.get(country_key, "Europe/London")
    today = date.today().strftime("%Y-%m-%d")
    end_date = (date.today() + timedelta(days=365)).strftime("%Y-%m-%d")

    day_config = {
        "monday": True, "tuesday": True, "wednesday": True,
        "thursday": True, "friday": False, "saturday": False, "sunday": False,
    }
    schedules = [
        {"name": "Morning Window", "timezone": timezone, "days": day_config, "timing": {"from": "08:00", "to": "11:00"}},
        {"name": "Afternoon Window", "timezone": timezone, "days": dict(day_config), "timing": {"from": "14:00", "to": "16:00"}},
    ]

    payload = {
        "name": name,
        "campaign_schedule": {"start_date": today, "end_date": end_date, "schedules": schedules},
        "sequences": build_email_sequences(country_key),
        "daily_limit": 40,
        "text_only": True,
        "stop_on_reply": True,
        "open_tracking": True,
        "link_tracking": False,
    }

    headers = {
        "Authorization": f"Bearer {INSTANTLY_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        resp = http_requests.post(f"{INSTANTLY_BASE_URL}/campaigns", headers=headers, json=payload, timeout=30)
        if resp.status_code in (200, 201):
            data = resp.json()
            return data.get("id", "unknown"), None
        else:
            return None, f"Instantly returned {resp.status_code}: {resp.text[:300]}"
    except http_requests.exceptions.RequestException as e:
        return None, f"Could not reach Instantly: {e}"


def add_leads_to_instantly(campaign_id, leads, vertical_label):
    headers = {
        "Authorization": f"Bearer {INSTANTLY_API_KEY}",
        "Content-Type": "application/json",
    }
    success = 0
    failed = []
    for lead in leads:
        payload = {
            "campaign": campaign_id,
            "email": lead["email"],
            "first_name": lead.get("first_name", ""),
            "last_name": lead.get("last_name", ""),
            "company_name": lead.get("company_name", ""),
            "website": lead.get("website", ""),
            "custom_variables": {"companyName": lead.get("company_name", ""), "vertical": vertical_label},
            "skip_if_in_workspace": True,
            "skip_if_in_campaign": True,
        }
        try:
            resp = http_requests.post(f"{INSTANTLY_BASE_URL}/leads", headers=headers, json=payload, timeout=15)
            if resp.status_code in (200, 201):
                success += 1
            else:
                failed.append(lead)
        except http_requests.exceptions.RequestException:
            failed.append(lead)
    return success, failed


# ---------------------------------------------------------------------------
# Flask App
# ---------------------------------------------------------------------------
app = Flask(__name__)

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Veston Campaign Tool</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    min-height: 100vh;
    background: linear-gradient(145deg, #0a0f1a 0%, #111827 40%, #0d1520 100%);
    font-family: 'Instrument Sans', 'SF Pro Display', -apple-system, sans-serif;
    color: #e2e8f0;
    overflow-x: hidden;
  }
  .glow1 { position: fixed; top: -20%; right: -10%; width: 600px; height: 600px;
    background: radial-gradient(circle, rgba(212,168,67,0.06) 0%, transparent 70%); pointer-events: none; }
  .glow2 { position: fixed; bottom: -20%; left: -10%; width: 500px; height: 500px;
    background: radial-gradient(circle, rgba(39,174,96,0.04) 0%, transparent 70%); pointer-events: none; }

  .container { max-width: 600px; margin: 0 auto; padding: 40px 24px; position: relative; }

  .badge {
    display: inline-block; padding: 6px 16px; border: 1px solid rgba(212,168,67,0.3);
    border-radius: 100px; font-size: 11px; letter-spacing: 2px; text-transform: uppercase;
    color: #D4A843; margin-bottom: 24px;
  }
  h1 {
    font-size: clamp(26px, 5vw, 38px); font-weight: 700; line-height: 1.15; margin: 0 0 16px;
    background: linear-gradient(135deg, #ffffff 0%, #D4A843 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  }
  .subtitle { font-size: 15px; color: #94a3b8; line-height: 1.6; max-width: 480px; margin: 0 auto 32px; }

  .card {
    background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06);
    border-radius: 20px; padding: 36px 32px; backdrop-filter: blur(20px);
  }

  .field-label {
    display: block; font-size: 12px; letter-spacing: 1.5px; text-transform: uppercase;
    color: #D4A843; margin-bottom: 10px; font-weight: 600;
  }
  .field-group { margin-bottom: 28px; }

  select, input[type="number"], input[type="text"] {
    width: 100%; padding: 14px 18px; border-radius: 12px;
    border: 1px solid rgba(255,255,255,0.1); background: rgba(255,255,255,0.04);
    color: #fff; font-size: 16px; font-weight: 500; outline: none;
    transition: border-color 0.2s; -webkit-appearance: none; appearance: none;
  }
  select { cursor: pointer; background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' fill='%2394a3b8'%3E%3Cpath d='M6 8L1 3h10z'/%3E%3C/svg%3E");
    background-repeat: no-repeat; background-position: right 16px center; padding-right: 40px; }
  select:focus, input:focus { border-color: rgba(212,168,67,0.5); }
  option { background: #1a1f2e; color: #e2e8f0; }

  .btn-launch {
    width: 100%; padding: 16px; border-radius: 12px; border: none;
    background: linear-gradient(135deg, #D4A843 0%, #b8912e 100%);
    color: #0a0f1a; font-size: 15px; font-weight: 700; letter-spacing: 0.5px;
    cursor: pointer; transition: all 0.3s; text-transform: uppercase;
  }
  .btn-launch:hover { transform: translateY(-1px); box-shadow: 0 8px 25px rgba(212,168,67,0.3); }
  .btn-launch:disabled { background: rgba(255,255,255,0.05); color: #64748b; cursor: default; transform: none; box-shadow: none; }

  .btn-dryrun {
    width: 100%; padding: 14px; border-radius: 12px; margin-top: 10px;
    border: 1px solid rgba(212,168,67,0.3); background: transparent;
    color: #D4A843; font-size: 13px; font-weight: 600; cursor: pointer;
    transition: all 0.2s; letter-spacing: 0.5px;
  }
  .btn-dryrun:hover { background: rgba(212,168,67,0.08); }
  .btn-dryrun:disabled { border-color: rgba(255,255,255,0.05); color: #64748b; cursor: default; }

  /* Status / Results */
  .status-card {
    background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06);
    border-radius: 20px; padding: 32px; margin-top: 24px;
  }
  .status-title { font-size: 14px; font-weight: 700; color: #D4A843; margin-bottom: 20px; text-transform: uppercase; letter-spacing: 1px; }

  .log-area {
    background: rgba(0,0,0,0.3); border-radius: 12px; padding: 16px 20px;
    font-family: 'SF Mono', 'Fira Code', monospace; font-size: 13px;
    line-height: 1.8; color: #94a3b8; max-height: 300px; overflow-y: auto;
    border: 1px solid rgba(255,255,255,0.04);
  }
  .log-area .step { color: #D4A843; font-weight: 600; }
  .log-area .ok { color: #27ae60; }
  .log-area .err { color: #ef4444; }
  .log-area .num { color: #60a5fa; }

  .summary-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 20px; }
  .summary-item {
    padding: 16px; border-radius: 12px;
    background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06);
  }
  .summary-item .label { font-size: 10px; text-transform: uppercase; letter-spacing: 1.5px; color: #64748b; margin-bottom: 4px; }
  .summary-item .value { font-size: 20px; font-weight: 700; color: #e2e8f0; }
  .summary-item.success .value { color: #27ae60; }
  .summary-item.highlight .value { color: #D4A843; }

  .btn-reset {
    display: block; margin: 24px auto 0; background: none; border: none;
    color: #64748b; font-size: 13px; cursor: pointer; text-decoration: underline;
  }

  .api-status { display: flex; gap: 16px; margin-bottom: 24px; }
  .api-dot {
    display: flex; align-items: center; gap: 6px; font-size: 12px; color: #64748b;
  }
  .api-dot .dot { width: 8px; height: 8px; border-radius: 50%; }
  .dot-green { background: #27ae60; }
  .dot-red { background: #ef4444; }
  .dot-grey { background: #475569; }

  .spinner {
    display: inline-block; width: 16px; height: 16px; border: 2px solid rgba(212,168,67,0.3);
    border-top-color: #D4A843; border-radius: 50%; animation: spin 0.8s linear infinite;
    vertical-align: middle; margin-right: 8px;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
</head>
<body>
<div class="glow1"></div>
<div class="glow2"></div>

<div class="container">
  <div style="text-align:center">
    <div class="badge">Veston Partners</div>
    <h1>Campaign Tool</h1>
    <p class="subtitle">Pull leads, deduplicate, create Instantly campaign — all in one click.</p>
  </div>

  <!-- API Status -->
  <div class="api-status" id="apiStatus">
    <div class="api-dot">
      <span class="dot dot-grey" id="dotDropleads"></span> DropLeads
    </div>
    <div class="api-dot">
      <span class="dot dot-grey" id="dotInstantly"></span> Instantly
    </div>
  </div>

  <!-- Form -->
  <div class="card" id="formCard">
    <div class="field-group">
      <label class="field-label">Vertical</label>
      <select id="vertical">
        <option value="">Pick a vertical...</option>
        <option value="recruitment">Recruitment</option>
        <option value="agencies">Agencies</option>
        <option value="ecommerce">Ecommerce</option>
        <option value="saas">SaaS</option>
        <option value="consulting">Consulting</option>
        <option value="it_services">IT Services</option>
        <option value="content_media">Content / Media</option>
      </select>
    </div>

    <div class="field-group">
      <label class="field-label">Country</label>
      <select id="country">
        <option value="">Pick a country...</option>
        <option value="uk">UK</option>
        <option value="netherlands">Netherlands</option>
        <option value="canada">Canada</option>
        <option value="australia">Australia</option>
        <option value="new zealand">New Zealand</option>
      </select>
    </div>

    <div class="field-group">
      <label class="field-label">Number of Leads</label>
      <input type="number" id="leadCount" value="500" min="10" max="5000" step="10">
    </div>

    <div class="field-group">
      <label class="field-label">Campaign Name (optional)</label>
      <input type="text" id="campaignName" placeholder="Auto-generated if blank">
    </div>

    <button class="btn-launch" id="btnLaunch" disabled>Launch Campaign</button>
    <button class="btn-dryrun" id="btnDryRun" disabled>Test Run (no emails sent)</button>
  </div>

  <!-- Results -->
  <div id="resultsArea" style="display:none">
    <div class="status-card">
      <div class="status-title" id="statusTitle"><span class="spinner"></span> Running...</div>
      <div class="log-area" id="logArea"></div>
      <div class="summary-grid" id="summaryGrid" style="display:none"></div>
    </div>
    <button class="btn-reset" id="btnReset" style="display:none">Run another campaign</button>
  </div>
</div>

<script>
const $ = id => document.getElementById(id);
const vertical = $('vertical'), country = $('country');
const leadCount = $('leadCount'), campaignName = $('campaignName');
const btnLaunch = $('btnLaunch'), btnDryRun = $('btnDryRun');
const formCard = $('formCard'), resultsArea = $('resultsArea');
const logArea = $('logArea'), statusTitle = $('statusTitle');
const summaryGrid = $('summaryGrid'), btnReset = $('btnReset');

// Enable buttons when form is filled
function checkForm() {
  const ok = vertical.value && country.value;
  btnLaunch.disabled = !ok;
  btnDryRun.disabled = !ok;
}
vertical.addEventListener('change', checkForm);
country.addEventListener('change', checkForm);

// Check API keys on load
fetch('/api/status').then(r => r.json()).then(d => {
  $('dotDropleads').className = 'dot ' + (d.dropleads ? 'dot-green' : 'dot-red');
  $('dotInstantly').className = 'dot ' + (d.instantly ? 'dot-green' : 'dot-red');
});

function log(html) {
  logArea.innerHTML += html + '<br>';
  logArea.scrollTop = logArea.scrollHeight;
}

function showSummary(data) {
  summaryGrid.style.display = 'grid';
  summaryGrid.innerHTML = `
    <div class="summary-item highlight">
      <div class="label">Leads Pulled</div>
      <div class="value">${data.total_pulled}</div>
    </div>
    <div class="summary-item">
      <div class="label">Duplicates Removed</div>
      <div class="value">${data.dedup_removed}</div>
    </div>
    <div class="summary-item success">
      <div class="label">Leads Loaded</div>
      <div class="value">${data.loaded}</div>
    </div>
    <div class="summary-item">
      <div class="label">Status</div>
      <div class="value" style="font-size:14px">${data.status}</div>
    </div>
  `;
}

async function runCampaign(dryRun) {
  formCard.style.display = 'none';
  resultsArea.style.display = 'block';
  logArea.innerHTML = '';
  summaryGrid.style.display = 'none';
  btnReset.style.display = 'none';
  statusTitle.innerHTML = '<span class="spinner"></span> Running...';

  const body = {
    vertical: vertical.value,
    country: country.value,
    lead_count: parseInt(leadCount.value) || 500,
    campaign_name: campaignName.value || '',
    dry_run: dryRun,
  };

  try {
    const resp = await fetch('/api/launch', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(body),
    });
    const data = await resp.json();

    // Show log
    for (const line of data.log) {
      log(line);
    }

    if (data.success) {
      statusTitle.innerHTML = '<span class="ok" style="font-size:20px">&#10003;</span> ' +
        (dryRun ? 'Test Run Complete' : 'Campaign Launched!');
    } else {
      statusTitle.innerHTML = '<span class="err">&#10007;</span> Failed';
    }

    showSummary(data);
  } catch(e) {
    log('<span class="err">Error: ' + e.message + '</span>');
    statusTitle.innerHTML = '<span class="err">&#10007;</span> Error';
  }

  btnReset.style.display = 'block';
}

btnLaunch.addEventListener('click', () => {
  if (confirm('This will create a LIVE campaign and start sending emails. Continue?')) {
    runCampaign(false);
  }
});
btnDryRun.addEventListener('click', () => runCampaign(true));
btnReset.addEventListener('click', () => {
  formCard.style.display = 'block';
  resultsArea.style.display = 'none';
});
</script>
</body>
</html>"""


@app.route("/")
def index():
    return Response(HTML_PAGE, mimetype="text/html")


@app.route("/api/status")
def api_status():
    return jsonify({
        "dropleads": bool(DROPLEADS_API_KEY),
        "instantly": bool(INSTANTLY_API_KEY),
    })


@app.route("/api/launch", methods=["POST"])
def api_launch():
    data = request.json
    vertical_key = data.get("vertical", "")
    country_input = data.get("country", "")
    lead_count = data.get("lead_count", 500)
    campaign_name = data.get("campaign_name", "")
    dry_run = data.get("dry_run", False)

    log_lines = []

    def log(msg, cls=""):
        if cls:
            log_lines.append(f'<span class="{cls}">{msg}</span>')
        else:
            log_lines.append(msg)

    # Validate
    country_key = COUNTRY_MAP.get(country_input.lower(), country_input)
    country_lower = country_key.lower()

    if country_lower in BLOCKED_COUNTRIES:
        log("This country is blocked from Veston campaigns.", "err")
        return jsonify({"success": False, "log": log_lines, "total_pulled": 0, "dedup_removed": 0, "loaded": 0, "status": "BLOCKED"})

    vertical_def = VERTICALS.get(vertical_key, {})
    vertical_label = vertical_def.get("label", vertical_key)

    if not campaign_name:
        campaign_name = f"{country_input.replace(' ', '_')}_{vertical_label.replace(' ', '_').replace('/', '_')}_{date.today().strftime('%Y-%m-%d')}"

    # Ensure country has timezone/demonym/savings
    if country_lower not in COUNTRY_TIMEZONE:
        COUNTRY_TIMEZONE[country_lower] = "Europe/London"
    if country_lower not in COUNTRY_DEMONYM:
        COUNTRY_DEMONYM[country_lower] = country_key
    if country_lower not in COUNTRY_SAVINGS:
        COUNTRY_SAVINGS[country_lower] = "EUR 50,000-150,000"

    # Step 1: Get filters
    filters = get_filters(vertical_key, country_lower)
    log("PULLING LEADS", "step")
    log(f"Vertical: {vertical_label} &middot; Country: {country_key} &middot; Limit: {lead_count}")
    if "industry" in filters:
        log(f"Industry: {filters['industry']}")
    log(f"Headcount: {filters.get('headcount_min', '?')}-{filters.get('headcount_max', '?')}")

    # Step 2: Pull leads
    if dry_run:
        first_names = ["James", "Sarah", "Michael", "Emma", "David",
                       "Lisa", "Robert", "Anna", "Thomas", "Maria"]
        last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones",
                      "Wilson", "Taylor", "Davies", "Evans", "Clark"]
        leads = []
        for i in range(min(lead_count, 10)):
            leads.append({
                "email": f"{first_names[i].lower()}.{last_names[i].lower()}@example-{i}.com",
                "first_name": first_names[i], "last_name": last_names[i],
                "company_name": f"Sample Co {i+1}", "website": f"https://example-{i}.com", "title": "CEO",
            })
        log(f"[DRY RUN] Generated <span class='num'>{len(leads)}</span> sample leads", "ok")
    else:
        leads, err = dropleads_search(filters, country_key, lead_count)
        if err:
            log(f"DropLeads error: {err}", "err")
        log(f"Pulled <span class='num'>{len(leads)}</span> leads")

    total_pulled = len(leads)
    if total_pulled == 0 and not dry_run:
        log("No leads found. Check your DropLeads API key and filters.", "err")
        return jsonify({"success": False, "log": log_lines, "total_pulled": 0, "dedup_removed": 0, "loaded": 0, "status": "NO LEADS"})

    # Step 3: Deduplicate
    log("", "")
    log("DEDUPLICATING", "step")
    suppressed = load_suppression_list()
    log(f"Suppression list: <span class='num'>{len(suppressed)}</span> emails")
    clean_leads = [l for l in leads if l["email"] not in suppressed]
    dedup_removed = total_pulled - len(clean_leads)
    log(f"Removed <span class='num'>{dedup_removed}</span> duplicates")
    log(f"Clean leads: <span class='num'>{len(clean_leads)}</span>")

    if len(clean_leads) == 0:
        log("All leads already in suppression list.", "err")
        return jsonify({"success": False, "log": log_lines, "total_pulled": total_pulled, "dedup_removed": dedup_removed, "loaded": 0, "status": "ALL DUPES"})

    # Step 4: Create campaign
    log("", "")
    log("CREATING INSTANTLY CAMPAIGN", "step")
    log(f"Name: {campaign_name}")

    if dry_run:
        campaign_id = "DRY-RUN-ID"
        log(f"[DRY RUN] Would create campaign: {campaign_name}", "ok")
        log(f"Schedule: Mon-Thu, 08:00-11:00 &amp; 14:00-16:00")
        log(f"Daily limit: 40 &middot; Text only &middot; Stop on reply")
        log(f"Emails in sequence: 4")
    else:
        campaign_id, err = create_instantly_campaign(campaign_name, country_lower)
        if err:
            log(f"Instantly error: {err}", "err")
            return jsonify({"success": False, "log": log_lines, "total_pulled": total_pulled, "dedup_removed": dedup_removed, "loaded": 0, "status": "CAMPAIGN FAILED"})
        log(f"Campaign created! ID: {campaign_id}", "ok")

    # Step 5: Load leads
    log("", "")
    log("LOADING LEADS", "step")

    if dry_run:
        loaded = len(clean_leads)
        log(f"[DRY RUN] Would load <span class='num'>{loaded}</span> leads", "ok")
        for l in clean_leads[:3]:
            log(f"&nbsp;&nbsp;{l['first_name']} {l['last_name']} &lt;{l['email']}&gt;")
        if len(clean_leads) > 3:
            log(f"&nbsp;&nbsp;... and {len(clean_leads) - 3} more")
    else:
        loaded, failed = add_leads_to_instantly(campaign_id, clean_leads, vertical_label)
        log(f"Loaded <span class='num'>{loaded}</span> / {len(clean_leads)} leads", "ok")
        if failed:
            log(f"<span class='num'>{len(failed)}</span> leads failed to upload", "err")

    # Step 6: Update suppression list
    if not dry_run:
        new_emails = [l["email"] for l in clean_leads]
        save_to_suppression_list(new_emails)
        log(f"Added {len(new_emails)} emails to suppression list", "ok")
    else:
        log(f"[DRY RUN] Would add {len(clean_leads)} to suppression list", "ok")

    log("", "")
    log("DONE", "step")

    status = "DRY RUN" if dry_run else ("ACTIVE" if loaded > 0 else "FAILED")
    return jsonify({
        "success": True,
        "log": log_lines,
        "total_pulled": total_pulled,
        "dedup_removed": dedup_removed,
        "loaded": loaded,
        "campaign_name": campaign_name,
        "campaign_id": campaign_id,
        "status": status,
    })


def open_browser():
    """Wait for the server to start, then open the browser."""
    time.sleep(1.5)
    webbrowser.open("http://localhost:5000")


if __name__ == "__main__":
    print()
    print("=" * 50)
    print("  VESTON CAMPAIGN TOOL")
    print("  Opening in your browser...")
    print("=" * 50)
    print()
    print("  If it doesn't open automatically, go to:")
    print("  http://localhost:5000")
    print()
    print("  Press Ctrl+C to stop.")
    print()

    threading.Thread(target=open_browser, daemon=True).start()
    app.run(host="127.0.0.1", port=5000, debug=False)
