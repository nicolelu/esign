/**
 * API client for the AI E-Sign backend.
 */

import type {
  AuthResponse,
  Document,
  DocumentDetail,
  Envelope,
  EnvelopeCreate,
  EnvelopeDetail,
  Field,
  FieldCreate,
  FieldDetectionResponse,
  FieldUpdate,
  FieldValue,
  FieldValueCreate,
  SigningLink,
  SigningSession,
  User,
} from '@/types';

const API_BASE = '/api/v1';

class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string
  ) {
    super(detail);
    this.name = 'ApiError';
  }
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {},
  token?: string
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;

  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };

  // Don't set Content-Type for FormData
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  // Add token as query parameter for MVP (in production, use Authorization header)
  const urlWithToken = token ? `${url}${url.includes('?') ? '&' : '?'}token=${token}` : url;

  const response = await fetch(urlWithToken, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'An error occurred' }));
    throw new ApiError(response.status, error.detail || 'An error occurred');
  }

  // Handle empty responses
  const text = await response.text();
  if (!text) {
    return {} as T;
  }

  return JSON.parse(text);
}

// Auth API
export const authApi = {
  requestMagicLink: (email: string) =>
    request<{ message: string; token: string; magic_link: string }>('/auth/magic-link', {
      method: 'POST',
      body: JSON.stringify({ email }),
    }),

  verifyMagicLink: (token: string) =>
    request<AuthResponse>(`/auth/verify?token=${token}`, {
      method: 'POST',
    }),

  getMe: (token: string) => request<User>('/auth/me', {}, token),
};

// Documents API
export const documentsApi = {
  upload: async (file: File, name: string | undefined, token: string) => {
    const formData = new FormData();
    formData.append('file', file);

    const url = name
      ? `/documents?token=${token}&name=${encodeURIComponent(name)}`
      : `/documents?token=${token}`;

    return request<Document>(url, {
      method: 'POST',
      body: formData,
    });
  },

  list: (token: string, status?: string) => {
    const url = status ? `/documents?status=${status}` : '/documents';
    return request<Document[]>(url, {}, token);
  },

  get: (documentId: string, token: string) =>
    request<DocumentDetail>(`/documents/${documentId}`, {}, token),

  delete: (documentId: string, token: string) =>
    request<{ message: string }>(`/documents/${documentId}`, { method: 'DELETE' }, token),

  getPageImage: (documentId: string, pageNumber: number, token: string) =>
    `${API_BASE}/documents/${documentId}/page/${pageNumber}?token=${token}`,
};

// Fields API
export const fieldsApi = {
  create: (documentId: string, field: FieldCreate, token: string) =>
    request<Field>(`/documents/${documentId}/fields`, {
      method: 'POST',
      body: JSON.stringify(field),
    }, token),

  createBulk: (documentId: string, fields: FieldCreate[], token: string) =>
    request<Field[]>(`/documents/${documentId}/fields/bulk`, {
      method: 'POST',
      body: JSON.stringify(fields),
    }, token),

  list: (documentId: string, token: string) =>
    request<Field[]>(`/documents/${documentId}/fields`, {}, token),

  get: (documentId: string, fieldId: string, token: string) =>
    request<Field>(`/documents/${documentId}/fields/${fieldId}`, {}, token),

  update: (documentId: string, fieldId: string, field: FieldUpdate, token: string) =>
    request<Field>(`/documents/${documentId}/fields/${fieldId}`, {
      method: 'PATCH',
      body: JSON.stringify(field),
    }, token),

  delete: (documentId: string, fieldId: string, token: string) =>
    request<{ message: string }>(`/documents/${documentId}/fields/${fieldId}`, {
      method: 'DELETE',
    }, token),

  deleteAll: (documentId: string, token: string) =>
    request<{ message: string }>(`/documents/${documentId}/fields`, {
      method: 'DELETE',
    }, token),
};

// Envelopes API
export const envelopesApi = {
  create: (envelope: EnvelopeCreate, token: string) =>
    request<Envelope>('/envelopes', {
      method: 'POST',
      body: JSON.stringify(envelope),
    }, token),

  list: (token: string, status?: string) => {
    const url = status ? `/envelopes?status_filter=${status}` : '/envelopes';
    return request<Envelope[]>(url, {}, token);
  },

  get: (envelopeId: string, token: string) =>
    request<EnvelopeDetail>(`/envelopes/${envelopeId}`, {}, token),

  send: (envelopeId: string, senderVariables?: Record<string, string>, token?: string) =>
    request<Envelope>(`/envelopes/${envelopeId}/send`, {
      method: 'POST',
      body: JSON.stringify({ sender_variables: senderVariables }),
    }, token),

  getSigningLinks: (envelopeId: string, token: string) =>
    request<{ envelope_id: string; signing_links: SigningLink[] }>(
      `/envelopes/${envelopeId}/signing-links`,
      {},
      token
    ),

  void: (envelopeId: string, token: string) =>
    request<{ message: string }>(`/envelopes/${envelopeId}`, {
      method: 'DELETE',
    }, token),
};

// Signing API
export const signingApi = {
  getSession: (signingToken: string) =>
    request<SigningSession>(`/signing/session/${signingToken}`),

  saveFieldValue: (signingToken: string, fieldValue: FieldValueCreate) =>
    request<FieldValue>(`/signing/session/${signingToken}/field`, {
      method: 'POST',
      body: JSON.stringify(fieldValue),
    }),

  complete: (signingToken: string, fieldValues: FieldValueCreate[]) =>
    request<{ message: string; all_completed: boolean }>(
      `/signing/session/${signingToken}/complete`,
      {
        method: 'POST',
        body: JSON.stringify({ field_values: fieldValues }),
      }
    ),

  downloadFinal: (envelopeId: string, token: string) =>
    `${API_BASE}/signing/download/${envelopeId}/final?token=${token}`,

  downloadCertificate: (envelopeId: string, token: string) =>
    `${API_BASE}/signing/download/${envelopeId}/certificate?token=${token}`,
};

// Detection API (to be implemented)
export const detectionApi = {
  detectFields: (documentId: string, token: string) =>
    request<FieldDetectionResponse>(`/documents/${documentId}/detect`, {
      method: 'POST',
    }, token),
};
