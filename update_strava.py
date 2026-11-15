import requests, json, os
from datetime import datetime

# --- Get secrets from GitHub's secret vault ---
CLIENT_ID = os.environ.get('CLIENT_ID')
CLIENT_SECRET = os.environ.get('CLIENT_SECRET')
REFRESH_TOKEN = os.environ.get('REFRESH_TOKEN')

def get_access_token():
    print("Asking Strava for a fresh token...")
    r = requests.post('https://www.strava.com/oauth/token', data={
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'refresh_token': REFRESH_TOKEN,
        'grant_type': 'refresh_token'
    })
    if r.status_code == 200:
        return r.json()['access_token']
    else:
        print("Error getting token. Check your GitHub Secrets!")
        print(r.text)
        exit()

token = get_access_token()
headers = {'Authorization': f'Bearer {token}'}
athlete_id = requests.get('https://www.strava.com/api/v3/athlete', headers=headers).json()['id']
stats = requests.get(f'https://www.strava.com/api/v3/athletes/{athlete_id}/stats', headers=headers).json()

# --- 1. Extract Run Data ---
run_dist = round(stats['all_run_totals']['distance'] / 1000, 1)
run_elev = int(round(stats['all_run_totals']['elevation_gain']))
run_time = round(stats['all_run_totals']['moving_time'] / 3600, 1)

# --- 2. Extract Ride Data ---
ride_dist = round(stats['all_ride_totals']['distance'] / 1000, 1)
ride_elev = int(round(stats['all_ride_totals']['elevation_gain']))
ride_time = round(stats['all_ride_totals']['moving_time'] / 3600, 1)

# --- 3. Journal entries from recent activities ---
acts = requests.get(
    f'https://www.strava.com/api/v3/athletes/{athlete_id}/activities?per_page=5',
    headers=headers).json()

lines = []
for a in acts:
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

html = html.replace('{{RUN_DIST}}', str(run_dist))
html = html.replace('{{RUN_ELEV}}', str(run_elev))
html = html.replace('{{RUN_TIME}}', str(run_time))

html = html.replace('{{RIDE_DIST}}', str(ride_dist))
html = html.replace('{{RIDE_ELEV}}', str(ride_elev))
html = html.replace('{{RIDE_TIME}}', str(ride_time))

html = html.replace('{{JOURNAL}}', journal_html)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f"Success! Run: {run_dist}km | Ride: {ride_dist}km")