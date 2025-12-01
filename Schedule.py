import requests
from datetime import datetime

LEAGUE_URL = "https://apps.daysmartrecreation.com/dash/jsonapi/api/v1/leagues/547?cache[save]=false&include=sport%2Cteams.allEvents.statEvents.stat&company=unionpointsports"
TIMEZONE = "America/New_York"
BULLDOGS_ID = "2368"  # ✅ Correct Bulldogs ID

def fetch_league_data():
    r = requests.get(LEAGUE_URL)
    r.raise_for_status()
    return r.json()

def build_team_map(included):
    teams = {}
    for item in included:
        if item.get("type") == "teams":
            tid = item.get("id")
            name = (item.get("attributes") or {}).get("name") or f"Team {tid}"
            teams[tid] = name
    # Ensure Bulldogs resolve even if attributes were missing
    teams[BULLDOGS_ID] = teams.get(BULLDOGS_ID, "(U10G) HAYSA Bulldogs")
    return teams

def filter_bulldogs_events(included):
    games = []
    for item in included:
        if item.get("type") != "events":
            continue
        attrs = item.get("attributes", {})
        htid = str(attrs.get("hteam_id"))
        vtid = str(attrs.get("vteam_id"))
        if htid == BULLDOGS_ID or vtid == BULLDOGS_ID:
            games.append(item)
    return games

def safe_name(teams, tid):
    return teams.get(tid, f"Team {tid}")

def parse_dt(dt_str):
    return datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S")

def write_ics(events, teams, filename="bulldogs_schedule.ics"):
    with open(filename, "w", encoding="utf-8") as f:
        f.write("BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:dash_scraper\n")
        for ev in events:
            attrs = ev["attributes"]
            start_iso = attrs["start"]
            end_iso = attrs["end"]
            start_ics = start_iso.replace("-", "").replace(":", "")
            end_ics = end_iso.replace("-", "").replace(":", "")

            htid = str(attrs["hteam_id"])
            vtid = str(attrs["vteam_id"])
            hteam = safe_name(teams, htid)
            vteam = safe_name(teams, vtid)

            summary = f"{hteam} vs {vteam}"
            uid = f"{ev['id']}@unionpointsports"

            f.write("BEGIN:VEVENT\n")
            f.write(f"UID:{uid}\n")
            f.write(f"DTSTAMP:{start_ics}Z\n")
            f.write(f"DTSTART;TZID={TIMEZONE}:{start_ics}\n")
            f.write(f"DTEND;TZID={TIMEZONE}:{end_ics}\n")
            f.write(f"SUMMARY:{summary}\n")
            f.write("END:VEVENT\n")
        f.write("END:VCALENDAR\n")

def main():
    data = fetch_league_data()
    included = data.get("included", [])
    teams = build_team_map(included)
    bulldogs_games = filter_bulldogs_events(included)

    bulldogs_games.sort(key=lambda e: e["attributes"]["start"])

    print(f"Found {len(bulldogs_games)} Bulldogs games")
    for ev in bulldogs_games:
        attrs = ev["attributes"]
        start = parse_dt(attrs["start"])
        end = parse_dt(attrs["end"])
        hname = safe_name(teams, str(attrs["hteam_id"]))
        vname = safe_name(teams, str(attrs["vteam_id"]))
        start_str = start.strftime("%a %m/%d/%Y %I:%M%p")
        end_str = end.strftime("%I:%M%p")
        print(f"{start_str}–{end_str} {hname} vs {vname}")

    write_ics(bulldogs_games, teams)
    print("✅ Bulldogs-only ICS generated: bulldogs_schedule.ics")

if __name__ == "__main__":
    main()
