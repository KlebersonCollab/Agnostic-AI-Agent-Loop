from __future__ import annotations
import asyncio
import os
import json
import threading
from concurrent.futures import Future
from typing import Dict, Any, Set, List

# Thread-safe async runner helper
def run_async(coro):
    def target(f: Future):
        try:
            res = asyncio.run(coro)
            f.set_result(res)
        except Exception as e:
            f.set_exception(e)
            
    fut = Future()
    t = threading.Thread(target=target)
    t.start()
    t.join()
    return fut.result()
