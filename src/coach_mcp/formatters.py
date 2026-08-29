"""Formatters to render Intervals.icu data into structured JSON and agent-friendly Markdown."""

import json
from typing import Any, cast

from coach_mcp.models import ResponseFormat


def to_json_str(data: Any) -> str:
    """Format Python object as indented JSON string."""
    return json.dumps(data, indent=2, default=str)


def format_profile(data: dict[str, Any], fmt_json: bool = False) -> str:
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
            lines.append(
                "- **Power Zones (Watts)**: "
                + ", ".join(f"Z{i + 1}: {z}W" for i, z in enumerate(power_zones))
            )

        hr_zones = sport.get("hr_zones", [])
        if hr_zones:
            lines.append(
                "- **HR Zones (bpm)**: "
                + ", ".join(f"Z{i + 1}: {z}bpm" for i, z in enumerate(hr_zones))
            )

        lines.append("")

    return "\n".join(lines)


def format_activities_list(activities: list[dict[str, Any]], fmt_json: bool = False) -> str:
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
        avg_hr = (
            f"{act.get('average_heartrate', 0):.0f} bpm" if act.get("average_heartrate") else "-"
        )
        load = (
            f"{act.get('icu_training_load', 0):.0f}"
            if act.get("icu_training_load") is not None
            else "-"
        )

        lines.append(
            f"| {date_str} | [{name}](id:{act_id}) | {act_type} | {dur_str} | {dist_km} | {avg_watts} | {avg_hr} | {load} |"  # noqa: E501
        )

    return "\n".join(lines)


def format_activity_detail(act: dict[str, Any], fmt_json: bool = False) -> str:
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
        f"- **Average Power**: {act.get('average_watts', 'N/A')} W "
        f"(Max: {act.get('max_watts', 'N/A')} W)",
        f"- **Training Load (TSS)**: {act.get('icu_training_load', 'N/A')}",
        f"- **Intensity Factor (IF)**: {act.get('icu_intensity', 'N/A')}",
        f"- **Average Heart Rate**: {act.get('average_heartrate', 'N/A')} bpm "
        f"(Max: {act.get('max_heartrate', 'N/A')} bpm)",
        f"- **Average Cadence**: {act.get('average_cadence', 'N/A')} rpm",
        f"- **Aerobic / Anaerobic Training Effect**: "
        f"{act.get('icu_aerobic_training_effect', 'N/A')} / "
        f"{act.get('icu_anaerobic_training_effect', 'N/A')}",
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
        f"- **Total Stream Data Points**: "
        f"{len(stream_list[0].get('data', [])) if stream_list else 0}",
        "",
        "```json",
        to_json_str(data[:3] if isinstance(data, list) and len(data) > 3 else data),
        "```",
    ]
    return "\n".join(lines)


