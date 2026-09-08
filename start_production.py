from __future__ import annotations

import os
import signal
import subprocess
import sys
import time


def stop_process(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()


if __name__ == "__main__":
    env = os.environ.copy()
    env.setdefault("HOST", "0.0.0.0")
    app = subprocess.Popen([sys.executable, "app.py"], env=env)
    time.sleep(1)
    if app.poll() is not None:
        raise SystemExit("Web application failed to start")

    bot = subprocess.Popen([sys.executable, "bot.py"], env=env)

    def shutdown(_signal: int, _frame: object) -> None:
        stop_process(bot)
        stop_process(app)
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    while True:
        if app.poll() is not None:
            stop_process(bot)
            raise SystemExit("Web application stopped unexpectedly")
        if bot.poll() is not None:
            stop_process(app)
            raise SystemExit("Telegram bot stopped unexpectedly")
        time.sleep(2)
