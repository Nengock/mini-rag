import time
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, Optional
import psutil
import torch

@dataclass
class RequestMetrics:
    path: str
    method: str
    start_time: float
    end_time: Optional[float] = None
    status_code: Optional[int] = None
    error: Optional[str] = None

class SystemMonitor:
    def __init__(self, max_history: int = 1000):
        self.request_history: Deque[RequestMetrics] = deque(maxlen=max_history)
        self.start_time = time.time()
    
    def start_request(self, path: str, method: str) -> RequestMetrics:
        metrics = RequestMetrics(
            path=path,
            method=method,
            start_time=time.time()
        )
        self.request_history.append(metrics)
        return metrics
    
    def end_request(self, metrics: RequestMetrics, status_code: int, error: Optional[str] = None):
        metrics.end_time = time.time()
        metrics.status_code = status_code
        metrics.error = error
    
    def get_metrics(self) -> Dict:
        now = time.time()
        recent_requests = [r for r in self.request_history if r.end_time and now - r.end_time < 60]
        
        # Calculate request statistics
        total_requests = len(recent_requests)
        successful_requests = len([r for r in recent_requests if r.status_code and r.status_code < 400])
        failed_requests = len([r for r in recent_requests if r.status_code and r.status_code >= 400])
        
        # Calculate average response time
        response_times = [
            r.end_time - r.start_time 
            for r in recent_requests 
            if r.end_time is not None
        ]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        # System metrics
        process = psutil.Process()
        memory_info = process.memory_info()
        
        metrics = {
            "uptime_seconds": now - self.start_time,
            "requests": {
                "total_last_minute": total_requests,
                "successful_last_minute": successful_requests,
                "failed_last_minute": failed_requests,
                "average_response_time": avg_response_time
            },
            "system": {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "process_memory_mb": memory_info.rss / (1024 * 1024),
            }
        }
        
        # Add GPU metrics if available
        if torch.cuda.is_available():
            metrics["system"].update({
                "gpu_memory_allocated_mb": torch.cuda.memory_allocated() / (1024 * 1024),
                "gpu_memory_cached_mb": torch.cuda.memory_reserved() / (1024 * 1024),
                "gpu_utilization": torch.cuda.utilization()
            })
        
        return metrics

system_monitor = SystemMonitor()