import requests
import os
import random
from datetime import datetime, timedelta

# --- Quest Settings (change goals/titles here) ---
RUN_GOAL = 100   # km this month
RIDE_GOAL = 200  # km this month
RUN_QUEST_TITLE = "The Road to Rivendell"
RIDE_QUEST_TITLE = "The Ride to Rohan"

# --- Journey Map Settings ---
VOYAGE_START = datetime(2026, 11, 17)  # The day your voyage began (the Shire). Change this date anytime.
JOURNEY_GOAL = 2863                    # Exact km from the Shire to Mount Doom

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

# --- 2. Fetch activities for Weekly (Mon-Sun) + Monthly + Voyage ---
now = datetime.now()
days_since_monday = now.weekday()
start_of_week = (now - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
# Make sure the query window reaches back far enough to include the voyage start date
earliest_ts = int(min(start_of_week, start_of_month, VOYAGE_START).timestamp())

acts = requests.get(
    f'https://www.strava.com/api/v3/athletes/{athlete_id}/activities'
    f'?per_page=200&after={earliest_ts}',
    headers=headers).json()

weekly_run_dist = 0
weekly_run_elev = 0
weekly_ride_dist = 0
weekly_ride_elev = 0
monthly_run_dist = 0
monthly_ride_dist = 0
voyage_dist = 0

for a in acts:
    act_date = datetime.strptime(a['start_date_local'].split('T')[0], '%Y-%m-%d')
    dist_km = a['distance'] / 1000
    elev_m = a.get('total_elevation_gain', 0)

    # Weekly (Monday to Sunday)
    if act_date >= start_of_week:
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

    # Voyage (since the journey began at the Shire)
    if act_date >= VOYAGE_START:
        if a['type'] in ['Run', 'VirtualRun', 'Ride', 'VirtualRide', 'Walk']:
            voyage_dist += dist_km

weekly_run_dist = round(weekly_run_dist, 1)
weekly_run_elev = int(round(weekly_run_elev))
weekly_ride_dist = round(weekly_ride_dist, 1)
weekly_ride_elev = int(round(weekly_ride_elev))
monthly_run_dist = round(monthly_run_dist, 1)
monthly_ride_dist = round(monthly_ride_dist, 1)
voyage_dist = round(voyage_dist, 1)

# --- 3. Quest percentages + flavour text ---
def quest_status(pct, current, goal):
    remaining = round(goal - current, 1)
    if pct >= 100:
        return f"Quest Complete! The realm is saved. ⚔️ You conquered {current} leagues!"
    if pct >= 75:
        return f"The final stretch! Only {remaining} leagues left to conquer."
    if pct >= 50:
        return f"Past the halfway mark! You have {remaining} leagues remaining on this quest."
    if pct >= 25:
        return f"A good start. {remaining} leagues still lie ahead."
    return f"The journey begins. {remaining} leagues to go until the quest is done."

run_pct  = round(min(100, monthly_run_dist  / RUN_GOAL  * 100))
ride_pct = round(min(100, monthly_ride_dist / RIDE_GOAL * 100))

# Voyage progress toward Mount Doom
journey_pct = round(min(100, voyage_dist / JOURNEY_GOAL * 100))

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
        options = [
            f"A journey of {km} leagues on foot, ascending {elev}m of rugged terrain.",
            f"The road goes ever on and on. {km} leagues covered, with {elev}m of elevation conquered.",
            f"A swift stride through the wilds! {km} leagues travelled, scaling {elev}m of mountains.",
            f"Not all those who wander are lost, but this one covered {km} leagues and climbed {elev}m!",
            f"Through shadow and light, {km} leagues were walked and {elev}m of mountains scaled.",
            f"A fellowship of one, marching {km} leagues and conquering {elev}m of steep ascent.",
            f"The eagles may fly, but you ran {km} leagues and climbed {elev}m on your own two feet!",
            f"From the Shire to the edge of the wild: {km} leagues on foot, {elev}m of elevation gained.",
            f"A steady pace, a heavy breath, and {km} leagues travelled with {elev}m of mountains overcome.",
            f"You have walked where few dare to tread: {km} leagues and {elev}m of elevation behind you.",
            f"The path was long and the hills were high: {km} leagues covered, {elev}m climbed.",
            f"A true Ranger's pace: {km} leagues traversed on foot, ascending {elev}m into the clouds."
        ]
    elif act_type in ['Ride', 'VirtualRide']:
        options = [
            f"A ride across the lands, travelling {km} leagues on wheels and conquering {elev}m of elevation.",
            f"Ride out, ride out! {km} leagues crossed on two wheels, ascending {elev}m into the sky.",
            f"Like a rider of Rohan, you covered {km} leagues and climbed {elev}m of steep terrain.",
            f"The wind in your face and the road beneath you: {km} leagues ridden, {elev}m climbed.",
            f"Faster than the horses of the Mark! {km} leagues ridden, with {elev}m of elevation conquered.",
            f"A great gallop across the plains: {km} leagues covered, scaling {elev}m of mountains.",
            f"The wheels turned and the miles flew by: {km} leagues travelled, {elev}m of ascent achieved.",
            f"Through the fields of Rohan and beyond: {km} leagues on two wheels, {elev}m of elevation gained.",
            f"A swift journey on the wings of the wind: {km} leagues ridden, {elev}m climbed.",
            f"The road called, and you answered on two wheels: {km} leagues and {elev}m of elevation.",
            f"No shadow could catch you today: {km} leagues ridden and {elev}m of mountains scaled.",
            f"A magnificent charge across Middle-earth: {km} leagues covered, {elev}m of elevation conquered."
        ]
    elif act_type == 'Walk':
        options = [
            f"A steady pace through the shire, covering {km} leagues with {elev}m of gentle ascent.",
            f"A quiet stroll through the woods. {km} leagues walked, gaining {elev}m in height.",
            f"Second breakfast was well earned after this {km} league walk, climbing {elev}m."
        ]
    else:
        options = [
            f"An adventure of {km} leagues, gaining {elev}m in elevation.",
            f"A mysterious journey of {km} leagues, scaling {elev}m of unknown lands."
        ]

    flavor = random.choice(options)
    lines.append(f"<p><strong>{date}:</strong> <em>{name}</em> — {flavor}</p>")

journal_html = "\n                ".join(lines)

# --- 5. Quote of the Day ---
quotes = [
    "\"Not all those who wander are lost.\" - J.R.R. Tolkien",
    "\"You shall not pass!\" - Gandalf",
    "\"The road goes ever on and on.\" - Bilbo Baggins",
    "\"There's some good in this world, Mr. Frodo, and it's worth fighting for.\" - Samwise Gamgee",
    "\"I will not say: do not weep; for not all tears are an evil.\" - Gandalf",
    "\"A wizard is never late, nor is he early, he arrives precisely when he means to.\" - Gandalf",
    "\"Courage is found in unlikely places.\" - Gildor",
    "\"Even the smallest person can change the course of the future.\" - Galadriel",
    "\"There is nothing like looking, if you want to find something.\" - Bilbo Baggins",
    "\"It's a dangerous business, Frodo, going out your door.\" - Bilbo Baggins",
    "\"Faithless is he that says farewell when the road darkens.\" - Gimli",
    "\"I am no man!\" - Éowyn",
    "\"For Frodo.\" - Samwise Gamgee",
    "\"The world is indeed full of peril, and in it there are many dark places.\" - Haldir"
]
day_of_year = datetime.now().timetuple().tm_yday
daily_quote = quotes[day_of_year % len(quotes)]

# --- 6. Fill the template ---
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

# Quests
html = html.replace('{{RUN_QUEST_TITLE}}', RUN_QUEST_TITLE)
html = html.replace('{{RUN_QUEST_CURRENT}}', str(monthly_run_dist))
html = html.replace('{{RUN_QUEST_GOAL}}', str(RUN_GOAL))
html = html.replace('{{RUN_QUEST_PCT}}', str(run_pct))
html = html.replace('{{RUN_QUEST_COLOR}}', run_color)
html = html.replace('{{RUN_QUEST_STATUS}}', quest_status(run_pct, monthly_run_dist, RUN_GOAL))

html = html.replace('{{RIDE_QUEST_TITLE}}', RIDE_QUEST_TITLE)
html = html.replace('{{RIDE_QUEST_CURRENT}}', str(monthly_ride_dist))
html = html.replace('{{RIDE_QUEST_GOAL}}', str(RIDE_GOAL))
html = html.replace('{{RIDE_QUEST_PCT}}', str(ride_pct))
html = html.replace('{{RIDE_QUEST_COLOR}}', ride_color)
html = html.replace('{{RIDE_QUEST_STATUS}}', quest_status(ride_pct, monthly_ride_dist, RIDE_GOAL))

# Journal
html = html.replace('{{JOURNAL}}', journal_html)

# Quote of the Day
html = html.replace('{{QUOTE_OF_THE_DAY}}', daily_quote)

# Journey Map (now the voyage, not all-time)
html = html.replace('{{TOTAL_DIST}}', str(voyage_dist))
html = html.replace('{{JOURNEY_PCT}}', str(journey_pct))

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f"Success! Voyage: {voyage_dist}/{JOURNEY_GOAL} km to Mount Doom ({journey_pct}%) | Weekly Run: {weekly_run_dist}km | Monthly Run: {monthly_run_dist}/{RUN_GOAL}km ({run_pct}%)")
