import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta
import locale
import re


@dataclass
class CalendarEvent:
    title: str
    start: datetime
    end: datetime
    location: str = ""
    notes: str = ""
    calendar: str = ""


class AppleCalendarClient:

    @staticmethod
    def _date_set_script(var: str, dt: datetime) -> str:
        """Generate AppleScript to set a date variable from components (locale-independent)."""
        return (
            f'set {var} to current date\n'
            f'set day of {var} to 1\n'
            f'set year of {var} to {dt.year}\n'
            f'set month of {var} to {dt.month}\n'
            f'set day of {var} to {dt.day}\n'
            f'set hours of {var} to {dt.hour}\n'
            f'set minutes of {var} to {dt.minute}\n'
            f'set seconds of {var} to {dt.second}'
        )

    @staticmethod
    def _date_format_expr(var: str) -> str:
        """AppleScript expression that formats a date variable as ISO string."""
        return (
            f'((year of {var}) as string) & "-" & '
            f'text -2 thru -1 of ("0" & ((month of {var}) as integer)) & "-" & '
            f'text -2 thru -1 of ("0" & (day of {var})) & " " & '
            f'text -2 thru -1 of ("0" & (hours of {var})) & ":" & '
            f'text -2 thru -1 of ("0" & (minutes of {var})) & ":" & '
            f'text -2 thru -1 of ("0" & (seconds of {var}))'
        )

    def _run_applescript(self, script: str) -> str:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".scpt", delete=True) as f:
            f.write(script)
            f.flush()
            result = subprocess.run(
                ["osascript", f.name],
                capture_output=True,
                text=True,
                timeout=30,
            )
        if result.returncode != 0:
            raise RuntimeError(f"AppleScript error: {result.stderr.strip()}")
        return result.stdout.strip()

    def get_events(
        self,
        period: str = "today",
        date: str | None = None,
    ) -> list[CalendarEvent]:
        if date:
            target = datetime.strptime(date, "%Y-%m-%d")
        else:
            target = datetime.now()

        if period == "today":
            start = target.replace(hour=0, minute=0, second=0)
            end = target.replace(hour=23, minute=59, second=59)
        elif period == "tomorrow":
            target = target + timedelta(days=1)
            start = target.replace(hour=0, minute=0, second=0)
            end = target.replace(hour=23, minute=59, second=59)
        elif period == "week":
            start = target.replace(hour=0, minute=0, second=0)
            end = (target + timedelta(days=7)).replace(hour=23, minute=59, second=59)
        elif period == "month":
            start = target.replace(hour=0, minute=0, second=0)
            end = (target + timedelta(days=30)).replace(hour=23, minute=59, second=59)
        else:
            start = target.replace(hour=0, minute=0, second=0)
            end = target.replace(hour=23, minute=59, second=59)

        return self._get_events_range(start, end)

    def get_events_today(self) -> list[CalendarEvent]:
        return self.get_events("today")

    def _get_events_range(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        set_start = self._date_set_script("startDate", start)
        set_end = self._date_set_script("endDate", end)
        fmt_start = self._date_format_expr("d1")
        fmt_end = self._date_format_expr("d2")

        script = f'''
{set_start}
{set_end}
tell application "Calendar"
    set output to ""
    repeat with aCal in calendars
        set calName to name of aCal
        try
            set calEvents to (every event of aCal whose start date >= startDate and start date <= endDate)
            repeat with anEvent in calEvents
                set d1 to start date of anEvent
                set evtStart to {fmt_start}
                set d2 to end date of anEvent
                set evtEnd to {fmt_end}
                set evtSummary to summary of anEvent
                set evtLocation to ""
                try
                    set evtLocation to location of anEvent
                end try
                set output to output & evtSummary & "|||" & evtStart & "|||" & evtEnd & "|||" & evtLocation & "|||" & calName & "\\n"
            end repeat
        end try
    end repeat
    return output
end tell
'''
        try:
            raw = self._run_applescript(script)
        except Exception:
            return []

        return self._parse_events(raw)

    def create_event(
        self,
        title: str,
        start_datetime: str,
        end_datetime: str,
        location: str = "",
        notes: str = "",
        calendar: str = "Calendrier",
    ) -> str:
        start = datetime.fromisoformat(start_datetime)
        end = datetime.fromisoformat(end_datetime)

        set_start = self._date_set_script("startDate", start)
        set_end = self._date_set_script("endDate", end)

        # Sanitize inputs for AppleScript (prevent injection)
        safe_title = title.replace('"', '\\"').replace("\\", "\\\\")
        safe_notes = notes.replace('"', '\\"').replace("\\", "\\\\")
        safe_location = location.replace('"', '\\"').replace("\\", "\\\\")
        safe_calendar = calendar.replace('"', '\\"').replace("\\", "\\\\")

        script = f'''
{set_start}
{set_end}
tell application "Calendar"
    tell calendar "{safe_calendar}"
        set newEvent to make new event with properties {{summary:"{safe_title}", start date:startDate, end date:endDate, description:"{safe_notes}", location:"{safe_location}"}}
    end tell
end tell
'''
        self._run_applescript(script)
        return f"Événement créé: {title} le {start.strftime('%d/%m/%Y %H:%M')} - {end.strftime('%H:%M')}"

    def find_free_slots(
        self,
        date: str | None = None,
        duration_minutes: int = 60,
    ) -> str:
        if date:
            target = datetime.strptime(date, "%Y-%m-%d")
        else:
            target = datetime.now()

        start = target.replace(hour=8, minute=0, second=0)
        end = target.replace(hour=20, minute=0, second=0)
        events = self._get_events_range(start, end)

        # Sort events by start time
        events.sort(key=lambda e: e.start)

        free_slots = []
        current = start

        for event in events:
            if event.start > current:
                gap = (event.start - current).total_seconds() / 60
                if gap >= duration_minutes:
                    free_slots.append(
                        f"{current.strftime('%H:%M')} - {event.start.strftime('%H:%M')} ({int(gap)} min)"
                    )
            if event.end > current:
                current = event.end

        if current < end:
            gap = (end - current).total_seconds() / 60
            if gap >= duration_minutes:
                free_slots.append(
                    f"{current.strftime('%H:%M')} - {end.strftime('%H:%M')} ({int(gap)} min)"
                )

        if not free_slots:
            return "Aucun créneau libre trouvé."
        return "Créneaux libres:\n" + "\n".join(f"  • {s}" for s in free_slots)

    def get_week_summary(self) -> str:
        now = datetime.now()
        start = now.replace(hour=0, minute=0, second=0)
        end = (now + timedelta(days=7)).replace(hour=23, minute=59, second=59)
        events = self._get_events_range(start, end)
        events.sort(key=lambda e: e.start)

        if not events:
            return "Aucun événement cette semaine."

        # French day/month names
        JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
        MOIS = ["", "janvier", "février", "mars", "avril", "mai", "juin",
                "juillet", "août", "septembre", "octobre", "novembre", "décembre"]

        lines = []
        current_day = None
        for event in events:
            day = f"{JOURS[event.start.weekday()]} {event.start.day} {MOIS[event.start.month]}"
            if day != current_day:
                lines.append(f"\n**{day}**")
                current_day = day
            time_str = f"{event.start.strftime('%H:%M')}-{event.end.strftime('%H:%M')}"
            loc = f" @ {event.location}" if event.location else ""
            lines.append(f"  • {time_str} — {event.title}{loc}")

        return "\n".join(lines)

    def _parse_events(self, raw: str) -> list[CalendarEvent]:
        events = []
        for line in raw.split("\n"):
            line = line.strip()
            if not line:
                continue
            parts = line.split("|||")
            if len(parts) >= 3:
                title = parts[0].strip()
                try:
                    start = self._parse_applescript_date(parts[1].strip())
                    end = self._parse_applescript_date(parts[2].strip())
                except (ValueError, IndexError):
                    continue
                location = parts[3].strip() if len(parts) > 3 else ""
                if location == "missing value":
                    location = ""
                calendar = parts[4].strip() if len(parts) > 4 else ""
                events.append(CalendarEvent(
                    title=title,
                    start=start,
                    end=end,
                    location=location,
                    calendar=calendar,
                ))
        return events

    def _parse_applescript_date(self, date_str: str) -> datetime:
        # ISO format first (our AppleScript outputs this), then fallbacks
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%d/%m/%Y %H:%M:%S",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        # Last resort: try dateutil
        raise ValueError(f"Cannot parse date: {date_str}")
