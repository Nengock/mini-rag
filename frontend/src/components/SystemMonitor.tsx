import React, { useEffect, useState } from 'react';
import { getHealth } from '../api';
import ApiKeyInput from './ApiKeyInput';

interface SystemHealth {
  status: string;
  config: {
    model_device: string;
    torch_threads: number;
    max_upload_size: number;
  };
  memory: {
    rss: number;
    vms: number;
    percent: number;
    cpu_percent: number;
    gpu_memory_allocated?: number;
    gpu_memory_reserved?: number;
    gpu_max_memory?: number;
  };
  system: {
    cpu_count: number;
    cpu_freq: { current: number; min: number; max: number } | null;
    memory_total: number;
    memory_available: number;
    gpu_available: boolean;
    gpu_count: number;
    gpu_name: string | null;
  };
}

const SystemMonitor: React.FC = () => {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [requiresAuth, setRequiresAuth] = useState(false);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const data = await getHealth();
        setHealth(data);
        setError(null);
      } catch (err) {
        const error = err as Error;
        setError(error.message);
        if (error.message.includes('401')) {
          setRequiresAuth(true);
        }
      }
    };

    fetchHealth();
    const interval = setInterval(fetchHealth, 30000); // Update every 30 seconds
    return () => clearInterval(interval);
  }, []);

  if (error) {
    return (
      <div className="p-4 bg-white rounded-lg shadow">
        <h2 className="text-xl font-bold mb-4">System Status</h2>
        <div className="text-red-500 mb-4">{error}</div>
        {requiresAuth && <ApiKeyInput />}
      </div>
    );
  }

  if (!health) {
    return (
      <div className="p-4 bg-white rounded-lg shadow">
        <h2 className="text-xl font-bold mb-4">System Status</h2>
        <div>Loading system information...</div>
      </div>
    );
  }

  return (
    <div className="p-4 bg-white rounded-lg shadow">
      <h2 className="text-xl font-bold mb-4">System Status</h2>
      
      {requiresAuth && <ApiKeyInput />}
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <h3 className="font-semibold mb-2">Configuration</h3>
          <ul className="space-y-1">
            <li>Device: {health.config.model_device}</li>
            <li>Threads: {health.config.torch_threads}</li>
            <li>Max Upload: {(health.config.max_upload_size / 1024 / 1024).toFixed(1)} MB</li>
          </ul>
        </div>
        
        <div>
          <h3 className="font-semibold mb-2">Memory Usage</h3>
          <ul className="space-y-1">
            <li>RAM: {health.memory.rss.toFixed(1)} MB</li>
            <li>CPU: {health.memory.cpu_percent.toFixed(1)}%</li>
            {health.system.gpu_available && (
              <>
                <li>GPU Memory: {health.memory.gpu_memory_allocated?.toFixed(1)} MB</li>
                <li>GPU Max: {health.memory.gpu_max_memory?.toFixed(1)} MB</li>
              </>
            )}
          </ul>
        </div>
        
        <div>
          <h3 className="font-semibold mb-2">System Resources</h3>
          <ul className="space-y-1">
            <li>CPU Cores: {health.system.cpu_count}</li>
            <li>Total RAM: {(health.system.memory_total).toFixed(1)} MB</li>
            <li>Available RAM: {(health.system.memory_available).toFixed(1)} MB</li>
          </ul>
        </div>
        
        {health.system.gpu_available && (
          <div>
            <h3 className="font-semibold mb-2">GPU Information</h3>
            <ul className="space-y-1">
              <li>GPU Count: {health.system.gpu_count}</li>
              <li>GPU Name: {health.system.gpu_name}</li>
            </ul>
          </div>
        )}
      </div>
    </div>
  );
};

export default SystemMonitor;