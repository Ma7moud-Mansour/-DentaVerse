"""Own only fixed DentaVerse workers; subprocesses never accept shell text."""
import asyncio
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

MODULES = {"vision": "backend.workers.vision", "bluetooth": "backend.workers.bluetooth"}


class WorkerSupervisor:
    def __init__(self, root: Path, port: int, on_exit):
        self.root = root
        self.port = port
        self.on_exit = on_exit
        self.children = {}
        self.tasks = set()
        self.stopping = set()

    def owns(self, source):
        process = self.children.get(source)
        return process is not None and process.poll() is None

    async def start(self, source, camera=0):
        if source not in MODULES:
            raise ValueError("Unknown service")
        if self.owns(source):
            raise ValueError("Service is already starting or running")
        if source == "vision":
            if importlib.util.find_spec("mediapipe") is None or importlib.util.find_spec("cv2") is None:
                raise ValueError("Camera dependencies are missing. Run setup with -WithVision first.")
            if not (self.root / "models" / "pose_landmarker_lite.task").is_file():
                raise ValueError("Download the Pose model before starting the camera.")
            if not (self.root / "models" / "hand_landmarker.task").is_file():
                raise ValueError("Hand model missing. Run python tools/download_hand_model.py, then retry.")
        args = [sys.executable, "-m", MODULES[source], "--port", str(self.port)]
        if source == "vision":
            args += ["--camera", str(camera), "--no-preview"]
        log_dir = self.root / ".review" / "runtime"
        log_dir.mkdir(parents=True, exist_ok=True)
        with (log_dir / f"{source}.log").open("ab") as output:
            process = subprocess.Popen(args, cwd=self.root, stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        self.children[source] = process
        task = asyncio.create_task(self._watch(source, process))
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)

    async def _watch(self, source, process):
        code = await asyncio.to_thread(process.wait)
        expected = process in self.stopping
        self.stopping.discard(process)
        if self.children.get(source) is process:
            self.children.pop(source, None)
            await self.on_exit(source, code, expected)

    async def stop(self, source):
        process = self.children.get(source)
        if process is None or process.poll() is not None:
            return
        self.stopping.add(process)
        try:
            await asyncio.wait_for(asyncio.to_thread(process.wait), 2)
        except asyncio.TimeoutError:
            # Kill only the process tree we launched. A Windows venv redirector
            # can own the real Python child; terminating only its parent leaks it.
            if os.name == "nt":
                await asyncio.to_thread(subprocess.run, ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                process.terminate()
            try:
                await asyncio.wait_for(asyncio.to_thread(process.wait), 3)
            except asyncio.TimeoutError:
                process.kill()
                await asyncio.to_thread(process.wait)

    async def close(self):
        await asyncio.gather(*(self.stop(source) for source in list(self.children)), return_exceptions=True)
        if self.tasks:
            await asyncio.gather(*list(self.tasks), return_exceptions=True)
