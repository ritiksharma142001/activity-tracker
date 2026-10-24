#!/usr/bin/env bash
# Installs Activity Tracker for the current user (no sudo needed).
set -euo pipefail

APP_ID=io.github.ritiksharma142001.ActivityTracker
EXT_UUID=activity-tracker@io.github.ritiksharma142001
SRC="$(cd "$(dirname "$0")" && pwd)"
PREFIX="$HOME/.local"
LIB="$PREFIX/share/activity-tracker"
BIN="$PREFIX/bin/activity-tracker"

if ! python3 -c 'import gi; gi.require_version("Gtk", "4.0"); gi.require_version("Adw", "1")' 2>/dev/null; then
    echo "Missing GTK4/libadwaita for Python. Install them with:"
    echo "  Ubuntu/Debian: sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1"
    echo "  Fedora:        sudo dnf install python3-gobject gtk4 libadwaita"
    exit 1
fi

mkdir -p "$LIB" "$PREFIX/bin" "$PREFIX/share/applications" "$PREFIX/share/metainfo" \
         "$PREFIX/share/icons/hicolor/scalable/apps" "$HOME/.config/autostart"

rm -rf "$LIB/activity_tracker"
cp -r "$SRC/activity_tracker" "$LIB/"

cat > "$BIN" <<EOF
#!/bin/sh
export PYTHONPATH="$LIB\${PYTHONPATH:+:\$PYTHONPATH}"
exec python3 -m activity_tracker "\$@"
EOF
chmod +x "$BIN"

sed "s|^Exec=.*|Exec=$BIN|" "$SRC/data/$APP_ID.desktop" > "$PREFIX/share/applications/$APP_ID.desktop"
cp "$SRC/data/$APP_ID.metainfo.xml" "$PREFIX/share/metainfo/"
cp "$SRC/data/$APP_ID.svg" "$PREFIX/share/icons/hicolor/scalable/apps/"

# Start the tracking service automatically at login.
cat > "$HOME/.config/autostart/$APP_ID.Daemon.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Activity Tracker (background)
Exec=$BIN --daemon
NoDisplay=true
X-GNOME-Autostart-enabled=true
EOF

ext_active() { gnome-extensions info "$EXT_UUID" 2>/dev/null | grep -q "State: ACTIVE"; }

if [ "${XDG_CURRENT_DESKTOP:-}" != "${XDG_CURRENT_DESKTOP%GNOME*}" ] && ! ext_active; then
    gnome-extensions enable "$EXT_UUID" 2>/dev/null || true
    if ! ext_active; then
        # Installing from extensions.gnome.org loads the extension right away (no logout).
        echo "Installing the “Activity Tracker Helper” GNOME extension (confirm if GNOME asks)..."
        gdbus call --session --dest org.gnome.Shell --object-path /org/gnome/Shell \
            --method org.gnome.Shell.Extensions.InstallRemoteExtension "$EXT_UUID" >/dev/null 2>&1 || true
    fi
    if ! ext_active; then
        # Not on extensions.gnome.org yet: install the local copy, which GNOME loads at next login.
        EXT_DIR="$HOME/.local/share/gnome-shell/extensions/$EXT_UUID"
        mkdir -p "$(dirname "$EXT_DIR")"
        rm -rf "$EXT_DIR"
        cp -r "$SRC/extension/$EXT_UUID" "$EXT_DIR"
        NEEDS_LOGIN=1
    fi
fi

update-desktop-database "$PREFIX/share/applications" 2>/dev/null || true
gtk-update-icon-cache -f -t "$PREFIX/share/icons/hicolor" 2>/dev/null || true

echo "Installed. Open “Activity Tracker” from your app menu."
if [ -n "${NEEDS_LOGIN:-}" ]; then
    echo
    echo "The helper extension isn't on extensions.gnome.org yet, so GNOME loads it"
    echo "at your next login. After that, click “Turn On” in the app."
fi
