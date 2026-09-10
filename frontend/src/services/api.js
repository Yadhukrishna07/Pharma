import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor to attach token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

export const authAPI = {
  login: (username, password) => api.post('/auth/login', { username, password }),
  register: (data) => api.post('/auth/register', data),
  getMe: () => api.get('/auth/me'),
  switchRole: (role) => api.post('/auth/switch-role', { role }),
  getNotificationsCount: () => api.get('/auth/notifications/count'),
  getNotifications: () => api.get('/auth/notifications'),
  markNotificationRead: (id) => api.post(`/auth/notifications/${id}/read`),
};

export const batchAPI = {
  getBatches: () => api.get('/batches/'),
  getBatch: (id) => api.get(`/batches/${id}`),
  scanBatch: (batch_number, location, actor_role) =>
    api.post('/batches/scan', { batch_number, location, actor_role }),
  getBatchTimeline: (id) => api.get(`/batches/${id}/timeline`),
  getModeratorEvents: (id) => api.get(`/batches/${id}/moderator-events`),
};

export const returnAPI = {
  createReturnRequest: (data) => api.post('/returns/', data),
  getReturns: () => api.get('/returns/'),
  confirmPickup: (returnId) => api.post(`/returns/${returnId}/pickup`),
  receiveReturn: (returnId, received_quantity) =>
    api.post(`/returns/${returnId}/receive`, { batch_id: returnId, received_quantity }),
};

export const disputeAPI = {
  getDisputes: () => api.get('/disputes/'),
  getDispute: (id) => api.get(`/disputes/${id}`),
  resolveDispute: (id, resolution_notes) =>
    api.post(`/disputes/${id}/resolve`, { resolution_notes }),
};

export const destructionAPI = {
  handoff: (data) => api.post('/destruction/handoff', data),
  scheduleDestruction: (batch_id, facility_id) =>
    api.post('/destruction/schedule', { batch_id, facility_id }),
  recordDestruction: (batch_id, quantity_destroyed) =>
    api.post('/destruction/record', { batch_id, quantity_destroyed }),
};

export const certificateAPI = {
  createCertificate: (certificate_number, batch_id, quantity) =>
    api.post('/certificates/', { certificate_number, batch_id, quantity }),
  getCertificates: () => api.get('/certificates/'),
  getCertificate: (id) => api.get(`/certificates/${id}`),
  verifyCertificate: (id) => api.post(`/certificates/${id}/verify`),
};

export const auditAPI = {
  getAuditLog: () => api.get('/audit/'),
  verifyAudit: () => api.post('/audit/verify'),
  getAlerts: () => api.get('/alerts/'),
  getCriticalAlerts: () => api.get('/alerts/critical'),
  acknowledgeAlert: (id) => api.post(`/alerts/${id}/acknowledge`),
  getDashboardStats: () => api.get('/dashboard/stats'),
};

export default api;
