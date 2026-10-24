#!/usr/bin/env bash
# Removes Activity Tracker. Your recorded data is kept unless you pass --purge.
set -euo pipefail

APP_ID=io.github.ritiksharma142001.ActivityTracker
EXT_UUID=activity-tracker@io.github.ritiksharma142001
PREFIX="$HOME/.local"

pkill -f "activity_tracker --daemon" 2>/dev/null || true
gnome-extensions disable "$EXT_UUID" 2>/dev/null || true
rm -rf "$PREFIX/share/activity-tracker/activity_tracker" \
       "$PREFIX/bin/activity-tracker" \
       "$PREFIX/share/applications/$APP_ID.desktop" \
       "$PREFIX/share/metainfo/$APP_ID.metainfo.xml" \
       "$PREFIX/share/icons/hicolor/scalable/apps/$APP_ID.svg" \
       "$HOME/.config/autostart/$APP_ID.Daemon.desktop" \
       "$HOME/.local/share/gnome-shell/extensions/$EXT_UUID"

if [ "${1:-}" = "--purge" ]; then
    rm -rf "$PREFIX/share/activity-tracker"
    echo "Removed Activity Tracker and its data."
else
    echo "Removed Activity Tracker. Data kept in $PREFIX/share/activity-tracker (use --purge to delete)."
fi