def format_wellness_list(wellness_list: list[dict[str, Any]], fmt_json: bool = False) -> str:
    """Format daily wellness and recovery records."""
    if fmt_json:
        return to_json_str(wellness_list)

    if not wellness_list:
        return "No wellness records found for the requested period."

    lines = [
        f"# Wellness & Recovery History ({len(wellness_list)} days)",
        "",
        "| Date | Resting HR | HRV (rMSSD) | Weight | Sleep (h) | Quality | Readiness | Fatigue | Soreness | Stress | Mood |",  # noqa: E501
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

        lines.append(
            f"| {date_str} | {r_hr} | {hrv} | {weight} | {sleep_h} | {sq} | {readiness} | {fatigue} | {soreness} | {stress} | {mood} |"  # noqa: E501
        )

    return "\n".join(lines)


def _compute_fitness_metrics(wellness_entries: list[dict[str, Any]]) -> dict[str, Any]:
    """Extract latest CTL, ATL, TSB, and ramp rate from wellness entries."""
    if not wellness_entries:
        return {
            "ctl": None,
            "atl": None,
            "tsb": None,
            "ramp_rate": None,
            "date": None,
        }

    latest = wellness_entries[-1]
    ctl = latest.get("ctl")
    atl = latest.get("atl")
    tsb = latest.get("tsb")
    if ctl is not None and atl is not None and tsb is None:
        tsb = ctl - atl
    ramp_rate = latest.get("rampRate")
    if ramp_rate is None and len(wellness_entries) >= 2:
        previous = wellness_entries[-2]
        prev_ctl = previous.get("ctl")
        if prev_ctl is not None and ctl is not None:
            ramp_rate = round(ctl - prev_ctl, 1)

    return {
        "ctl": ctl,
        "atl": atl,
        "tsb": tsb,
        "ramp_rate": ramp_rate,
        "date": latest.get("id"),
    }


def _form_status(tsb: float | None) -> str:
    """Map TSB value to a training status label."""
    if tsb is None:
        return "Unknown"
    if tsb > 25:
        return "Transition / Detraining (TSB > +25)"
    if 10 <= tsb <= 25:
        return "Fresh / Peak Race Performance (+10 to +25)"
    if -10 <= tsb < 10:
        return "Neutral / Productive Training (-10 to +10)"
    if -30 <= tsb < -10:
        return "Optimal Overload / Building Fitness (-30 to -10)"
    return "High Fatigue / Overreaching Risk (TSB < -30)"


def format_fitness_summary(wellness_list: list[dict[str, Any]], fmt_json: bool = False) -> str:
    """Format CTL (Fitness), ATL (Fatigue), and TSB (Form) summary."""
    if fmt_json:
        return to_json_str(wellness_list)

    if not wellness_list:
        return "No fitness tracking records found."

    metrics = _compute_fitness_metrics(wellness_list)
    date_str = metrics.get("date", "Recent") or "Recent"
    ctl = metrics.get("ctl", 0.0)
    atl = metrics.get("atl", 0.0)
    tsb = metrics.get("tsb", 0.0)
    ramp_rate = metrics.get("ramp_rate", "N/A")
    form_status = _form_status(tsb)

    ctl_label = "CTL (Fitness / Chronic Training Load)"
    atl_label = "ATL (Fatigue / Acute Training Load)"
    tsb_label = "TSB (Form / Training Stress Balance)"
    ctl_line = f"- **{ctl_label}**: {ctl:.1f}" if ctl is not None else f"- **{ctl_label}**: N/A"
    atl_line = f"- **{atl_label}**: {atl:.1f}" if atl is not None else f"- **{atl_label}**: N/A"
    tsb_line = f"- **{tsb_label}**: {tsb:.1f}" if tsb is not None else f"- **{tsb_label}**: N/A"

    lines = [
        f"# Training Load & Fitness Status ({date_str})",
        "",
        ctl_line,
        atl_line,
        tsb_line,
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


def _extract_cycling_settings(sport_settings: Any) -> dict[str, Any]:
    """Select the cycling sport settings from a list or dict payload."""
    if not sport_settings:
        return {}

    settings_list = sport_settings if isinstance(sport_settings, list) else [sport_settings]
    for sport in settings_list:
        types = sport.get("types", [])
        if isinstance(types, list) and "Ride" in types:
            return cast(dict[str, Any], sport)
    return cast(dict[str, Any], settings_list[0])


def _sleep_hours(seconds: Any) -> str:
    """Convert sleep seconds to a readable hours label."""
    try:
        return f"{float(seconds) / 3600:.1f} h"
    except (TypeError, ValueError):
        return "N/A"


def _recommendation(metrics: dict[str, Any], latest: dict[str, Any] | None) -> str:
    """Generate an actionable coaching recommendation from TSB and wellness."""
    tsb = metrics.get("tsb")
    readiness = latest.get("readiness") if latest else None
    soreness = latest.get("soreness") if latest else None
    fatigue = latest.get("fatigue") if latest else None

    if readiness is not None and readiness < 50:
        return (
            "Low readiness score — prioritize recovery, sleep, "
            "and easy movement today."
        )
    if (soreness is not None and soreness >= 3) or (fatigue is not None and fatigue >= 3):
        return "Elevated soreness/fatigue — reduce intensity and focus on recovery."
    if tsb is None:
        return (
            "Insufficient fitness data — follow your planned schedule "
            "and monitor recovery."
        )
    if tsb > 25:
        return "Fresh — suitable for high-intensity session or race performance."
    if 10 <= tsb <= 25:
        return "Optimal — proceed with planned training including quality work."
    if -10 <= tsb < 10:
        return "Productive — maintain planned load with attention to recovery."
    if -30 <= tsb < -10:
        return "Overload — keep volume moderate, prioritize sleep and nutrition."
    return "High fatigue — take a rest day or very easy spin."


def format_readiness_dashboard(
    wellness_data: list[dict[str, Any]],
    sport_settings: Any,
    fmt_json: bool = False,
) -> str:
    """Format composite daily readiness dashboard from wellness and sport settings."""
    latest = wellness_data[-1] if wellness_data else {}
    metrics = _compute_fitness_metrics(wellness_data)
    cycling = _extract_cycling_settings(sport_settings)
    recommendation = _recommendation(metrics, latest if latest else None)

    if fmt_json:
        sleep_secs = latest.get("sleepSecs")
        return to_json_str(
            {
                "date": metrics.get("date"),
                "wellness": {
                    "hrv": latest.get("hrv"),
                    "resting_hr": latest.get("restingHR"),
                    "sleep_hours": _sleep_hours(sleep_secs) if sleep_secs is not None else None,
                    "sleep_quality": latest.get("sleepQuality"),
                    "readiness_score": latest.get("readiness"),
                    "soreness": latest.get("soreness"),
                    "fatigue": latest.get("fatigue"),
                    "stress": latest.get("stress"),
                },
                "fitness": {
                    "ctl": metrics.get("ctl"),
                    "atl": metrics.get("atl"),
                    "tsb": metrics.get("tsb"),
                    "ramp_rate": metrics.get("ramp_rate"),
                    "status": _form_status(metrics.get("tsb")),
                },
                "cycling_parameters": {
                    "ftp_watts": cycling.get("ftp"),
                    "indoor_ftp_watts": cycling.get("indoor_ftp"),
                    "lthr_bpm": cycling.get("lthr"),
                    "max_hr_bpm": cycling.get("max_hr"),
                    "power_zones": cycling.get("power_zones", []),
                },
                "recommendation": recommendation,
            }
        )

    date_str = metrics.get("date") or "Latest"
    hrv = latest.get("hrv", "N/A")
    resting_hr = latest.get("restingHR", "N/A")
    sleep_secs = latest.get("sleepSecs")
    sleep = _sleep_hours(sleep_secs) if sleep_secs is not None else "N/A"
    readiness = latest.get("readiness", "N/A")
    soreness = latest.get("soreness", "N/A")
    fatigue = latest.get("fatigue", "N/A")
    stress = latest.get("stress", "N/A")

    ctl = metrics.get("ctl")
    atl = metrics.get("atl")
    tsb = metrics.get("tsb")
    ramp_rate = metrics.get("ramp_rate", "N/A")
    status = _form_status(tsb)

    ftp = cycling.get("ftp", "N/A")
    indoor_ftp = cycling.get("indoor_ftp", "N/A")
    lthr = cycling.get("lthr", "N/A")
    max_hr = cycling.get("max_hr", "N/A")
    power_zones = cycling.get("power_zones", [])

    ctl_line = f"- **CTL (Fitness)**: {ctl:.1f}" if ctl is not None else "- **CTL (Fitness)**: N/A"
    atl_line = f"- **ATL (Fatigue)**: {atl:.1f}" if atl is not None else "- **ATL (Fatigue)**: N/A"
    tsb_line = f"- **TSB (Form)**: {tsb:.1f}" if tsb is not None else "- **TSB (Form)**: N/A"

    lines = [
        "# Daily Readiness & Training Dashboard",
        "",
        f"## Today's Wellness ({date_str})",
        f"- **HRV (rMSSD)**: {hrv} ms",
        f"- **Resting HR**: {resting_hr} bpm",
        f"- **Sleep**: {sleep}",
        f"- **Readiness Score**: {readiness}",
        f"- **Soreness**: {soreness}",
        f"- **Fatigue**: {fatigue}",
        f"- **Stress**: {stress}",
        "",
        "## Banister Fitness & Form",
        ctl_line,
        atl_line,
        tsb_line,
        f"- **Ramp Rate**: {ramp_rate}",
        f"- **Status**: **{status}**",
        "",
        "## Active Cycling Parameters",
        f"- **FTP**: {ftp} W (Indoor: {indoor_ftp} W)",
        f"- **LTHR**: {lthr} bpm | **Max HR**: {max_hr} bpm",
    ]

    if power_zones:
        zones_str = ", ".join(f"Z{i + 1}: {z}W" for i, z in enumerate(power_zones))
        lines.append(f"- **Power Zones**: {zones_str}")
    else:
        lines.append("- **Power Zones**: Not configured")

    lines.extend(["", "## Coaching Recommendation", recommendation])

    return "\n".join(lines)


def format_events_list(events: list[dict[str, Any]], fmt_json: bool = False) -> str:
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

        lines.append(
            f"| {date_str} | [{name}](id:{ev_id}) | {cat} | {sport} | {dur_str} | {load} | {desc} |"
        )

    return "\n".join(lines)


def format_folders(folders: list[dict[str, Any]], fmt_json: bool = False) -> str:
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


def format_workouts(workouts: list[dict[str, Any]], fmt_json: bool = False) -> str:
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


def _format_duration(seconds: int | float | str) -> str:
    """Convert seconds into a human-readable duration label."""
    try:
        secs = int(seconds)
    except (ValueError, TypeError):
        return str(seconds)

    if secs < 60:
        return f"{secs}s"
    if secs < 3600:
        return f"{secs // 60}m"
    hours = secs // 3600
    minutes = (secs % 3600) // 60
    if minutes == 0:
        return f"{hours}h"
    return f"{hours}h {minutes}m"


def _extract_power_curve_points(data: dict[str, Any] | list[Any]) -> list[dict[str, Any]]:
    """Extract normalized (duration, watts, wkg) points from various power curve shapes."""
    if isinstance(data, list):
        return [
            {
                "duration": item.get("duration", item.get("secs", "-")),
                "watts": item.get("watts", item.get("power", "-")),
                "wkg": item.get("wkg", "-"),
            }
            for item in data
            if isinstance(item, dict)
        ]

    points: list[dict[str, Any]] = []

    # Flat activity power curve: {seconds: watts}
    if data and all(not isinstance(v, dict) for v in data.values()):
        for duration, watts in data.items():
            points.append(
                {
                    "duration": duration,
                    "watts": watts,
                    "wkg": "-",
                }
            )
        return points

    # Intervals.icu athlete power-curves returns {sport_type: {seconds: watts}}
    for sport_type, curve in data.items():
        if not isinstance(curve, dict):
            continue
        for duration, watts in curve.items():
            if isinstance(watts, dict):
                points.append(
                    {
                        "sport": sport_type,
                        "duration": duration,
                        "watts": watts.get("watts", watts.get("power", "-")),
                        "wkg": watts.get("wkg", "-"),
                    }
                )
            else:
                points.append(
                    {
                        "sport": sport_type,
                        "duration": duration,
                        "watts": watts,
                        "wkg": "-",
                    }
                )
    return points


def format_power_curve(
    data: dict[str, Any] | list[Any],
    response_format: ResponseFormat = ResponseFormat.MARKDOWN,
) -> str:
    """Format power-duration / MMP curve data as markdown table or JSON."""
    if response_format == ResponseFormat.JSON:
        return to_json_str(data)

    if not data:
        return "# Power Curve\n\nNo power curve data available."

    points = _extract_power_curve_points(data)

    # If data is a flat activity power curve dict, points will have no sport key
    is_activity_curve = isinstance(data, dict) and not any("sport" in p for p in points)

    title = "# Activity Power Curve" if is_activity_curve else "# Power Curve"
    lines = [title, ""]

    # Include eFTP / critical power if present at top level
    eftp = data.get("eftp") if isinstance(data, dict) else None
    cp = data.get("cp") if isinstance(data, dict) else None
    if eftp is not None:
        lines.append(f"- **eFTP**: {eftp} W")
    if cp is not None:
        lines.append(f"- **Critical Power (CP)**: {cp} W")
    if eftp is not None or cp is not None:
        lines.append("")

    if not points:
        lines.append("No power-duration points found in response.")
        return "\n".join(lines)

    lines.append("| Duration | Watts | W/kg | Sport |")
    lines.append("| :--- | :--- | :--- | :--- |")

    for point in points:
        duration = _format_duration(point["duration"])
        watts = point.get("watts", "-")
        wkg = point.get("wkg", "-")
        sport = point.get("sport", "-")
        lines.append(f"| {duration} | {watts} | {wkg} | {sport} |")

    return "\n".join(lines)


def format_power_model(data: dict[str, Any], fmt_json: bool = False) -> str:
    """Format critical power (CP), W', and Pmax model as markdown or JSON."""
    if fmt_json:
        return to_json_str(data)

    if not data:
        return "# Critical Power Model\n\nNo power model data available."

    sport_type = data.get("sport_type", data.get("type", "Ride"))
    lines = [f"# Critical Power Model ({sport_type})", ""]

    # Critical Power (CP) - check multiple possible field names
    cp = data.get("cp", data.get("ftp"))
    if cp is None:
        cp = data.get("critical_power")
    if cp is not None:
        lines.append(f"- **Critical Power (CP)**: {cp} W")

    # Anaerobic Work Capacity (W')
    w_prime = data.get("wPrime", data.get("w_prime", data.get("wprime")))
    if w_prime is None:
        w_prime = data.get("anaerobic_work_capacity")
    if w_prime is not None:
        # Display in kJ if value is large (Joules), otherwise assume kJ
        if isinstance(w_prime, (int, float)) and w_prime >= 1000:
            w_prime_kj = w_prime / 1000
            lines.append(f"- **Anaerobic Work Capacity ($W'$)**: {w_prime} J ({w_prime_kj:.1f} kJ)")
        else:
            lines.append(f"- **Anaerobic Work Capacity ($W'$)**: {w_prime} kJ")

    # Peak Neuromuscular Power (Pmax)
    p_max = data.get("pMax", data.get("p_max", data.get("pmax")))
    if p_max is None:
        p_max = data.get("peak_power")
    if p_max is not None:
        lines.append(f"- **Peak Neuromuscular Power ($P_{{max}}$)**: {p_max} W")

    # Model Type / Name
    model_type = data.get("model", data.get("name", data.get("fit_type", data.get("type"))))
    if model_type is not None and model_type != sport_type:
        lines.append(f"- **Model Type**: {model_type}")

    # Estimated/Model FTP if available and distinct from CP
    ftp = data.get("ftp")
    if ftp is not None and ftp != cp:
        lines.append(f"- **Estimated FTP**: {ftp} W")

    if len(lines) == 2:
        lines.append("No model parameters found in response.")

    return "\n".join(lines)
