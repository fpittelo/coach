"""Formatters to render Intervals.icu data into structured JSON and agent-friendly Markdown."""

import json
from typing import Any, Dict, List


def to_json_str(data: Any) -> str:
    """Format Python object as indented JSON string."""
    return json.dumps(data, indent=2, default=str)


def format_profile(data: Dict[str, Any], fmt_json: bool = False) -> str:
    """Format athlete profile."""
    if fmt_json:
        return to_json_str(data)

    athlete = data.get("athlete", data)
    name = athlete.get("name", "Unknown Athlete")
    athlete_id = athlete.get("id", "N/A")
    email = athlete.get("email", "N/A")
    city = athlete.get("city") or athlete.get("state") or "N/A"
    country = athlete.get("country", "N/A")
    weight = athlete.get("weight", "N/A")
    dob = athlete.get("dob", "N/A")

    lines = [
        f"# Athlete Profile: {name} (ID: {athlete_id})",
        "",
        f"- **Email**: {email}",
        f"- **Location**: {city}, {country}",
        f"- **Weight**: {weight} kg",
        f"- **Date of Birth**: {dob}",
        f"- **Resting HR**: {athlete.get('restingHR', 'N/A')} bpm",
        f"- **Max HR**: {athlete.get('maxHR', 'N/A')} bpm",
    ]
    return "\n".join(lines)


def format_sport_settings(data: Any, fmt_json: bool = False) -> str:
    """Format athlete sport settings (zones, FTP, threshold HR)."""
    if fmt_json:
        return to_json_str(data)

    settings_list = data if isinstance(data, list) else [data]
    lines = ["# Athlete Sport Settings & Training Zones", ""]

    for sport in settings_list:
        types = sport.get("types", [])
        types_str = ", ".join(types) if isinstance(types, list) else str(types)
        ftp = sport.get("ftp", "N/A")
        indoor_ftp = sport.get("indoor_ftp", "N/A")
        lthr = sport.get("lthr", "N/A")
        max_hr = sport.get("max_hr", "N/A")

        lines.append(f"## Sport: {types_str or 'Default'}")
        lines.append(f"- **FTP**: {ftp} W (Indoor: {indoor_ftp} W)")
        lines.append(f"- **Threshold HR (LTHR)**: {lthr} bpm | **Max HR**: {max_hr} bpm")

        power_zones = sport.get("power_zones", [])
        if power_zones:
            lines.append("- **Power Zones (Watts)**: " + ", ".join(f"Z{i+1}: {z}W" for i, z in enumerate(power_zones)))

        hr_zones = sport.get("hr_zones", [])
        if hr_zones:
            lines.append("- **HR Zones (bpm)**: " + ", ".join(f"Z{i+1}: {z}bpm" for i, z in enumerate(hr_zones)))

        lines.append("")

    return "\n".join(lines)


