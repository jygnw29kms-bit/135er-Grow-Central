import ctypes,time
from ctypes import wintypes
u=ctypes.windll.user32
pid=22532
wins=[]
@ctypes.WINFUNCTYPE(ctypes.c_bool,wintypes.HWND,wintypes.LPARAM)
def cb(hwnd,l):
    p=wintypes.DWORD(); u.GetWindowThreadProcessId(hwnd,ctypes.byref(p))
    if p.value==pid and u.IsWindowVisible(hwnd):
        n=u.GetWindowTextLengthW(hwnd); b=ctypes.create_unicode_buffer(n+1); u.GetWindowTextW(hwnd,b,n+1)
        if 'OpenSCAD' in b.value: wins.append(hwnd)
    return True
u.EnumWindows(cb,0)
if wins:
    h=wins[0]; u.ShowWindow(h,9); u.SetForegroundWindow(h); time.sleep(.3)
    r=wintypes.RECT(); u.GetWindowRect(h,ctypes.byref(r))
    x=int(r.left+(r.right-r.left)*0.72); y=int(r.top+(r.bottom-r.top)*0.48)
    u.SetCursorPos(x,y)
    for _ in range(9):
        u.mouse_event(0x0800,0,0,120,0); time.sleep(.08)
print(wins)