"""Isolated test coordinator with CPU time reserved for its sensor deadline."""
import ctypes
import sys
from pathlib import Path

if sys.platform == "win32":
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.SetPriorityClass.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.SetPriorityClass.restype = wintypes.BOOL
    # ABOVE_NORMAL_PRIORITY_CLASS; never HIGH/REALTIME. Only this test process.
    if not kernel.SetPriorityClass(kernel.GetCurrentProcess(), 0x00008000):
        raise ctypes.WinError(ctypes.get_last_error())

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.app:app", host="127.0.0.1", port=8001)
