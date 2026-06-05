import axios from 'axios';

const API_BASE_URL = 'http://127.0.0.1:8000';

export const api = axios.create({
  baseURL: API_BASE_URL,
});

// Parse response data directly
api.interceptors.response.use(
  (response) => response.data,
  (error) => Promise.reject(error)
);

// ==================== Auth ====================

export const login = (email: string, password: string) => {
  const formData = new FormData();
  formData.append('username', email);
  formData.append('password', password);
  return api.post('/api/v1/auth/login/access-token', formData);
};

export const register = (email: string, password: string) => {
  return api.post('/api/v1/auth/register', { email, password });
};

export const getMe = (token: string) => {
  return api.get('/api/v1/auth/me', {
    headers: { Authorization: `Bearer ${token}` }
  });
};

// ==================== Sessions (Legacy CDA) ====================

export const getSessions = (userId: number) => 
  api.get('/api/v1/sessions/', { params: { user_id: userId } });

export const createSession = (userId: number, title: string) => 
  api.post('/api/v1/sessions/', { title }, { params: { user_id: userId } });

export const updateSession = (sessionId: number, title: string) => {
  const formData = new FormData();
  formData.append('title', title);
  return api.put(`/api/v1/sessions/${sessionId}`, formData);
};

export const deleteSession = (sessionId: number) => 
  api.delete(`/api/v1/sessions/${sessionId}`);

// ==================== Legacy Data Chat ====================

export const uploadFile = (sessionId: number, file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  return api.post(`/api/v1/upload/${sessionId}/upload`, formData);
};

export const sendMessage = (sessionId: number, query: string) => {
  return api.post(`/api/v1/chat/${sessionId}/send`, { query });
};

export const getHistory = (sessionId: number) => 
  api.get(`/api/v1/chat/${sessionId}/history`);

export const downloadPDF = (sessionId: number) => {
  return api.get(`/api/v1/download/${sessionId}`, {
    params: { t: new Date().getTime() },
    responseType: 'blob'
  });
};

export const downloadDataset = (sessionId: number) => {
  return api.get(`/api/v1/download/session/${sessionId}/dataset`, {
    params: { t: new Date().getTime() },
    responseType: 'blob'
  });
};

// ==================== DocMind AI — PDF Operations ====================

export const uploadPDF = (
  sessionId: number,
  file: File,
  onProgress?: (percent: number) => void
) => {
  const formData = new FormData();
  formData.append('file', file);
  return api.post(`/api/v1/pdf/upload?session_id=${sessionId}`, formData, {
    onUploadProgress: (progressEvent) => {
      if (onProgress && progressEvent.total) {
        const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        onProgress(percent);
      }
    },
  });
};

export const getSessionDocuments = (sessionId: number) =>
  api.get(`/api/v1/pdf/session/${sessionId}/documents`);

export const getDocument = (docId: number) =>
  api.get(`/api/v1/pdf/${docId}`);

export const getDocumentVersions = (docId: number) =>
  api.get(`/api/v1/pdf/${docId}/versions`);

export const getVersionFileUrl = (docId: number, versionId: number) =>
  `${API_BASE_URL}/api/v1/pdf/${docId}/versions/${versionId}/file`;

export const getPageText = (docId: number, pageNum: number) =>
  api.get(`/api/v1/pdf/${docId}/pages/${pageNum}`);

export const deleteDocument = (docId: number) =>
  api.delete(`/api/v1/pdf/${docId}`);

// ==================== DocMind AI — PDF Chat ====================

export const askQuestion = (docId: number, query: string) =>
  api.post(`/api/v1/pdf-chat/${docId}/ask`, { query });

export const summarizeDocument = (
  docId: number,
  mode: string = "executive",
  pages?: number[]
) =>
  api.post(`/api/v1/pdf-chat/${docId}/summarize`, { mode, pages });

export const editDocument = (docId: number, command: string) =>
  api.post(`/api/v1/pdf-chat/${docId}/edit`, { command });

export const confirmEdit = (docId: number, previewId: number) =>
  api.post(`/api/v1/pdf-chat/${docId}/edit/confirm`, { preview_id: previewId });

export const getAutocompleteSuggestions = (docId: number, partialQuery: string) =>
  api.get(`/api/v1/pdf-chat/${docId}/suggestions`, { params: { q: partialQuery } });

export const getPdfChatHistory = (docId: number) =>
  api.get(`/api/v1/pdf-chat/${docId}/history`);

export const getDocumentProfile = (docId: number) =>
  api.get(`/api/v1/pdf-chat/${docId}/profile`);
