"""
Generates summer_2026.html — open it in any browser.
Run list_calendars.py first to find your calendar IDs.
"""
import os
import re
import datetime
import difflib
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# ── Configure these ──────────────────────────────────────────────────────────
CALENDAR_IDS = {
    "Matt": "mattw7186@gmail.com",
    # Add your wife's calendar ID here once she shares it with you:
    # "Wife": "her-email@gmail.com",
}

SUMMER_START = datetime.date(2026, 6, 1)
SUMMER_END   = datetime.date(2026, 8, 31)
OUTPUT_FILE  = "index.html"

# Events whose title contains any of these words (case-insensitive) are hidden
FILTER_KEYWORDS = ["bethany"]

# Event type detection — first match wins, order matters
EVENT_TYPES = [
    ("trip",     ["beach house", "vacation", "trip", "flight", "hotel", "airbnb", "cruise", "travel", "resort", "cabin", "camping"]),
    ("concert",  ["concert", "ticket", "festival", "show", "tour", "music", "live at", "in the park"]),
    ("doctor",   ["dr.", "doctor", "dentist", "therapy", "therapist", "appointment", "medical", "checkup", "physical", "ortho", "derma"]),
    ("sports",   ["game", "match", "tournament", "race", "marathon", "league"]),
    ("birthday", ["birthday", "bday", "b-day"]),
    ("dinner",   ["dinner", "restaurant", "reservation", "lunch", "brunch"]),
    ("wedding",  ["wedding", "ceremony", "reception", "bridal", "bachelor"]),
]

TYPE_ICONS = {
    "trip":     "✈️",
    "concert":  "🎵",
    "doctor":   "🏥",
    "sports":   "🏆",
    "birthday": "🎂",
    "dinner":   "🍽️",
    "wedding":  "💍",
}
# ─────────────────────────────────────────────────────────────────────────────

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
DIR = os.path.dirname(os.path.abspath(__file__))

COLORS = [
    "#4A90D9",  # blue
    "#E8693A",  # orange
    "#43A86E",  # green
    "#9B59B6",  # purple
]


def get_credentials(token_file='token.json'):
    token_path = os.path.join(DIR, token_file)
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(os.path.join(DIR, 'credentials.json'), SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, 'w') as f:
            f.write(creds.to_json())
    return creds


def fetch_events(service, calendar_id, label, color):
    time_min = datetime.datetime.combine(SUMMER_START, datetime.time.min).isoformat() + 'Z'
    time_max = datetime.datetime.combine(SUMMER_END, datetime.time.max).isoformat() + 'Z'

    events = []
    page_token = None
    while True:
        result = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime',
            pageToken=page_token,
            maxResults=500,
        ).execute()
        for e in result.get('items', []):
            start = e['start'].get('date') or e['start'].get('dateTime', '')[:10]
            end   = e['end'].get('date')   or e['end'].get('dateTime', '')[:10]
            time_str = ''
            if 'dateTime' in e['start']:
                t = datetime.datetime.fromisoformat(e['start']['dateTime'])
                time_str = t.strftime('%-I:%M %p')
            events.append({
                'date':     start,
                'end_date': end,
                'title':    e.get('summary', '(no title)'),
                'time':     time_str,
                'location': e.get('location', ''),
                'label':    label,
                'color':    color,
                'all_day':  'date' in e['start'],
            })
        page_token = result.get('nextPageToken')
        if not page_token:
            break
    return events


def filter_events(events):
    return [
        e for e in events
        if not any(kw in e['title'].lower() for kw in FILTER_KEYWORDS)
    ]


def _norm(title):
    """Normalize a title for fuzzy comparison."""
    t = title.lower()
    t = re.sub(r'^ticket[:\s]+', '', t)       # strip "Ticket: " prefix
    t = re.sub(r'[-–—]+\s*(sat|sun|mon|tue|wed|thu|fri)\w*\s*ticket', '', t)  # strip "- SATURDAY TICKET" suffix
    t = re.sub(r'[^\w\s]', ' ', t)            # remove punctuation
    return re.sub(r'\s+', ' ', t).strip()


def deduplicate_events(events):
    """Within each day, drop events whose title is very similar to one already kept."""
    kept = []
    for e in events:
        norm = _norm(e['title'])
        is_dup = False
        for k in kept:
            if k['date'] == e['date']:
                k_norm = _norm(k['title'])
                ratio = difflib.SequenceMatcher(None, norm, k_norm).ratio()
                if ratio >= 0.75 or norm in k_norm or k_norm in norm:
                    is_dup = True
                    break
        if not is_dup:
            kept.append(e)
    return kept


