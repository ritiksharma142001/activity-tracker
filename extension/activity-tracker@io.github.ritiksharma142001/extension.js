// Exposes the currently focused window over D-Bus so the Activity Tracker
// app can read it. Wayland does not let normal apps see other windows.
import Gio from 'gi://Gio';
import Shell from 'gi://Shell';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

const BUS_NAME = 'io.github.ActivityTracker.Shell';
const OBJECT_PATH = '/io/github/ActivityTracker/Shell';
const IFACE_XML = `
<node>
  <interface name="io.github.ActivityTracker.Shell">
    <method name="GetFocusedWindow">
      <arg type="s" direction="out" name="json"/>
    </method>
  </interface>
</node>`;

export default class ActivityTrackerExtension extends Extension {
    enable() {
        this._dbus = Gio.DBusExportedObject.wrapJSObject(IFACE_XML, this);
        this._dbus.export(Gio.DBus.session, OBJECT_PATH);
        this._nameId = Gio.bus_own_name(Gio.BusType.SESSION, BUS_NAME,
            Gio.BusNameOwnerFlags.NONE, null, null, null);
    }

    disable() {
        Gio.bus_unown_name(this._nameId);
        this._dbus.unexport();
        this._dbus = null;
        this._nameId = 0;
    }

    GetFocusedWindow() {
        const win = global.display.focus_window;
        if (!win)
            return '{}';
        const app = Shell.WindowTracker.get_default().get_window_app(win);
        return JSON.stringify({
            app_id: app?.get_id() ?? win.get_wm_class() ?? '',
            app_name: app?.get_name() ?? win.get_wm_class() ?? 'Unknown',
            title: win.get_title() ?? '',
        });
    }
}
