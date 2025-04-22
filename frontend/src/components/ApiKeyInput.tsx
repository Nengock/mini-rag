import React, { useState, useEffect } from 'react';
import { setApiKey } from '../api';

const ApiKeyInput: React.FC = () => {
  const [key, setKey] = useState<string>('');
  const [isVisible, setIsVisible] = useState<boolean>(false);

  // Load saved API key from localStorage
  useEffect(() => {
    const savedKey = localStorage.getItem('api_key');
    if (savedKey) {
      setKey(savedKey);
      setApiKey(savedKey);
    }
  }, []);

  const handleKeyChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newKey = e.target.value;
    setKey(newKey);
    setApiKey(newKey);
    localStorage.setItem('api_key', newKey);
  };

  return (
    <div className="flex items-center gap-2 p-2 bg-gray-100 rounded">
      <label htmlFor="api-key" className="text-sm font-medium text-gray-700">
        API Key:
      </label>
      <div className="relative flex-1">
        <input
          id="api-key"
          type={isVisible ? 'text' : 'password'}
          value={key}
          onChange={handleKeyChange}
          placeholder="Enter API key"
          className="w-full px-3 py-1 text-sm border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          type="button"
          onClick={() => setIsVisible(!isVisible)}
          className="absolute right-2 top-1/2 transform -translate-y-1/2 text-gray-500 hover:text-gray-700"
        >
          {isVisible ? '🔒' : '👁️'}
        </button>
      </div>
    </div>
  );
};

export default ApiKeyInput;