def get_event_type(title):
    title_lower = title.lower()
    for etype, keywords in EVENT_TYPES:
        if any(kw in title_lower for kw in keywords):
            return etype
    return None


def events_by_day(all_events):
    days = {}
    current = SUMMER_START
    while current <= SUMMER_END:
        days[current.isoformat()] = []
        current += datetime.timedelta(days=1)
    for e in all_events:
        start = datetime.date.fromisoformat(e['date'])
        if e['all_day'] and e['end_date']:
            # Google all-day end dates are exclusive
            end = datetime.date.fromisoformat(e['end_date'])
        else:
            end = start + datetime.timedelta(days=1)
        day = start
        while day < end:
            if day.isoformat() in days:
                days[day.isoformat()].append(e)
            day += datetime.timedelta(days=1)
    return days


def render_event(e):
    time_part = f'<span class="etime">{e["time"]}</span> ' if e['time'] else '<span class="etime all-day">All day</span> '
    loc_part  = f'<span class="eloc">📍 {e["location"]}</span>' if e['location'] else ''
    etype = get_event_type(e['title'])
    icon = TYPE_ICONS.get(etype, '')
    type_badge = f'<span class="etype {etype}">{icon} {etype}</span>' if etype else ''
    return (
        f'<div class="event" style="border-left:3px solid {e["color"]}">'
        f'{time_part}'
        f'<span class="etitle">{e["title"]}</span>'
        f'{type_badge}'
        f'<span class="ecal" style="color:{e["color"]}">{e["label"]}</span>'
        f'{loc_part}'
        f'</div>'
    )


