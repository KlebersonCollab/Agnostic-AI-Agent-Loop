import sys
import time
import threading

def handler(name: str, arguments: dict, result: str) -> str:
    thread_id = threading.get_ident()
    start_times = getattr(sys, "_tool_start_times", {})
    key = (thread_id, name)
    
    if key in start_times:
        duration = time.time() - start_times.pop(key)
        
        if not hasattr(sys, "_tool_perf_stats"):
            sys._tool_perf_stats = {}
            
        stats = sys._tool_perf_stats.setdefault(name, {
            "calls": 0,
            "total_time": 0.0,
            "min_time": duration,
            "max_time": duration
        })
        
        stats["calls"] += 1
        stats["total_time"] += duration
        stats["min_time"] = min(stats["min_time"], duration)
        stats["max_time"] = max(stats["max_time"], duration)
        
    return result
