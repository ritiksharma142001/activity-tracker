"""Where the focused window and idle time come from.

GNOME (Wayland or X11): our Shell extension over D-Bus.
Other X11 desktops: xprop.
Idle time: GNOME's Mutter IdleMonitor.
"""
import json
import os
import re
import shutil
import subprocess

import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib

EXT_NAME = "io.github.ActivityTracker.Shell"
EXT_PATH = "/io/github/ActivityTracker/Shell"
EXT_UUID = "activity-tracker@io.github.ritiksharma142001"


class SystemSource:
    def __init__(self):
        self.bus = Gio.bus_get_sync(Gio.BusType.SESSION)

    def _call(self, name, path, iface, method, args=None, timeout_ms=1000):
        return self.bus.call_sync(name, path, iface, method, args, None,
                                  Gio.DBusCallFlags.NO_AUTO_START, timeout_ms, None).unpack()

    def extension_available(self):
        try:
            return self._call("org.freedesktop.DBus", "/org/freedesktop/DBus",
                              "org.freedesktop.DBus", "NameHasOwner",
                              GLib.Variant("(s)", (EXT_NAME,)))[0]
        except GLib.Error:
            return False

    def focused_window(self):
        """Return {'app_id', 'app_name', 'title'} or None."""
        try:
            data = json.loads(self._call(EXT_NAME, EXT_PATH, EXT_NAME, "GetFocusedWindow")[0])
            return data or None
        except GLib.Error:
            pass
        if os.environ.get("XDG_SESSION_TYPE") == "x11":
            return _x11_focused_window()
        return None

    def idle_ms(self):
        try:
            return self._call("org.gnome.Mutter.IdleMonitor", "/org/gnome/Mutter/IdleMonitor/Core",
                              "org.gnome.Mutter.IdleMonitor", "GetIdletime")[0]
        except GLib.Error:
            return 0


def _x11_focused_window():
    if not shutil.which("xprop"):
        return None
    try:
        root = subprocess.run(["xprop", "-root", "_NET_ACTIVE_WINDOW"],
                              capture_output=True, text=True, timeout=2).stdout
        match = re.search(r"window id # (0x[0-9a-f]+)", root)
        if not match or match.group(1) == "0x0":
            return None
        props = subprocess.run(["xprop", "-id", match.group(1), "WM_CLASS", "_NET_WM_NAME"],
                               capture_output=True, text=True, timeout=2).stdout
    except (subprocess.SubprocessError, OSError):
        return None
    wm_class = re.search(r'WM_CLASS\(STRING\) = "[^"]*", "([^"]*)"', props)
    title = re.search(r'_NET_WM_NAME\(UTF8_STRING\) = "(.*)"', props)
    name = wm_class.group(1) if wm_class else "Unknown"
    return {"app_id": name.lower(), "app_name": name, "title": title.group(1) if title else ""}