def render_html(days_map):
    legend_items = ''.join(
        f'<span class="leg-item"><span class="leg-dot" style="background:{COLORS[i % len(COLORS)]}"></span>{label}</span>'
        for i, label in enumerate(CALENDAR_IDS.keys())
    )

    months_html = ''
    current_month = None
    month_html = ''

    for date_str, events in sorted(days_map.items()):
        d = datetime.date.fromisoformat(date_str)
        if d.month != current_month:
            if month_html:
                months_html += f'<div class="month"><h2>{month_name}</h2><div class="days">{month_html}</div></div>'
            current_month = d.month
            month_name = d.strftime('%B %Y')
            month_html = ''

        has_events = bool(events)
        is_weekend = d.weekday() >= 5

        # Skip empty weekdays entirely
        if not has_events and not is_weekend:
            continue

        events_html = ''.join(render_event(e) for e in sorted(events, key=lambda x: (not x['all_day'], x['time'])))

        if not has_events:
            # Empty weekend — show as a quiet placeholder
            month_html += (
                f'<div class="day empty-weekend">'
                f'<div class="date-header">'
                f'<span class="dow">{d.strftime("%a")}</span>'
                f'<span class="dom">{d.day}</span>'
                f'</div>'
                f'<div class="events"><span class="free-tag">Free weekend</span></div>'
                f'</div>'
            )
        else:
            day_class = f'day has-events{" weekend" if is_weekend else ""}'
            month_html += (
                f'<div class="{day_class}">'
                f'<div class="date-header">'
                f'<span class="dow">{d.strftime("%a")}</span>'
                f'<span class="dom">{d.day}</span>'
                f'</div>'
                f'<div class="events">{events_html}</div>'
                f'</div>'
            )

    if month_html:
        months_html += f'<div class="month"><h2>{month_name}</h2><div class="days">{month_html}</div></div>'

    total_event_days = sum(1 for events in days_map.values() if events)
    generated_at = datetime.datetime.now().strftime('%B %d, %Y at %-I:%M %p')

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Summer 2026</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #f5f5f0; color: #222; }}
  header {{ background: #1a1a2e; color: white; padding: 24px 32px; display: flex; align-items: center; justify-content: space-between; }}
  header h1 {{ font-size: 1.8rem; font-weight: 700; letter-spacing: -0.5px; }}
  header .meta {{ font-size: 0.8rem; opacity: 0.5; margin-top: 4px; }}
  .legend {{ display: flex; gap: 16px; align-items: center; }}
  .leg-item {{ display: flex; align-items: center; gap: 6px; font-size: 0.85rem; }}
  .leg-dot {{ width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }}
  main {{ max-width: 960px; margin: 0 auto; padding: 32px 16px; }}
  .month {{ margin-bottom: 48px; }}
  .month h2 {{ font-size: 1.3rem; font-weight: 600; color: #1a1a2e; border-bottom: 2px solid #1a1a2e; padding-bottom: 8px; margin-bottom: 16px; }}
  .days {{ display: flex; flex-direction: column; gap: 6px; }}
  .day {{ display: flex; gap: 12px; padding: 10px 14px; border-radius: 8px; background: white; border: 1px solid #eee; min-height: 44px; align-items: flex-start; align-items: center; }}
  .day.empty-weekend {{ opacity: 0.45; background: #fafaf8; border: 1px dashed #ddd; min-height: 36px; }}
  .day.weekend {{ background: #fafaf8; }}
  .free-tag {{ font-size: 0.75rem; color: #bbb; font-style: italic; }}
  .day.has-events {{ box-shadow: 0 1px 4px rgba(0,0,0,0.06); }}
  .date-header {{ min-width: 52px; display: flex; flex-direction: column; align-items: center; padding-top: 2px; }}
  .dow {{ font-size: 0.7rem; text-transform: uppercase; color: #999; font-weight: 600; letter-spacing: 0.5px; }}
  .dom {{ font-size: 1.2rem; font-weight: 700; color: #1a1a2e; line-height: 1; }}
  .day.weekend .dom {{ color: #555; }}
  .events {{ flex: 1; display: flex; flex-direction: column; gap: 5px; }}
  .event {{ padding: 4px 8px; border-radius: 4px; background: #f8f8f8; display: flex; flex-wrap: wrap; gap: 6px; align-items: baseline; }}
  .etime {{ font-size: 0.75rem; color: #888; min-width: 60px; }}
  .etime.all-day {{ color: #bbb; }}
  .etitle {{ font-size: 0.9rem; font-weight: 500; flex: 1; }}
  .ecal {{ font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }}
  .etype {{ font-size: 0.65rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.4px; padding: 1px 6px; border-radius: 10px; }}
  .etype.trip     {{ background: #FFF0D6; color: #B05E00; }}
  .etype.concert  {{ background: #F0E6FF; color: #6B28A8; }}
  .etype.doctor   {{ background: #FFE6E6; color: #B00020; }}
  .etype.sports   {{ background: #E6F7EE; color: #1A7A40; }}
  .etype.birthday {{ background: #FFE6F0; color: #A8004A; }}
  .etype.dinner   {{ background: #E6F4FF; color: #0060A8; }}
  .etype.wedding  {{ background: #FFFFF0; color: #807000; }}
  .eloc {{ font-size: 0.75rem; color: #888; width: 100%; padding-left: 66px; }}
  footer {{ text-align: center; padding: 24px; font-size: 0.75rem; color: #bbb; }}
</style>
</head>
<body>
<header>
  <div>
    <h1>☀️ Summer 2026</h1>
    <div class="meta">Generated {generated_at} &nbsp;·&nbsp; {total_event_days} days with events</div>
  </div>
  <div class="legend">{legend_items}</div>
</header>
<main>
{months_html}
</main>
<footer>Regenerate anytime by running <code>python3 generate.py</code></footer>
</body>
</html>'''


def main():
    print("Connecting to Google Calendar...")
    creds = get_credentials()
    service = build('calendar', 'v3', credentials=creds)

    all_events = []
    for i, (label, cal_id) in enumerate(CALENDAR_IDS.items()):
        color = COLORS[i % len(COLORS)]
        print(f"  Fetching: {label} ({cal_id})")
        all_events.extend(fetch_events(service, cal_id, label, color))

    print(f"  Found {len(all_events)} events total")
    all_events = filter_events(all_events)
    all_events = deduplicate_events(all_events)
    print(f"  {len(all_events)} after filtering and deduplication")
    days_map = events_by_day(all_events)
    html = render_html(days_map)

    with open(OUTPUT_FILE, 'w') as f:
        f.write(html)

    print(f"\nDone! Open {OUTPUT_FILE} in your browser.")
    import sys, subprocess
    if sys.platform == 'darwin':
        subprocess.run(['open', os.path.join(DIR, OUTPUT_FILE)])


if __name__ == '__main__':
    main()
