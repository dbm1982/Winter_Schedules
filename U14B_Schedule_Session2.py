import requests
from datetime import datetime

# League 632 = Holbrook United's league
LEAGUE_URL = (
    "https://apps.daysmartrecreation.com/dash/jsonapi/api/v1/leagues/632"
    "?cache[save]=false"
    "&include=sport,teams.allEvents.statEvents.stat"
    "&company=unionpointsports"
)
TIMEZONE = "America/New_York"
HOLBROOK_ID = "2586"

RESOURCE_MAP = {
    "1": "Bubble 1",
    "2": "Bubble 2",
}

RESOURCE_AREA_MAP = {
    "1": "Quarter 1A",
    "2": "Quarter 1B",
    "3": "Quarter 1C",
    "4": "Quarter 1D",
    "5": "Quarter 2A",
    "6": "Quarter 2B",
    "7": "Quarter 2C",
    "8": "Quarter 2D",
}

VENUE_ADDRESS = "Union Point Sports Complex, 170 Memorial Grove Ave, Weymouth, MA 02190"
TEAM_PAGE_URL = "https://apps.daysmartrecreation.com/dash/x/#/online/unionpointsports/teams/2586"


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
    teams[HOLBROOK_ID] = teams.get(HOLBROOK_ID, "Holbrook United")
    return teams


def filter_team_events(included):
    games = []
    for item in included:
        if item.get("type") != "events":
            continue
        attrs = item.get("attributes", {})
        htid = str(attrs.get("hteam_id"))
        vtid = str(attrs.get("vteam_id"))
        if htid == HOLBROOK_ID or vtid == HOLBROOK_ID:
            games.append(item)
    return games


def index_stat_events(included):
    """
    Build a map: scores_by_event[event_id][team_id] = total_goals (sum of 'value')
    """
    scores_by_event = {}
    for item in included:
        if item.get("type") != "stat-events":
            continue
        attrs = item.get("attributes", {}) or {}
        event_id = str(attrs.get("event_id"))
        team_id = str(attrs.get("team_id"))
        value = attrs.get("value", 0) or 0
        if not event_id or not team_id:
            continue
        scores_by_event.setdefault(event_id, {})
        scores_by_event[event_id][team_id] = scores_by_event[event_id].get(team_id, 0) + value
    return scores_by_event


def safe_name(teams, tid):
    return teams.get(tid, f"Team {tid}")


def parse_dt(dt_str):
    return datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S")


def get_score_for_event(ev, scores_by_event):
    """
    Determine the score for an event using the stat-events index.
    Returns 'H-A' string or None if unavailable.
    """
    attrs = ev.get("attributes", {}) or {}
    eid = str(ev.get("id"))
    htid = str(attrs.get("hteam_id"))
    vtid = str(attrs.get("vteam_id"))

    # Prefer direct hscore/vscore if present
    hscore = attrs.get("hscore")
    vscore = attrs.get("vscore")
    if hscore is not None and vscore is not None:
        return f"{hscore}-{vscore}"

    # Fallback: sum stat-events
    event_scores = scores_by_event.get(eid, {})
    if not event_scores:
        return None

    home_goals = event_scores.get(htid, 0)
    away_goals = event_scores.get(vtid, 0)

    # Only show if at least one side has a nonzero score
    if home_goals == 0 and away_goals == 0:
        return None

    return f"{home_goals}-{away_goals}"


def write_ics(events, teams, scores_by_event, filename="U14B_schedule.ics"):
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
            summary = f"{hteam} vs {vteam}"  # matchup only
            uid = f"{ev['id']}@unionpointsports"

            resource_id = str(attrs.get("resource_id"))
            area_id = str(attrs.get("resource_area_id"))
            resource_name = RESOURCE_MAP.get(resource_id, f"Resource {resource_id}")
            area_name = RESOURCE_AREA_MAP.get(area_id, f"Area {area_id}")

            # Notes/description field (score only in notes)
            score = get_score_for_event(ev, scores_by_event)
            notes = (
                f"Field Assignment: {resource_name}: {area_name}\\n"
                f"Team Page: {TEAM_PAGE_URL}"
            )
            if score:
                notes += f"\\nFinal Score: {score}"

            f.write("BEGIN:VEVENT\n")
            f.write(f"UID:{uid}\n")
            f.write(f"DTSTAMP:{start_ics}Z\n")
            f.write(f"DTSTART;TZID={TIMEZONE}:{start_ics}\n")
            f.write(f"DTEND;TZID={TIMEZONE}:{end_ics}\n")
            f.write(f"SUMMARY:{summary}\n")
            f.write(f"LOCATION:{VENUE_ADDRESS}\n")
            f.write(f"DESCRIPTION:{notes}\n")
            f.write("END:VEVENT\n")
        f.write("END:VCALENDAR\n")


def main():
    data = fetch_league_data()
    included = data.get("included", []) or []
    teams = build_team_map(included)
    holbrook_games = filter_team_events(included)
    scores_by_event = index_stat_events(included)

    holbrook_games.sort(key=lambda e: e["attributes"]["start"])

    print(f"Found {len(holbrook_games)} Holbrook United games")
    for ev in holbrook_games:
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

        # Console preview: no score here
        print(f"{start_str}–{end_str} {hname} vs {vname} @ {resource_name}: {area_name}")

    write_ics(holbrook_games, teams, scores_by_event)
    print("✅ Holbrook United-only ICS generated: U14B_schedule.ics")


if __name__ == "__main__":
    main()





