from fastapi import APIRouter, BackgroundTasks
from typing import Dict, List
import psutil
import torch
import time
import asyncio
from collections import deque
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Keep last 60 minutes of metrics, one sample per minute
MAX_HISTORY = 60
metrics_history = deque(maxlen=MAX_HISTORY)

class SystemMetrics:
    def __init__(self):
        self.timestamp = time.time()
        self.cpu_percent = psutil.cpu_percent(interval=None)
        self.memory = psutil.virtual_memory()._asdict()
        self.memory_percent = psutil.Process().memory_percent()
        
        if torch.cuda.is_available():
            self.gpu_memory_allocated = torch.cuda.memory_allocated() / (1024 * 1024)
            self.gpu_memory_reserved = torch.cuda.memory_reserved() / (1024 * 1024)
            self.gpu_utilization = [torch.cuda.utilization(i) for i in range(torch.cuda.device_count())]
        else:
            self.gpu_memory_allocated = 0
            self.gpu_memory_reserved = 0
            self.gpu_utilization = []

    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "cpu_percent": self.cpu_percent,
            "memory_total": self.memory["total"] / (1024 * 1024),  # MB
            "memory_available": self.memory["available"] / (1024 * 1024),  # MB
            "memory_percent": self.memory_percent,
            "gpu_memory_allocated": self.gpu_memory_allocated,
            "gpu_memory_reserved": self.gpu_memory_reserved,
            "gpu_utilization": self.gpu_utilization
        }

async def collect_metrics():
    """Background task to collect system metrics"""
    while True:
        try:
            metrics = SystemMetrics()
            metrics_history.append(metrics.to_dict())
            await asyncio.sleep(60)  # Collect every minute
        except Exception as e:
            logger.error(f"Error collecting metrics: {str(e)}")
            await asyncio.sleep(60)  # Wait before retry

@router.get("/metrics")
async def get_metrics(background_tasks: BackgroundTasks) -> Dict:
    """Get current system metrics and start collection if not running"""
    # Start metrics collection if this is the first request
    if not metrics_history:
        background_tasks.add_task(collect_metrics)
    
    current_metrics = SystemMetrics()
    
    return {
        "current": current_metrics.to_dict(),
        "history": list(metrics_history)
    }

@router.get("/metrics/history")
async def get_metrics_history() -> List[Dict]:
    """Get historical system metrics"""
    return list(metrics_history)

@router.post("/metrics/clear")
async def clear_metrics_history():
    """Clear metrics history"""
    metrics_history.clear()
    return {"message": "Metrics history cleared"}