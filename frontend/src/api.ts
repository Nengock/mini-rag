const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

interface ApiConfig {
  apiKey?: string;
}

let config: ApiConfig = {};

export const setApiKey = (apiKey: string) => {
  config.apiKey = apiKey;
};

const getHeaders = (contentType?: string): HeadersInit => {
  const headers: HeadersInit = {
    'Accept': 'application/json',
  };
  
  if (contentType) {
    headers['Content-Type'] = contentType;
  }
  
  if (config.apiKey) {
    headers['X-API-Key'] = config.apiKey;
  }
  
  return headers;
};

// Generic fetch wrapper with error handling
async function fetchWithErrorHandling(url: string, options: RequestInit = {}) {
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        ...getHeaders(options.headers?.['Content-Type']),
        ...options.headers,
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => null);
      throw new Error(
        errorData?.error || 
        errorData?.detail || 
        `HTTP error! status: ${response.status}`
      );
    }

    if (response.status === 204) {
      return null;
    }

    return await response.json();
  } catch (error) {
    if (error instanceof Error) {
      throw new Error(`API request failed: ${error.message}`);
    }
    throw error;
  }
}

export const uploadDocument = async (formData: FormData) => {
  return await fetchWithErrorHandling(`${API_BASE_URL}/documents/upload`, {
    method: 'POST',
    body: formData,
  });
};

export const checkDocumentStatus = async (documentId: string) => {
  return await fetchWithErrorHandling(`${API_BASE_URL}/documents/status/${documentId}`);
};

export const deleteDocument = async (documentId: string): Promise<void> => {
  await fetchWithErrorHandling(`${API_BASE_URL}/documents/${documentId}`, {
    method: 'DELETE',
  });
};

export const queryDocument = async (documentId: string, query: string) => {
  return await fetchWithErrorHandling(`${API_BASE_URL}/queries`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ document_id: documentId, query }),
  });
};

export const askQuestion = async (params: {
  question: string;
  document_id: string;
}) => {
  return await fetchWithErrorHandling(`${API_BASE_URL}/queries/ask`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(params),
  });
};

export const getHealth = async () => {
  return await fetchWithErrorHandling(`${API_BASE_URL}/health`);
};

export const getSystemMetrics = async () => {
  return await fetchWithErrorHandling(`${API_BASE_URL}/system/metrics`);
};

export const getSystemMetricsHistory = async () => {
  return await fetchWithErrorHandling(`${API_BASE_URL}/system/metrics/history`);
};