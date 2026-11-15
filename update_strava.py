import requests
import os
from datetime import datetime, timedelta

# --- Quest Settings (change goals/titles here) ---
RUN_GOAL = 100   # km this month
RIDE_GOAL = 200  # km this month
RUN_QUEST_TITLE = "The Road to Rivendell"
RIDE_QUEST_TITLE = "The Ride to Rohan"

# --- Get secrets from GitHub's secret vault ---
CLIENT_ID = os.environ.get('CLIENT_ID')
CLIENT_SECRET = os.environ.get('CLIENT_SECRET')
REFRESH_TOKEN = os.environ.get('REFRESH_TOKEN')

def get_access_token():
    print("Asking Strava for a fresh token...")
    r = requests.post('https://www.strava.com/oauth/token', data={
        'client_id': CLIENT_ID, 'client_secret': CLIENT_SECRET,
        'refresh_token': REFRESH_TOKEN, 'grant_type': 'refresh_token'
    })
    if r.status_code == 200:
        return r.json()['access_token']
    else:
        print("Error getting token. Check your GitHub Secrets!")
        exit()

token = get_access_token()
headers = {'Authorization': f'Bearer {token}'}
athlete_id = requests.get('https://www.strava.com/api/v3/athlete', headers=headers).json()['id']
stats = requests.get(f'https://www.strava.com/api/v3/athletes/{athlete_id}/stats', headers=headers).json()

# --- 1. Extract All-Time Data ---
run_dist = round(stats['all_run_totals']['distance'] / 1000, 1)
run_elev = int(round(stats['all_run_totals']['elevation_gain']))
run_time = round(stats['all_run_totals']['moving_time'] / 3600, 1)

ride_dist = round(stats['all_ride_totals']['distance'] / 1000, 1)
ride_elev = int(round(stats['all_ride_totals']['elevation_gain']))
ride_time = round(stats['all_ride_totals']['moving_time'] / 3600, 1)

# --- 2. Fetch activities for Weekly + Monthly (one call, wider window) ---
now = datetime.now()
seven_days_ago = now - timedelta(days=7)
start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
earliest_ts = int(min(seven_days_ago, start_of_month).timestamp())

acts = requests.get(
    f'https://www.strava.com/api/v3/athletes/{athlete_id}/activities'
    f'?per_page=200&after={earliest_ts}',
    headers=headers).json()

weekly_run_dist = weekly_run_elev = 0
weekly_ride_dist = weekly_ride_elev = 0
monthly_run_dist = 0
monthly_ride_dist = 0

for a in acts:
    act_date = datetime.strptime(a['start_date_local'].split('T')[0], '%Y-%m-%d')
    dist_km = a['distance'] / 1000
    elev_m = a.get('total_elevation_gain', 0)

    # Weekly (last 7 days)
    if act_date >= seven_days_ago:
        if a['type'] in ['Run', 'VirtualRun']:
            weekly_run_dist += dist_km
            weekly_run_elev += elev_m
        elif a['type'] in ['Ride', 'VirtualRide']:
            weekly_ride_dist += dist_km
            weekly_ride_elev += elev_m

    # Monthly (since 1st of this month)
    if act_date >= start_of_month:
        if a['type'] in ['Run', 'VirtualRun']:
            monthly_run_dist += dist_km
        elif a['type'] in ['Ride', 'VirtualRide']:
            monthly_ride_dist += dist_km

weekly_run_dist = round(weekly_run_dist, 1)
weekly_run_elev = int(round(weekly_run_elev))
weekly_ride_dist = round(weekly_ride_dist, 1)
weekly_ride_elev = int(round(weekly_ride_elev))
monthly_run_dist = round(monthly_run_dist, 1)
monthly_ride_dist = round(monthly_ride_dist, 1)

# --- 3. Quest percentages + flavour text ---
def quest_status(pct):
    if pct >= 100: return "Quest Complete! The realm is saved. ⚔️"
    if pct >= 75:  return "The final stretch! The end is in sight."
    if pct >= 50:  return "Halfway there, traveler. Keep moving."
    if pct >= 25:  return "A good start. The road ahead is long."
    return "The journey begins. One step at a time."

