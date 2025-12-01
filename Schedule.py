import requests
from datetime import datetime

LEAGUE_URL = (
    "https://apps.daysmartrecreation.com/dash/jsonapi/api/v1/leagues/547"
    "?cache[save]=false"
    "&include=sport,teams.allEvents.statEvents.stat"
    "&company=unionpointsports"
)
TIMEZONE = "America/New_York"
BULLDOGS_ID = "2368"

# ✅ Manual lookup dictionaries based on what you confirmed from the site
RESOURCE_MAP = {
    "1": "Bubble 1",
    "2": "Bubble 2",
}

RESOURCE_AREA_MAP = {
    # Bubble 1 quarters
    "1": "Quarter 1A",
    "2": "Quarter 1B",
    "3": "Quarter 1C",
    "4": "Quarter 1D",

    # Bubble 2 quarters
    "5": "Quarter 2A",
    "6": "Quarter 2B",
    "7": "Quarter 2C",
    "8": "Quarter 2D",
}

# ✅ Physical address for directions
VENUE_ADDRESS = "Union Point Sports Complex, 170 Memorial Grove Ave, Weymouth, MA 02190"

# ✅ Permanent team page link
TEAM_PAGE_URL = "https://apps.daysmartrecreation.com/dash/x/#/online/unionpointsports/teams/2368"

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

            hteam = safe_name(teams, str(attrs.get("hteam_id")))
            vteam = safe_name(teams, str(attrs.get("vteam_id")))
            summary = f"{hteam} vs {vteam}"
            uid = f"{ev['id']}@unionpointsports"

            # Resolve resource IDs
            resource_id = str(attrs.get("resource_id"))
            area_id = str(attrs.get("resource_area_id"))
            resource_name = RESOURCE_MAP.get(resource_id, f"Resource {resource_id}")
            area_name = RESOURCE_AREA_MAP.get(area_id, f"Area {area_id}")

            # Notes/description field
            notes = (
                f"Field Assignment: {resource_name}: {area_name}\\n"
                f"Team Page: {TEAM_PAGE_URL}"
            )

            f.write("BEGIN:VEVENT\n")
            f.write(f"UID:{uid}\n")
            f.write(f"DTSTAMP:{start_ics}Z\n")
            f.write(f"DTSTART;TZID={TIMEZONE}:{start_ics}\n")
            f.write(f"DTEND;TZID={TIMEZONE}:{end_ics}\n")
            f.write(f"SUMMARY:{summary}\n")
            f.write(f"LOCATION:{VENUE_ADDRESS}\n")   # ✅ physical address for directions
            f.write(f"DESCRIPTION:{notes}\n")        # ✅ bubble/quarter + link in notes
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
        hname = safe_name(teams, str(attrs.get("hteam_id")))
        vname = safe_name(teams, str(attrs.get("vteam_id")))
        start_str = start.strftime("%a %m/%d/%Y %I:%M%p")
        end_str = end.strftime("%I:%M%p")

        resource_id = str(attrs.get("resource_id"))
        area_id = str(attrs.get("resource_area_id"))
        resource_name = RESOURCE_MAP.get(resource_id, f"Resource {resource_id}")
        area_name = RESOURCE_AREA_MAP.get(area_id, f"Area {area_id}")

        print(f"{start_str}–{end_str} {hname} vs {vname} @ {resource_name}: {area_name}")

    write_ics(bulldogs_games, teams)
    print("✅ Bulldogs-only ICS generated: bulldogs_schedule.ics")

if __name__ == "__main__":
    main()
