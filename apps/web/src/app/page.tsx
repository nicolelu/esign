'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { FileText, Plus, Send, CheckCircle } from 'lucide-react';
import Link from 'next/link';
import toast from 'react-hot-toast';

import { authApi, documentsApi, envelopesApi } from '@/lib/api';
import { useAuthStore } from '@/lib/store';
import { cn, formatDate, formatFileSize, getStatusColor } from '@/lib/utils';
import type { Document, Envelope } from '@/types';

import AuthModal from '@/components/AuthModal';
import UploadModal from '@/components/UploadModal';

export default function HomePage() {
  const { token, user, setToken, setUser, logout } = useAuthStore();
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [activeTab, setActiveTab] = useState<'documents' | 'envelopes'>('documents');

  // Fetch user on mount if token exists
  useQuery({
    queryKey: ['user', token],
    queryFn: () => authApi.getMe(token!),
    enabled: !!token && !user,
    onSuccess: (data) => setUser(data),
    onError: () => {
      logout();
      toast.error('Session expired. Please login again.');
    },
  });

  // Fetch documents
  const { data: documents, isLoading: loadingDocs, refetch: refetchDocs } = useQuery({
    queryKey: ['documents', token],
    queryFn: () => documentsApi.list(token!),
    enabled: !!token,
  });

  // Fetch envelopes
  const { data: envelopes, isLoading: loadingEnvelopes, refetch: refetchEnvelopes } = useQuery({
    queryKey: ['envelopes', token],
    queryFn: () => envelopesApi.list(token!),
    enabled: !!token,
  });

  const handleLogin = async (email: string) => {
    try {
      const response = await authApi.requestMagicLink(email);
      // For MVP, auto-verify the token
      const authResponse = await authApi.verifyMagicLink(response.token);
      setToken(authResponse.access_token);
      const userData = await authApi.getMe(authResponse.access_token);
      setUser(userData);
      setShowAuthModal(false);
      toast.success('Logged in successfully!');
    } catch (error) {
      toast.error('Failed to login. Please try again.');
    }
  };

  const handleUploadComplete = () => {
    setShowUploadModal(false);
    refetchDocs();
    toast.success('Document uploaded successfully!');
  };

  if (!token) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-4">
        <div className="max-w-md w-full text-center">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">AI E-Sign</h1>
          <p className="text-gray-600 mb-8">
            Intelligent document signing with automatic field detection
          </p>
          <button
            onClick={() => setShowAuthModal(true)}
            className="px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
          >
            Get Started
          </button>
        </div>
        {showAuthModal && (
          <AuthModal
            onClose={() => setShowAuthModal(false)}
            onLogin={handleLogin}
          />
        )}
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <h1 className="text-xl font-bold text-gray-900">AI E-Sign</h1>
          <div className="flex items-center gap-4">
            <span className="text-gray-600">{user?.email}</span>
            <button
              onClick={logout}
              className="text-gray-500 hover:text-gray-700"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Tabs */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex gap-4">
            <button
              onClick={() => setActiveTab('documents')}
              className={cn(
                'px-4 py-2 rounded-lg font-medium transition-colors',
                activeTab === 'documents'
                  ? 'bg-primary-100 text-primary-700'
                  : 'text-gray-600 hover:bg-gray-100'
              )}
            >
              <FileText className="inline-block w-4 h-4 mr-2" />
              Documents
            </button>
            <button
              onClick={() => setActiveTab('envelopes')}
              className={cn(
                'px-4 py-2 rounded-lg font-medium transition-colors',
                activeTab === 'envelopes'
                  ? 'bg-primary-100 text-primary-700'
                  : 'text-gray-600 hover:bg-gray-100'
              )}
            >
              <Send className="inline-block w-4 h-4 mr-2" />
              Envelopes
            </button>
          </div>

          <button
            onClick={() => setShowUploadModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
          >
            <Plus className="w-4 h-4" />
            Upload Document
          </button>
        </div>

        {/* Documents Tab */}
        {activeTab === 'documents' && (
          <div className="bg-white rounded-lg shadow">
            {loadingDocs ? (
              <div className="p-8 text-center text-gray-500">Loading...</div>
            ) : documents?.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                <FileText className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                <p>No documents yet. Upload one to get started.</p>
              </div>
            ) : (
              <table className="w-full">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="text-left px-6 py-3 text-sm font-medium text-gray-500">Name</th>
                    <th className="text-left px-6 py-3 text-sm font-medium text-gray-500">Status</th>
                    <th className="text-left px-6 py-3 text-sm font-medium text-gray-500">Size</th>
                    <th className="text-left px-6 py-3 text-sm font-medium text-gray-500">Created</th>
                    <th className="text-left px-6 py-3 text-sm font-medium text-gray-500">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {documents?.map((doc: Document) => (
                    <tr key={doc.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <FileText className="w-5 h-5 text-gray-400" />
                          <div>
                            <div className="font-medium text-gray-900">{doc.name}</div>
                            <div className="text-sm text-gray-500">{doc.page_count} pages</div>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <span className={cn('px-2 py-1 rounded-full text-xs font-medium', getStatusColor(doc.status))}>
                          {doc.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-gray-500">{formatFileSize(doc.file_size)}</td>
                      <td className="px-6 py-4 text-gray-500">{formatDate(doc.created_at)}</td>
                      <td className="px-6 py-4">
                        <Link
                          href={`/documents/${doc.id}`}
                          className="text-primary-600 hover:text-primary-700 font-medium"
                        >
                          Edit Fields
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

        {/* Envelopes Tab */}
        {activeTab === 'envelopes' && (
          <div className="bg-white rounded-lg shadow">
            {loadingEnvelopes ? (
              <div className="p-8 text-center text-gray-500">Loading...</div>
            ) : envelopes?.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                <Send className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                <p>No envelopes yet. Send a document for signing to create one.</p>
              </div>
            ) : (
              <table className="w-full">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="text-left px-6 py-3 text-sm font-medium text-gray-500">Name</th>
                    <th className="text-left px-6 py-3 text-sm font-medium text-gray-500">Status</th>
                    <th className="text-left px-6 py-3 text-sm font-medium text-gray-500">Recipients</th>
                    <th className="text-left px-6 py-3 text-sm font-medium text-gray-500">Sent</th>
                    <th className="text-left px-6 py-3 text-sm font-medium text-gray-500">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {envelopes?.map((envelope: Envelope) => (
                    <tr key={envelope.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4">
                        <div className="font-medium text-gray-900">{envelope.name}</div>
                      </td>
                      <td className="px-6 py-4">
                        <span className={cn('px-2 py-1 rounded-full text-xs font-medium', getStatusColor(envelope.status))}>
                          {envelope.status}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-2">
                          {envelope.recipients.map((r) => (
                            <span
                              key={r.id}
                              className={cn('px-2 py-1 rounded-full text-xs', getStatusColor(r.status))}
                              title={`${r.name} - ${r.status}`}
                            >
                              {r.name.charAt(0)}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td className="px-6 py-4 text-gray-500">
                        {envelope.sent_at ? formatDate(envelope.sent_at) : '-'}
                      </td>
                      <td className="px-6 py-4">
                        <Link
                          href={`/envelopes/${envelope.id}`}
                          className="text-primary-600 hover:text-primary-700 font-medium"
                        >
                          View
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      </main>

      {/* Upload Modal */}
      {showUploadModal && (
        <UploadModal
          token={token}
          onClose={() => setShowUploadModal(false)}
          onComplete={handleUploadComplete}
        />
      )}
    </div>
  );
}
