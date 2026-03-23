"""
Numbers10 PCMonitor — System Tray Monitor (native win32gui)
Shows connection status icon in the Windows system tray.
"""
import ctypes
import json
import os
import struct
import subprocess
import sys
import tempfile
import threading
import time

import win32api
import win32con
import win32gui
import win32service
import win32serviceutil

SERVICE_NAME = "PCMonitorProbe"
POLL_INTERVAL = 10
WM_TRAY = win32con.WM_USER + 1


def get_base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def create_ico_file(r, g, b):
    """Create a minimal 16x16 .ico file with a colored circle, return path."""
    width, height = 16, 16
    pixels = []
    cx, cy = 7.5, 7.5
    radius = 6.5
    for y in range(height):
        for x in range(width):
            dx, dy = x - cx, y - cy
            if dx * dx + dy * dy <= radius * radius:
                pixels.append(struct.pack("BBBB", b, g, r, 255))
            else:
                pixels.append(struct.pack("BBBB", 0, 0, 0, 0))

    pixel_data = b"".join(pixels)
    # ICO file: header + directory entry + BMP info header + pixel data
    bmp_header = struct.pack(
        "<IiiHHIIiiII",
        40,           # biSize
        width,        # biWidth
        height * 2,   # biHeight (doubled for ICO)
        1,            # biPlanes
        32,           # biBitCount
        0,            # biCompression
        len(pixel_data),
        0, 0, 0, 0,
    )
    # AND mask (all zeros = fully opaque with alpha channel)
    and_mask = b"\x00" * (((width + 31) // 32) * 4 * height)
    image_data = bmp_header + pixel_data + and_mask
    ico_header = struct.pack("<HHH", 0, 1, 1)  # reserved, type=ico, count=1
    ico_entry = struct.pack(
        "<BBBBHHII",
        width if width < 256 else 0,
        height if height < 256 else 0,
        0,    # color palette
        0,    # reserved
        1,    # planes
        32,   # bits per pixel
        len(image_data),
        6 + 16,  # offset to image data (header=6, entry=16)
    )
    ico_data = ico_header + ico_entry + image_data

    fd, path = tempfile.mkstemp(suffix=".ico")
    os.write(fd, ico_data)
    os.close(fd)
    return path


def find_status_file():
    """Search for probe_status.json in likely locations."""
    candidates = [
        os.path.join(get_base_dir(), "probe_status.json"),
        os.path.join(os.path.expandvars(r"%ProgramData%"), "PCMonitorProbe", "probe_status.json"),
    ]
    # Also check the service executable path from registry
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SYSTEM\CurrentControlSet\Services\PCMonitorProbe",
        )
        image_path = winreg.QueryValueEx(key, "ImagePath")[0]
        winreg.CloseKey(key)
        # Strip quotes
        image_path = image_path.strip('"')
        svc_dir = os.path.dirname(image_path)
        candidates.insert(0, os.path.join(svc_dir, "probe_status.json"))
    except Exception:
        pass
    for path in candidates:
        if os.path.exists(path):
            return path
    return candidates[0]  # default to base_dir


def read_status_file():
    path = find_status_file()
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, PermissionError):
        return None


def query_service_running():
    try:
        status = win32serviceutil.QueryServiceStatus(SERVICE_NAME)
        return status[1] == 4  # SERVICE_RUNNING
    except Exception:
        return False


