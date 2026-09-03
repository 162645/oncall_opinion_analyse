"""Small Redis sidecar for hosts where the OS Redis package is unavailable."""
from pathlib import Path
import time
import redislite

Path("/home/wsl/OnCall/.redis").mkdir(parents=True, exist_ok=True)
redis = redislite.Redis("/home/wsl/OnCall/.redis/redis.db",
                        serverconfig={"port": 6379, "unixsocket": ""})
redis.ping()
while True:
    time.sleep(3600)
