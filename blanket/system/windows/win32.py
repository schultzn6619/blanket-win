# Copyright 2026 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

"""
The small part of the Win32 API Blanket uses, through ctypes

Every function gets explicit argument and return types: the ctypes default
of int would truncate 64-bit handles and pointers.
"""

import ctypes
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
shell32 = ctypes.WinDLL("shell32", use_last_error=True)

LRESULT = ctypes.c_ssize_t
HCURSOR = wintypes.HANDLE

WNDPROC = ctypes.WINFUNCTYPE(
    LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
)

ERROR_ALREADY_EXISTS = 183

# Messages
WM_NULL = 0x0000
WM_DESTROY = 0x0002
WM_CLOSE = 0x0010
WM_COMMAND = 0x0111
WM_LBUTTONUP = 0x0202
WM_RBUTTONUP = 0x0205
WM_CONTEXTMENU = 0x007B
WM_APP = 0x8000

# Window styles
WS_OVERLAPPED = 0x00000000

# Images
IMAGE_ICON = 1
LR_LOADFROMFILE = 0x00000010
LR_DEFAULTSIZE = 0x00000040
SM_CXSMICON = 49
SM_CYSMICON = 50
IDI_APPLICATION = 32512

# Menus
MF_STRING = 0x00000000
MF_SEPARATOR = 0x00000800
MF_GRAYED = 0x00000001
TPM_RIGHTBUTTON = 0x0002
TPM_RETURNCMD = 0x0100
TPM_NONOTIFY = 0x0080
TPM_BOTTOMALIGN = 0x0020

# Shell notification icon
NIM_ADD = 0x00000000
NIM_MODIFY = 0x00000001
NIM_DELETE = 0x00000002
NIF_MESSAGE = 0x00000001
NIF_ICON = 0x00000002
NIF_TIP = 0x00000004
NIF_SHOWTIP = 0x00000080

# Power
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001

ASFW_ANY = 0xFFFFFFFF


class WNDCLASSEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.UINT),
        ("style", wintypes.UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", HCURSOR),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
        ("hIconSm", wintypes.HICON),
    ]


class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", wintypes.BYTE * 8),
    ]


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("hWnd", wintypes.HWND),
        ("uID", wintypes.UINT),
        ("uFlags", wintypes.UINT),
        ("uCallbackMessage", wintypes.UINT),
        ("hIcon", wintypes.HICON),
        ("szTip", wintypes.WCHAR * 128),
        ("dwState", wintypes.DWORD),
        ("dwStateMask", wintypes.DWORD),
        ("szInfo", wintypes.WCHAR * 256),
        ("uVersion", wintypes.UINT),  # Union with uTimeout
        ("szInfoTitle", wintypes.WCHAR * 64),
        ("dwInfoFlags", wintypes.DWORD),
        ("guidItem", GUID),
        ("hBalloonIcon", wintypes.HICON),
    ]


class SYSTEM_POWER_STATUS(ctypes.Structure):
    _fields_ = [
        ("ACLineStatus", wintypes.BYTE),
        ("BatteryFlag", wintypes.BYTE),
        ("BatteryLifePercent", wintypes.BYTE),
        ("SystemStatusFlag", wintypes.BYTE),
        ("BatteryLifeTime", wintypes.DWORD),
        ("BatteryFullLifeTime", wintypes.DWORD),
    ]


def _declare(func, restype, *argtypes):
    func.restype = restype
    func.argtypes = list(argtypes)
    return func


