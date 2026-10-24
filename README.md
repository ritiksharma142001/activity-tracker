# Activity Tracker

A Linux desktop app that automatically records how much time you spend in each
app and window. Idle time (3+ minutes without input) and sleep are not counted.
All data stays on your computer in `~/.local/share/activity-tracker/activity.db`.

## How it works

| Piece | File | Job |
|---|---|---|
| GNOME Shell extension | `extension/` | Tells the app which window is focused (Wayland blocks apps from seeing this directly) |
| Background service | `activity_tracker/daemon.py` | Every 5 s, saves the focused app and window title to SQLite |
| App window | `activity_tracker/ui.py` | GTK4/libadwaita window showing usage per day |

On X11 desktops other than GNOME, it falls back to `xprop`, so the extension isn't needed.

## Install (from source)

```sh
# Ubuntu/Debian dependencies (Fedora: sudo dnf install python3-gobject gtk4 libadwaita)
sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1

./install.sh
```

On GNOME, the installer (or the **Turn On** button in the app) installs the helper
extension from extensions.gnome.org. GNOME asks you to confirm, and tracking starts
right away with no logout.

Command line: `activity-tracker --report` prints today's usage.

Uninstall: `./uninstall.sh` (add `--purge` to delete recorded data too).

## Flatpak

```sh
flatpak install flathub org.gnome.Platform//50 org.gnome.Sdk//50
flatpak-builder --user --install --force-clean build io.github.ritiksharma142001.ActivityTracker.yml
flatpak run io.github.ritiksharma142001.ActivityTracker
```

The Flatpak's **Turn On** button installs the helper extension the same way.

## Publishing the extension

Build the upload file with
`gnome-extensions pack extension/activity-tracker@io.github.ritiksharma142001`
and upload it at https://extensions.gnome.org/upload/. Until it's approved, the
installer falls back to a local copy that GNOME loads at the next login.