class TrayApp:
    def __init__(self):
        self.connected = False
        self.service_running = False
        self.hwnd = None
        self.icon_connected = None
        self.icon_disconnected = None
        self.current_icon = None
        self._ico_files = []

    def _find_log_file(self):
        """Search for probe_errors.log in likely locations."""
        candidates = [get_base_dir()]
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\CurrentControlSet\Services\PCMonitorProbe",
            )
            image_path = winreg.QueryValueEx(key, "ImagePath")[0].strip('"')
            candidates.insert(0, os.path.dirname(image_path))
            winreg.CloseKey(key)
        except Exception:
            pass
        for d in candidates:
            path = os.path.join(d, "probe_errors.log")
            if os.path.exists(path):
                return path
        return None

    def _create_icons(self):
        # Teal for connected, red for disconnected
        connected_path = create_ico_file(45, 212, 191)
        disconnected_path = create_ico_file(239, 68, 68)
        self._ico_files = [connected_path, disconnected_path]
        self.icon_connected = win32gui.LoadImage(
            0, connected_path, win32con.IMAGE_ICON, 0, 0,
            win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE,
        )
        self.icon_disconnected = win32gui.LoadImage(
            0, disconnected_path, win32con.IMAGE_ICON, 0, 0,
            win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE,
        )

    def _cleanup_icons(self):
        for path in self._ico_files:
            try:
                os.unlink(path)
            except Exception:
                pass

    def _update_tray(self, icon, tooltip):
        if self.hwnd:
            nid = (
                self.hwnd, 0,
                win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP,
                WM_TRAY, icon, tooltip[:127],
            )
            try:
                win32gui.Shell_NotifyIcon(win32gui.NIM_MODIFY, nid)
            except Exception:
                pass
            self.current_icon = icon

    def _show_menu(self):
        menu = win32gui.CreatePopupMenu()

        # Status line (grayed out)
        if self.connected:
            status_text = "Status: Connected"
        elif self.service_running:
            status_text = "Status: No Connection"
        else:
            status_text = "Status: Service Stopped"
        win32gui.AppendMenu(menu, win32con.MF_STRING | win32con.MF_GRAYED, 0, status_text)

        svc_text = f"Service: {'Running' if self.service_running else 'Stopped'}"
        win32gui.AppendMenu(menu, win32con.MF_STRING | win32con.MF_GRAYED, 0, svc_text)

        win32gui.AppendMenu(menu, win32con.MF_SEPARATOR, 0, "")
        win32gui.AppendMenu(menu, win32con.MF_STRING, 1001, "Open Logs")

        if self.service_running:
            win32gui.AppendMenu(menu, win32con.MF_STRING, 1003, "Stop Service")
        else:
            win32gui.AppendMenu(menu, win32con.MF_STRING, 1002, "Start Service")

        win32gui.AppendMenu(menu, win32con.MF_SEPARATOR, 0, "")
        win32gui.AppendMenu(menu, win32con.MF_STRING, 1099, "Exit")

        pos = win32gui.GetCursorPos()
        win32gui.SetForegroundWindow(self.hwnd)
        win32gui.TrackPopupMenu(
            menu, win32con.TPM_LEFTALIGN, pos[0], pos[1], 0, self.hwnd, None,
        )
        win32gui.PostMessage(self.hwnd, win32con.WM_NULL, 0, 0)
        win32gui.DestroyMenu(menu)

    def _on_command(self, cmd_id):
        if cmd_id == 1001:
            log_path = self._find_log_file()
            if log_path and os.path.exists(log_path):
                subprocess.Popen(["notepad.exe", log_path])
            else:
                win32api.MessageBox(0, "No log file found yet.\nLogs appear after the service runs.", "PCMonitor Tray", 0)
        elif cmd_id == 1002:
            try:
                win32serviceutil.StartService(SERVICE_NAME)
            except Exception as e:
                win32api.MessageBox(0, f"Could not start: {e}\nRun as Admin.", "PCMonitor Tray", 0)
        elif cmd_id == 1003:
            try:
                win32serviceutil.StopService(SERVICE_NAME)
            except Exception as e:
                win32api.MessageBox(0, f"Could not stop: {e}\nRun as Admin.", "PCMonitor Tray", 0)
        elif cmd_id == 1099:
            self._remove_tray()
            win32gui.PostQuitMessage(0)

    def _wnd_proc(self, hwnd, msg, wparam, lparam):
        if msg == WM_TRAY:
            if lparam == win32con.WM_RBUTTONUP or lparam == win32con.WM_LBUTTONUP:
                self._show_menu()
        elif msg == win32con.WM_COMMAND:
            self._on_command(win32api.LOWORD(wparam))
        elif msg == win32con.WM_DESTROY:
            self._remove_tray()
            win32gui.PostQuitMessage(0)
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    def _add_tray(self):
        icon = self.icon_disconnected
        nid = (
            self.hwnd, 0,
            win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP,
            WM_TRAY, icon, "Numbers10 PCMonitor - Starting...",
        )
        win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, nid)
        self.current_icon = icon

    def _remove_tray(self):
        try:
            nid = (self.hwnd, 0)
            win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, nid)
        except Exception:
            pass

    def _poll_loop(self):
        while True:
            self.service_running = query_service_running()

            if self.service_running:
                status = read_status_file()
                if status:
                    self.connected = status.get("connected", False)
                else:
                    # Service running but no status file yet — assume connecting
                    self.connected = False
            else:
                self.connected = False

            # Build tooltip
            if self.connected:
                tip = "Numbers10 PCMonitor - Connected"
            elif self.service_running:
                tip = "Numbers10 PCMonitor - Service Running"
            else:
                tip = "Numbers10 PCMonitor - Service Stopped"

            # Always update icon and tooltip
            new_icon = self.icon_connected if self.connected else self.icon_disconnected
            self._update_tray(new_icon, tip)

            time.sleep(POLL_INTERVAL)

    def run(self):
        self._create_icons()

        # Register window class
        wc = win32gui.WNDCLASS()
        wc.hInstance = win32api.GetModuleHandle(None)
        wc.lpszClassName = "PCMonitorTrayClass"
        wc.lpfnWndProc = self._wnd_proc
        class_atom = win32gui.RegisterClass(wc)

        # Create hidden window
        self.hwnd = win32gui.CreateWindow(
            class_atom, "PCMonitorTray", 0,
            0, 0, 0, 0,
            0, 0, wc.hInstance, None,
        )

        self._add_tray()

        # Start polling in background
        poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        poll_thread.start()

        # Win32 message loop
        win32gui.PumpMessages()

        self._cleanup_icons()


if __name__ == "__main__":
    app = TrayApp()
    app.run()