def format_activities_list(activities: List[Dict[str, Any]], fmt_json: bool = False) -> str:
    """Format list of activities."""
    if fmt_json:
        return to_json_str(activities)

    if not activities:
        return "No activities found for the specified date range."

    lines = [
        f"# Activities Summary ({len(activities)} activities found)",
        "",
        "| Date | Name | Type | Duration | Distance | Avg Power | Avg HR | Load (TSS) |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    for act in activities:
        date_str = act.get("start_date_local", "N/A")[:10]
        name = act.get("name", "Untitled")
        act_id = act.get("id", "")
        act_type = act.get("type", "Activity")
        moving_time = act.get("moving_time", 0)
        minutes = moving_time // 60
        hours = minutes // 60
        rem_min = minutes % 60
        dur_str = f"{hours}h {rem_min}m" if hours > 0 else f"{rem_min}m"
        dist_km = f"{act.get('distance', 0) / 1000:.1f} km" if act.get("distance") else "-"
        avg_watts = f"{act.get('average_watts', 0):.0f} W" if act.get("average_watts") else "-"
        avg_hr = f"{act.get('average_heartrate', 0):.0f} bpm" if act.get("average_heartrate") else "-"
        load = f"{act.get('icu_training_load', 0):.0f}" if act.get("icu_training_load") is not None else "-"

        lines.append(f"| {date_str} | [{name}](id:{act_id}) | {act_type} | {dur_str} | {dist_km} | {avg_watts} | {avg_hr} | {load} |")

    return "\n".join(lines)


def format_activity_detail(act: Dict[str, Any], fmt_json: bool = False) -> str:
    """Format single activity deep details."""
    if fmt_json:
        return to_json_str(act)

    name = act.get("name", "Untitled")
    act_id = act.get("id", "N/A")
    start_date = act.get("start_date_local", "N/A")
    act_type = act.get("type", "Activity")
    moving_time = act.get("moving_time", 0)
    dur_str = f"{moving_time // 3600}h {(moving_time % 3600) // 60}m {moving_time % 60}s"
    dist = f"{act.get('distance', 0) / 1000:.2f} km" if act.get("distance") else "N/A"

    lines = [
        f"# Activity: {name} (ID: {act_id})",
        "",
        f"- **Date & Time**: {start_date}",
        f"- **Type**: {act_type}",
        f"- **Duration**: {dur_str} (Elapsed: {act.get('elapsed_time', moving_time)}s)",
        f"- **Distance**: {dist}",
        f"- **Elevation Gain**: {act.get('total_elevation_gain', 'N/A')} m",
        "",
        "## Performance & Physiological Metrics",
        f"- **Normalized Power (NP)**: {act.get('icu_weighted_avg_watts', 'N/A')} W",
        f"- **Average Power**: {act.get('average_watts', 'N/A')} W (Max: {act.get('max_watts', 'N/A')} W)",
        f"- **Training Load (TSS)**: {act.get('icu_training_load', 'N/A')}",
        f"- **Intensity Factor (IF)**: {act.get('icu_intensity', 'N/A')}",
        f"- **Average Heart Rate**: {act.get('average_heartrate', 'N/A')} bpm (Max: {act.get('max_heartrate', 'N/A')} bpm)",
        f"- **Average Cadence**: {act.get('average_cadence', 'N/A')} rpm",
        f"- **Aerobic / Anaerobic Training Effect**: {act.get('icu_aerobic_training_effect', 'N/A')} / {act.get('icu_anaerobic_training_effect', 'N/A')}",
        f"- **Feel / RPE**: {act.get('feel', 'N/A')} / RPE: {act.get('perceived_exertion', 'N/A')}",
    ]

    desc = act.get("description")
    if desc:
        lines.extend(["", "## Athlete Notes", desc])

    return "\n".join(lines)


def format_activity_streams(data: Any, fmt_json: bool = False) -> str:
    """Format activity streams."""
    if fmt_json:
        return to_json_str(data)

    stream_list = data if isinstance(data, list) else []
    types_found = [s.get("type", "unknown") for s in stream_list]

    lines = [
        "# Activity Streams Data",
        f"- **Available Streams**: {', '.join(types_found) if types_found else 'None'}",
        f"- **Total Stream Data Points**: {len(stream_list[0].get('data', [])) if stream_list else 0}",
        "",
        "```json",
        to_json_str(data[:3] if isinstance(data, list) and len(data) > 3 else data),
        "```",
    ]
    return "\n".join(lines)


def format_wellness_list(wellness_list: List[Dict[str, Any]], fmt_json: bool = False) -> str:
    """Format daily wellness and recovery records."""
    if fmt_json:
        return to_json_str(wellness_list)

    if not wellness_list:
        return "No wellness records found for the requested period."

    lines = [
        f"# Wellness & Recovery History ({len(wellness_list)} days)",
        "",
        "| Date | Resting HR | HRV (rMSSD) | Weight | Sleep (h) | Quality | Readiness | Fatigue | Soreness | Stress | Mood |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    for w in wellness_list:
        date_str = w.get("id", "N/A")
        r_hr = f"{w.get('restingHR', '-')}"
        hrv = f"{w.get('hrv', '-')}"
        weight = f"{w.get('weight', '-')}"
        sleep_secs = w.get("sleepSecs")
        sleep_h = f"{sleep_secs / 3600:.1f}" if sleep_secs else "-"
        sq = f"{w.get('sleepQuality', '-')}"
        readiness = f"{w.get('readiness', '-')}"
        fatigue = f"{w.get('fatigue', '-')}"
        soreness = f"{w.get('soreness', '-')}"
        stress = f"{w.get('stress', '-')}"
        mood = f"{w.get('mood', '-')}"

        lines.append(f"| {date_str} | {r_hr} | {hrv} | {weight} | {sleep_h} | {sq} | {readiness} | {fatigue} | {soreness} | {stress} | {mood} |")

    return "\n".join(lines)


def format_fitness_summary(wellness_list: List[Dict[str, Any]], fmt_json: bool = False) -> str:
    """Format CTL (Fitness), ATL (Fatigue), and TSB (Form) summary."""
    if fmt_json:
        return to_json_str(wellness_list)

    if not wellness_list:
        return "No fitness tracking records found."

    latest = wellness_list[-1]
    date_str = latest.get("id", "Recent")
    ctl = latest.get("ctl", 0.0)
    atl = latest.get("atl", 0.0)
    tsb = ctl - atl if ctl is not None and atl is not None else latest.get("tsb", 0.0)
    ramp_rate = latest.get("rampRate", "N/A")

    # Form interpretation
    if tsb > 25:
        form_status = "Transition / Detraining (TSB > +25)"
    elif 10 <= tsb <= 25:
        form_status = "Fresh / Peak Race Performance (+10 to +25)"
    elif -10 <= tsb < 10:
        form_status = "Neutral / Productive Training (-10 to +10)"
    elif -30 <= tsb < -10:
        form_status = "Optimal Overload / Building Fitness (-30 to -10)"
    else:
        form_status = "High Fatigue / Overreaching Risk (TSB < -30)"

    lines = [
        f"# Training Load & Fitness Status ({date_str})",
        "",
        f"- **CTL (Fitness / Chronic Training Load)**: {ctl:.1f}",
        f"- **ATL (Fatigue / Acute Training Load)**: {atl:.1f}",
        f"- **TSB (Form / Training Stress Balance)**: {tsb:.1f}",
        f"- **Ramp Rate**: {ramp_rate}",
        f"- **Form Assessment**: **{form_status}**",
        "",
        "## Recent 7-Day Trend",
        "| Date | CTL (Fitness) | ATL (Fatigue) | TSB (Form) | Load |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ]

    for item in wellness_list[-7:]:
        d = item.get("id", "-")
        c = item.get("ctl", 0.0)
        a = item.get("atl", 0.0)
        t = c - a if c is not None and a is not None else item.get("tsb", 0.0)
        ld = item.get("load", item.get("training_load", "-"))
        lines.append(f"| {d} | {c:.1f} | {a:.1f} | {t:.1f} | {ld} |")

    return "\n".join(lines)


def format_events_list(events: List[Dict[str, Any]], fmt_json: bool = False) -> str:
    """Format planned calendar workouts and events."""
    if fmt_json:
        return to_json_str(events)

    if not events:
        return "No planned events or workouts scheduled in this date window."

    lines = [
        f"# Planned Workouts & Events ({len(events)} events)",
        "",
        "| Date | Title | Category | Sport | Planned Duration | Planned Load | Description |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    for ev in events:
        date_str = ev.get("start_date_local", "N/A")[:10]
        name = ev.get("name", "Untitled")
        ev_id = ev.get("id", "")
        cat = ev.get("category", "WORKOUT")
        sport = ev.get("type", "Ride")
        moving_time = ev.get("moving_time", 0)
        dur_str = f"{moving_time // 3600}h {(moving_time % 3600) // 60}m" if moving_time else "-"
        load = f"{ev.get('icu_training_load', '-')}"
        desc = (ev.get("description") or "").replace("\n", " ")[:40]

        lines.append(f"| {date_str} | [{name}](id:{ev_id}) | {cat} | {sport} | {dur_str} | {load} | {desc} |")

    return "\n".join(lines)


def format_folders(folders: List[Dict[str, Any]], fmt_json: bool = False) -> str:
    """Format workout library folders."""
    if fmt_json:
        return to_json_str(folders)

    lines = ["# Workout Library Folders", ""]
    for f in folders:
        f_id = f.get("id", "N/A")
        f_name = f.get("name", "Untitled Folder")
        child_count = len(f.get("children", []))
        lines.append(f"- **{f_name}** (ID: `{f_id}`) - {child_count} items")

    return "\n".join(lines)


def format_workouts(workouts: List[Dict[str, Any]], fmt_json: bool = False) -> str:
    """Format workout templates."""
    if fmt_json:
        return to_json_str(workouts)

    lines = ["# Workout Templates", ""]
    for w in workouts:
        w_id = w.get("id", "N/A")
        w_name = w.get("name", "Untitled Workout")
        w_type = w.get("type", "Ride")
        load = w.get("icu_training_load", "-")
        lines.append(f"## {w_name} (ID: `{w_id}`)")
        lines.append(f"- **Sport**: {w_type} | **Planned Load**: {load}")
        desc = w.get("description")
        if desc:
            lines.append(f"- **Description**: {desc}")
        lines.append("")

    return "\n".join(lines)
