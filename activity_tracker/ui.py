import datetime
import os
import subprocess
import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, Gtk

from . import APP_ID, APP_NAME
from .daemon import is_running
from .db import Database
from .main import day_range, format_duration
from .sources import EXT_UUID, SystemSource

IN_FLATPAK = os.path.exists("/.flatpak-info")
EXTENSION_URL = "https://extensions.gnome.org/"


def ensure_daemon():
    if is_running():
        return
    package_parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env = dict(os.environ, PYTHONPATH=package_parent)
    subprocess.Popen([sys.executable, "-m", "activity_tracker", "--daemon"], env=env,
                     start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def request_flatpak_autostart():
    """Inside Flatpak we can't write ~/.config/autostart; ask the Background portal instead."""
    bus = Gio.bus_get_sync(Gio.BusType.SESSION)
    options = {
        "reason": GLib.Variant("s", "Record app usage in the background"),
        "autostart": GLib.Variant("b", True),
        "commandline": GLib.Variant("as", ["activity-tracker", "--daemon"]),
    }
    bus.call("org.freedesktop.portal.Desktop", "/org/freedesktop/portal/desktop",
             "org.freedesktop.portal.Background", "RequestBackground",
             GLib.Variant("(sa{sv})", ("", options)), None, Gio.DBusCallFlags.NONE, -1, None, None)


def app_icon(app_id):
    info = None
    try:
        info = Gio.DesktopAppInfo.new(app_id)
    except TypeError:
        pass
    image = Gtk.Image.new_from_gicon(info.get_icon()) if info and info.get_icon() \
        else Gtk.Image.new_from_icon_name("application-x-executable")
    image.set_pixel_size(32)
    return image


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title=APP_NAME, default_width=560, default_height=680)
        self.db = Database()
        self.source = SystemSource()
        self.day = datetime.date.today()

        header = Adw.HeaderBar()
        self.title = Adw.WindowTitle()
        header.set_title_widget(self.title)
        prev_btn = Gtk.Button(icon_name="go-previous-symbolic", tooltip_text="Previous day")
        prev_btn.connect("clicked", lambda _b: self.shift_day(-1))
        self.next_btn = Gtk.Button(icon_name="go-next-symbolic", tooltip_text="Next day")
        self.next_btn.connect("clicked", lambda _b: self.shift_day(1))
        header.pack_start(prev_btn)
        header.pack_start(self.next_btn)

        self.banner = Adw.Banner(
            title="Window tracking is off. Log out and back in, then enable the "
                  "“Activity Tracker Helper” extension.",
            button_label="Enable",
        )
        self.banner.connect("button-clicked", self.on_enable_extension)

        self.page_holder = Adw.Bin(vexpand=True)

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(header)
        toolbar.add_top_bar(self.banner)
        toolbar.set_content(self.page_holder)
        self.set_content(toolbar)

        self.refresh()
        GLib.timeout_add_seconds(30, self.on_tick)

    def on_enable_extension(self, _banner):
        if IN_FLATPAK:
            # The sandbox can't manage extensions; send the user to the extensions website.
            Gtk.UriLauncher.new(EXTENSION_URL).launch(self, None, None)
            return
        subprocess.run(["gnome-extensions", "enable", EXT_UUID], check=False)
        GLib.timeout_add_seconds(1, lambda: self.refresh() and False)

    def on_tick(self):
        if self.day == datetime.date.today():
            self.refresh()
        return GLib.SOURCE_CONTINUE

    def shift_day(self, delta):
        self.day = min(self.day + datetime.timedelta(days=delta), datetime.date.today())
        self.refresh()

    def refresh(self):
        today = datetime.date.today()
        self.next_btn.set_sensitive(self.day < today)
        self.banner.set_revealed(not self.source.extension_available()
                                 and os.environ.get("XDG_SESSION_TYPE") != "x11")

        t0, t1 = day_range(self.day)
        rows = self.db.usage_by_app(t0, t1)
        total = sum(secs for *_rest, secs in rows)

        if self.day == today:
            label = "Today"
        elif self.day == today - datetime.timedelta(days=1):
            label = "Yesterday"
        else:
            label = self.day.strftime("%a, %d %b %Y")
        self.title.set_title(label)
        self.title.set_subtitle(f"{format_duration(total)} active" if rows else "")

        if not rows:
            self.page_holder.set_child(Adw.StatusPage(
                icon_name="preferences-system-time-symbolic",
                title="No activity yet",
                description="Usage is recorded while you work. Check back in a few minutes.",
            ))
            return

        page = Adw.PreferencesPage()
        group = Adw.PreferencesGroup(title="Apps")
        page.add(group)
        top = rows[0][2]
        for app_id, name, secs in rows:
            row = Adw.ExpanderRow(title=GLib.markup_escape_text(name),
                                  subtitle=f"{format_duration(secs)} · {secs / total:.0%}")
            row.add_prefix(app_icon(app_id))
            bar = Gtk.LevelBar(value=secs / top, valign=Gtk.Align.CENTER, width_request=110)
            row.add_suffix(bar)
            for title, title_secs in self.db.top_titles(app_id, t0, t1):
                child = Adw.ActionRow(title=GLib.markup_escape_text(title or "(untitled)"),
                                      title_lines=1)
                child.add_suffix(Gtk.Label(label=format_duration(title_secs), css_classes=["dim-label"]))
                row.add_row(child)
            group.add(row)
        self.page_holder.set_child(page)


class TrackerApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)

    def do_activate(self):
        win = self.get_active_window() or MainWindow(self)
        win.present()

    def do_startup(self):
        Adw.Application.do_startup(self)
        ensure_daemon()
        if IN_FLATPAK:
            request_flatpak_autostart()


def run_ui():
    sys.exit(TrackerApp().run(None))
