import requests, json, os
from datetime import datetime, timedelta

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

# --- 2. Calculate Weekly Data (Last 7 Days) ---
# We fetch the last 30 activities to look for recent ones
acts = requests.get(
    f'https://www.strava.com/api/v3/athletes/{athlete_id}/activities?per_page=30',
    headers=headers).json()

seven_days_ago = datetime.now() - timedelta(days=7)
weekly_run_dist = 0
weekly_run_elev = 0
weekly_ride_dist = 0
weekly_ride_elev = 0

for a in acts:
    act_date = datetime.strptime(a['start_date_local'].split('T')[0], '%Y-%m-%d')
    if act_date >= seven_days_ago:
        dist_km = a['distance'] / 1000
        elev_m = a.get('total_elevation_gain', 0)
        
        if a['type'] == 'Run':
            weekly_run_dist += dist_km
            weekly_run_elev += elev_m
        elif a['type'] in ['Ride', 'VirtualRide']:
            weekly_ride_dist += dist_km
            weekly_ride_elev += elev_m

weekly_run_dist = round(weekly_run_dist, 1)
weekly_run_elev = int(round(weekly_run_elev))
weekly_ride_dist = round(weekly_ride_dist, 1)
weekly_ride_elev = int(round(weekly_ride_elev))

# --- 3. Journal entries (using the first 5 activities from our list) ---
lines = []
for a in acts[:5]: # Only look at the first 5 for the journal
    date = datetime.strptime(a['start_date_local'].split('T')[0], '%Y-%m-%d').strftime('%b %d')
    km = round(a['distance'] / 1000, 1)
    elev = int(round(a.get('total_elevation_gain', 0)))
    entry = f"<p><strong>{date}:</strong> {a['name']} — {km} km"
    if elev > 0:
        entry += f", {elev} m climbed"
    entry += ".</p>"
    lines.append(entry)
journal_html = "\n                ".join(lines)

# --- 4. Fill the template and write index.html ---
with open('template.html', encoding='utf-8') as f:
    html = f.read()

# Replace All-Time placeholders
html = html.replace('{{RUN_DIST}}', str(run_dist))
html = html.replace('{{RUN_ELEV}}', str(run_elev))
html = html.replace('{{RUN_TIME}}', str(run_time))
html = html.replace('{{RIDE_DIST}}', str(ride_dist))
html = html.replace('{{RIDE_ELEV}}', str(ride_elev))
html = html.replace('{{RIDE_TIME}}', str(ride_time))

# Replace Weekly placeholders
html = html.replace('{{WEEKLY_RUN_DIST}}', str(weekly_run_dist))
html = html.replace('{{WEEKLY_RUN_ELEV}}', str(weekly_run_elev))
html = html.replace('{{WEEKLY_RIDE_DIST}}', str(weekly_ride_dist))
html = html.replace('{{WEEKLY_RIDE_ELEV}}', str(weekly_ride_elev))

# Replace Journal
html = html.replace('{{JOURNAL}}', journal_html)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f"Success! All-time Run: {run_dist}km | Weekly Run: {weekly_run_dist}km")