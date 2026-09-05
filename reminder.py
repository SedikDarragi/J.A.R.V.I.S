import json
import os
import threading
from datetime import datetime, timedelta

from winotify import Notification, audio

_REMINDER_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reminders.json")


def _notify(message: str) -> None:
    """Show a Windows toast notification."""
    try:
        from winotify import Notification, audio
        toast = Notification(
            app_id="J.A.R.V.I.S.",
            title="Reminder",
            msg=message,
            duration="long",
        )
        toast.set_audio(audio.Default, loop=False)
        toast.show()
    except Exception:
        pass


class ReminderManager:
    """Manages scheduled reminders with popup notifications."""

    def __init__(self):
        self._reminders: list[dict] = []
        self._timers: list[threading.Timer] = []
        self._lock = threading.Lock()

    def add(self, seconds: int, message: str) -> str:
        """Schedule a reminder. Returns a confirmation message."""
        if seconds <= 0:
            return "Please specify a time in the future, sir."
        when = datetime.now() + timedelta(seconds=seconds)
        reminder = {
            "when": when.isoformat(),
            "message": message,
        }
        timer = threading.Timer(seconds, self._fire, args=[reminder])
        timer.daemon = True
        with self._lock:
            self._reminders.append(reminder)
            self._timers.append(timer)
        timer.start()
        if seconds < 60:
            return f"Reminder set for {seconds} seconds from now: {message}"
        elif seconds < 3600:
            mins = seconds // 60
            return f"Reminder set for {mins} minute(s) from now: {message}"
        else:
            hrs = seconds // 3600
            return f"Reminder set for {hrs} hour(s) from now: {message}"

    def _fire(self, reminder: dict) -> None:
        """Called by the Timer when the reminder is due."""
        with self._lock:
            if reminder in self._reminders:
                self._reminders.remove(reminder)
        _notify(reminder["message"])

    def list_reminders(self) -> str:
        with self._lock:
            now = datetime.now()
            active = []
            for r in self._reminders:
                when = datetime.fromisoformat(r["when"])
                if when > now:
                    delta = when - now
                    secs = int(delta.total_seconds())
                    if secs < 60:
                        active.append(f"  - {r['message']} (in {secs}s)")
                    elif secs < 3600:
                        active.append(f"  - {r['message']} (in {secs // 60}m)")
                    else:
                        active.append(f"  - {r['message']} (in {secs // 3600}h)")
            if not active:
                return "No active reminders, sir."
            return "Active reminders:\n" + "\n".join(active)

    def cancel_all(self) -> str:
        with self._lock:
            count = len(self._reminders)
            for t in self._timers:
                t.cancel()
            self._reminders.clear()
            self._timers.clear()
        if count:
            return f"Cancelled {count} reminder(s), sir."
        return "No reminders to cancel, sir."


_manager: ReminderManager | None = None


def get_manager() -> ReminderManager:
    global _manager
    if _manager is None:
        _manager = ReminderManager()
    return _manager
