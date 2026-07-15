import sys
import time
import threading

def handler(name: str, arguments: dict):
    if not hasattr(sys, "_tool_start_times"):
        sys._tool_start_times = {}
        
    thread_id = threading.get_ident()
    # Store start time using (thread_id, tool_name) as key
    sys._tool_start_times[(thread_id, name)] = time.time()
    
    return name, arguments