run_pct  = round(min(100, monthly_run_dist  / RUN_GOAL  * 100))
ride_pct = round(min(100, monthly_ride_dist / RIDE_GOAL * 100))

# Gold gradient if 100%, otherwise standard green/gold gradient
run_color = "linear-gradient(90deg, #d4af37, #f9e79f)" if run_pct >= 100 else "linear-gradient(90deg, #7a9e5a, #c9a23a)"
ride_color = "linear-gradient(90deg, #d4af37, #f9e79f)" if ride_pct >= 100 else "linear-gradient(90deg, #7a9e5a, #c9a23a)"

# --- 4. Journal (5 most recent, regardless of week/month) ---
recent = requests.get(
    f'https://www.strava.com/api/v3/athletes/{athlete_id}/activities?per_page=5',
    headers=headers).json()

lines = []
for a in recent[:5]:
    date = datetime.strptime(a['start_date_local'].split('T')[0], '%Y-%m-%d').strftime('%b %d')
    km = round(a['distance'] / 1000, 1)
    elev = int(round(a.get('total_elevation_gain', 0)))
    act_type = a['type']
    name = a['name']

    if act_type in ['Run', 'VirtualRun']:
        flavor = f"A journey of {km} leagues on foot, ascending {elev}m of rugged terrain."
    elif act_type in ['Ride', 'VirtualRide']:
        flavor = f"A ride across the lands, traveling {km} leagues on wheels and conquering {elev}m of elevation."
    elif act_type == 'Walk':
        flavor = f"A steady pace through the shire, covering {km} leagues with {elev}m of gentle ascent."
    else:
        flavor = f"An adventure of {km} leagues, gaining {elev}m in elevation."

    lines.append(f"<p><strong>{date}:</strong> <em>{name}</em> — {flavor}</p>")

journal_html = "\n                ".join(lines)

# --- 5. Fill the template ---
with open('template.html', encoding='utf-8') as f:
    html = f.read()

# All-time
html = html.replace('{{RUN_DIST}}', str(run_dist))
html = html.replace('{{RUN_ELEV}}', str(run_elev))
html = html.replace('{{RUN_TIME}}', str(run_time))
html = html.replace('{{RIDE_DIST}}', str(ride_dist))
html = html.replace('{{RIDE_ELEV}}', str(ride_elev))
html = html.replace('{{RIDE_TIME}}', str(ride_time))

# Weekly
html = html.replace('{{WEEKLY_RUN_DIST}}', str(weekly_run_dist))
html = html.replace('{{WEEKLY_RUN_ELEV}}', str(weekly_run_elev))
html = html.replace('{{WEEKLY_RIDE_DIST}}', str(weekly_ride_dist))
html = html.replace('{{WEEKLY_RIDE_ELEV}}', str(weekly_ride_elev))

# Quests (NEW)
html = html.replace('{{RUN_QUEST_TITLE}}', RUN_QUEST_TITLE)
html = html.replace('{{RUN_QUEST_CURRENT}}', str(monthly_run_dist))
html = html.replace('{{RUN_QUEST_GOAL}}', str(RUN_GOAL))
html = html.replace('{{RUN_QUEST_PCT}}', str(run_pct))
html = html.replace('{{RUN_QUEST_COLOR}}', run_color)      # <-- Add this
html = html.replace('{{RUN_QUEST_STATUS}}', quest_status(run_pct))

html = html.replace('{{RIDE_QUEST_TITLE}}', RIDE_QUEST_TITLE)
html = html.replace('{{RIDE_QUEST_CURRENT}}', str(monthly_ride_dist))
html = html.replace('{{RIDE_QUEST_GOAL}}', str(RIDE_GOAL))
html = html.replace('{{RIDE_QUEST_PCT}}', str(ride_pct))
html = html.replace('{{RIDE_QUEST_COLOR}}', ride_color)    # <-- Add this
html = html.replace('{{RIDE_QUEST_STATUS}}', quest_status(ride_pct))

# Journal
html = html.replace('{{JOURNAL}}', journal_html)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f"Success! Weekly Run: {weekly_run_dist}km | Monthly Run: {monthly_run_dist}/{RUN_GOAL}km ({run_pct}%) | Monthly Ride: {monthly_ride_dist}/{RIDE_GOAL}km ({ride_pct}%)")