# user32
RegisterClassExW = _declare(
    user32.RegisterClassExW, wintypes.ATOM, ctypes.POINTER(WNDCLASSEXW)
)
UnregisterClassW = _declare(
    user32.UnregisterClassW, wintypes.BOOL, wintypes.LPCWSTR, wintypes.HINSTANCE
)
CreateWindowExW = _declare(
    user32.CreateWindowExW,
    wintypes.HWND,
    wintypes.DWORD,
    wintypes.LPCWSTR,
    wintypes.LPCWSTR,
    wintypes.DWORD,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.HWND,
    wintypes.HMENU,
    wintypes.HINSTANCE,
    wintypes.LPVOID,
)
DestroyWindow = _declare(user32.DestroyWindow, wintypes.BOOL, wintypes.HWND)
DefWindowProcW = _declare(
    user32.DefWindowProcW,
    LRESULT,
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
)
GetMessageW = _declare(
    user32.GetMessageW,
    wintypes.BOOL,
    ctypes.POINTER(wintypes.MSG),
    wintypes.HWND,
    wintypes.UINT,
    wintypes.UINT,
)
TranslateMessage = _declare(
    user32.TranslateMessage, wintypes.BOOL, ctypes.POINTER(wintypes.MSG)
)
DispatchMessageW = _declare(
    user32.DispatchMessageW, LRESULT, ctypes.POINTER(wintypes.MSG)
)
PostMessageW = _declare(
    user32.PostMessageW,
    wintypes.BOOL,
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
)
PostQuitMessage = _declare(user32.PostQuitMessage, None, ctypes.c_int)
RegisterWindowMessageW = _declare(
    user32.RegisterWindowMessageW, wintypes.UINT, wintypes.LPCWSTR
)
FindWindowW = _declare(
    user32.FindWindowW, wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR
)
GetWindowThreadProcessId = _declare(
    user32.GetWindowThreadProcessId,
    wintypes.DWORD,
    wintypes.HWND,
    ctypes.POINTER(wintypes.DWORD),
)
AllowSetForegroundWindow = _declare(
    user32.AllowSetForegroundWindow, wintypes.BOOL, wintypes.DWORD
)
SetForegroundWindow = _declare(user32.SetForegroundWindow, wintypes.BOOL, wintypes.HWND)
GetCursorPos = _declare(
    user32.GetCursorPos, wintypes.BOOL, ctypes.POINTER(wintypes.POINT)
)
GetSystemMetrics = _declare(user32.GetSystemMetrics, ctypes.c_int, ctypes.c_int)
LoadImageW = _declare(
    user32.LoadImageW,
    wintypes.HANDLE,
    wintypes.HINSTANCE,
    wintypes.LPCWSTR,
    wintypes.UINT,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.UINT,
)
LoadIconW = _declare(user32.LoadIconW, wintypes.HICON, wintypes.HINSTANCE, wintypes.LPVOID)
DestroyIcon = _declare(user32.DestroyIcon, wintypes.BOOL, wintypes.HICON)
CreatePopupMenu = _declare(user32.CreatePopupMenu, wintypes.HMENU)
AppendMenuW = _declare(
    user32.AppendMenuW,
    wintypes.BOOL,
    wintypes.HMENU,
    wintypes.UINT,
    ctypes.c_size_t,
    wintypes.LPCWSTR,
)
SetMenuDefaultItem = _declare(
    user32.SetMenuDefaultItem, wintypes.BOOL, wintypes.HMENU, wintypes.UINT, wintypes.UINT
)
TrackPopupMenu = _declare(
    user32.TrackPopupMenu,
    wintypes.BOOL,
    wintypes.HMENU,
    wintypes.UINT,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.HWND,
    wintypes.LPVOID,
)
DestroyMenu = _declare(user32.DestroyMenu, wintypes.BOOL, wintypes.HMENU)

# kernel32
GetModuleHandleW = _declare(kernel32.GetModuleHandleW, wintypes.HMODULE, wintypes.LPCWSTR)
CreateMutexW = _declare(
    kernel32.CreateMutexW,
    wintypes.HANDLE,
    wintypes.LPVOID,
    wintypes.BOOL,
    wintypes.LPCWSTR,
)
CloseHandle = _declare(kernel32.CloseHandle, wintypes.BOOL, wintypes.HANDLE)
SetThreadExecutionState = _declare(
    kernel32.SetThreadExecutionState, wintypes.DWORD, wintypes.DWORD
)
GetSystemPowerStatus = _declare(
    kernel32.GetSystemPowerStatus,
    wintypes.BOOL,
    ctypes.POINTER(SYSTEM_POWER_STATUS),
)
GetUserDefaultUILanguage = _declare(kernel32.GetUserDefaultUILanguage, wintypes.WORD)
LCIDToLocaleName = _declare(
    kernel32.LCIDToLocaleName,
    ctypes.c_int,
    wintypes.DWORD,
    wintypes.LPWSTR,
    ctypes.c_int,
    wintypes.DWORD,
)

# shell32
Shell_NotifyIconW = _declare(
    shell32.Shell_NotifyIconW,
    wintypes.BOOL,
    wintypes.DWORD,
    ctypes.POINTER(NOTIFYICONDATAW),
)
SetCurrentProcessExplicitAppUserModelID = _declare(
    shell32.SetCurrentProcessExplicitAppUserModelID, ctypes.c_long, wintypes.LPCWSTR
)


"""
Helpers
"""


def user_ui_language() -> str | None:
    """The Windows display language as a gettext locale name, like pt_BR"""
    buffer = ctypes.create_unicode_buffer(85)  # LOCALE_NAME_MAX_LENGTH
    if not LCIDToLocaleName(GetUserDefaultUILanguage(), buffer, len(buffer), 0):
        return None

    # Windows uses BCP 47 tags (pt-BR, sr-Latn-RS), gettext wants pt_BR
    parts = buffer.value.split("-")
    if not parts or not parts[0]:
        return None
    if len(parts) > 1 and len(parts[-1]) == 2:
        return f"{parts[0]}_{parts[-1].upper()}"
    return parts[0]


def set_app_user_model_id(app_id: str):
    """Group the taskbar button with the Start menu shortcut"""
    SetCurrentProcessExplicitAppUserModelID(app_id)


def keep_system_awake(awake: bool) -> bool:
    """Prevent the system from sleeping while it is true"""
    flags = ES_CONTINUOUS
    if awake:
        flags |= ES_SYSTEM_REQUIRED
    return SetThreadExecutionState(flags) != 0


def battery_saver_enabled() -> bool:
    status = SYSTEM_POWER_STATUS()
    if not GetSystemPowerStatus(ctypes.byref(status)):
        return False
    return status.SystemStatusFlag == 1
