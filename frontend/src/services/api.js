// 100% Frontend-Mocked API Layer for PharmMedian Platform
// Runs entirely standalone in the browser using local storage & mock database.
// Zero backend server required.

import { handleMockRequest } from './mockHandler';

// Simulated delay helper for realistic UI state handling
const asyncMock = async (url, method, data = null) => {
  await new Promise((resolve) => setTimeout(resolve, 30));
  return handleMockRequest(url, method, data);
};

const api = {
  get: (url) => asyncMock(url, 'GET'),
  post: (url, data) => asyncMock(url, 'POST', data),
  put: (url, data) => asyncMock(url, 'PUT', data),
  delete: (url) => asyncMock(url, 'DELETE'),
  interceptors: {
    request: { use: () => {} },
    response: { use: () => {} },
  },
};

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

export const dashboardAPI = {
  getPharmacyDashboard: () => api.get('/dashboard/pharmacy'),
  getDistributorDashboard: () => api.get('/dashboard/distributor'),
  getManufacturerDashboard: () => api.get('/dashboard/manufacturer'),
  getFacilityDashboard: () => api.get('/dashboard/facility'),
  getRegulatorDashboard: () => api.get('/dashboard/regulator'),
  getRoleDashboard: (role) => api.get(`/dashboard/${role}`),
  resetDashboard: (mode = 'fresh') => api.post('/dashboard/reset', { mode }),
};

export const evidenceAPI = {
  uploadEvidence: (formData) =>
    api.post('/evidence/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }),
};

export const reallocationAPI = {
  getRecommendations: () => api.get('/reallocation/recommendations'),
  getRawData: () => api.get('/reallocation/raw-data'),
};

export default api;
