import os, threading
import xarray as xr
from typing import Dict

class DatasetManager:
    def __init__(self):
        # Cache store dataset and timestamp
        self._cache: Dict[str, xr.Dataset] = {}
        self._timestamp: Dict[str, float] = {}
        self._lock = threading.Lock()

    def get(self, path: str) -> xr.Dataset:
        # Get dataset from cache, if not in cache or if the file has been modified, open the dataset
        mtime = os.path.getmtime(path)
        with self._lock:
            if path not in self._cache:
                print(f"🔄 Opening: {path}")
                time_dim = 'time' if "output\HYD" in path else 'nTimesDlwq'
                self._cache[path] = xr.open_dataset(path, chunks={time_dim:1})
                self._timestamp[path] = mtime
            elif self._timestamp[path] != mtime:
                print(f"♻️ Reload dataset: {path}")
                self._cache[path].close()
                del self._cache[path]
                time_dim = 'time' if "output\HYD" in path else 'nTimesDlwq'
                self._cache[path] = xr.open_dataset(path, chunks={time_dim:1})
                self._timestamp[path] = mtime
            else: print(f"✅ Using cached dataset: {path}")
            return self._cache[path]

    def close(self):
        # Close all datasets, usually at shutdown
        for path, dataset in self._cache.items():
            try:
                dataset.close()
                del dataset
                print(f"🛑 Closed dataset: {path}")
            except Exception as e: print(f"❌ Error closing dataset: {path} - {str(e)}")
        self._cache.clear()
        self._timestamp.clear()
