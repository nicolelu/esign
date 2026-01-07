'use client';

import { useParams, useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import {
  ArrowLeft,
  Download,
  ExternalLink,
  Clock,
  CheckCircle,
  XCircle,
  Eye,
} from 'lucide-react';
import Link from 'next/link';

import { envelopesApi, signingApi } from '@/lib/api';
import { useAuthStore } from '@/lib/store';
import { cn, formatDate, getStatusColor, getOwnerLabel } from '@/lib/utils';
import { EnvelopeStatus, RecipientStatus } from '@/types';

export default function EnvelopeDetailPage() {
  const params = useParams();
  const router = useRouter();
  const envelopeId = params.id as string;
  const { token } = useAuthStore();

  const { data: envelope, isLoading } = useQuery({
    queryKey: ['envelope', envelopeId],
    queryFn: () => envelopesApi.get(envelopeId, token!),
    enabled: !!token,
  });

  const { data: signingLinks } = useQuery({
    queryKey: ['signingLinks', envelopeId],
    queryFn: () => envelopesApi.getSigningLinks(envelopeId, token!),
    enabled: !!token && envelope?.status !== EnvelopeStatus.DRAFT,
  });

  if (!token) {
    router.push('/');
    return null;
  }

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-gray-500">Loading envelope...</div>
      </div>
    );
  }

  if (!envelope) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-gray-500">Envelope not found</div>
      </div>
    );
  }

  const getRecipientIcon = (status: RecipientStatus) => {
    switch (status) {
      case RecipientStatus.COMPLETED:
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case RecipientStatus.DECLINED:
        return <XCircle className="w-5 h-5 text-red-500" />;
      case RecipientStatus.VIEWED:
      case RecipientStatus.SIGNING:
        return <Eye className="w-5 h-5 text-blue-500" />;
      default:
        return <Clock className="w-5 h-5 text-gray-400" />;
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b px-4 py-4">
        <div className="max-w-4xl mx-auto flex items-center gap-4">
          <button
            onClick={() => router.push('/')}
            className="text-gray-500 hover:text-gray-700"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div className="flex-1">
            <h1 className="text-xl font-semibold text-gray-900">{envelope.name}</h1>
            <p className="text-sm text-gray-500">
              Created {formatDate(envelope.created_at)}
            </p>
          </div>
          <span
            className={cn(
              'px-3 py-1 rounded-full text-sm font-medium',
              getStatusColor(envelope.status)
            )}
          >
            {envelope.status}
          </span>
        </div>
      </header>

      <main className="max-w-4xl mx-auto py-8 px-4">
        <div className="grid gap-6">
          {/* Status Card */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-medium text-gray-900 mb-4">Recipients</h2>
            <div className="space-y-4">
              {envelope.recipients.map((recipient) => {
                const signingLink = signingLinks?.signing_links.find(
                  (l) => l.recipient_id === recipient.id
                );

                return (
                  <div
                    key={recipient.id}
                    className="flex items-center justify-between p-4 border rounded-lg"
                  >
                    <div className="flex items-center gap-4">
                      {getRecipientIcon(recipient.status)}
                      <div>
                        <p className="font-medium text-gray-900">{recipient.name}</p>
                        <p className="text-sm text-gray-500">{recipient.email}</p>
                        <p className="text-xs text-gray-400">
                          {getOwnerLabel(recipient.role)}
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <span
                        className={cn(
                          'px-2 py-1 rounded-full text-xs font-medium',
                          getStatusColor(recipient.status)
                        )}
                      >
                        {recipient.status}
                      </span>
                      {signingLink &&
                        recipient.status !== RecipientStatus.COMPLETED && (
                          <div className="mt-2">
                            <Link
                              href={`/sign/${encodeURIComponent(
                                signingLink.signing_url.split('/sign/')[1]
                              )}`}
                              target="_blank"
                              className="text-sm text-primary-600 hover:text-primary-700 flex items-center gap-1"
                            >
                              Open signing link
                              <ExternalLink className="w-3 h-3" />
                            </Link>
                          </div>
                        )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Document Info */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-medium text-gray-900 mb-4">Document</h2>
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium text-gray-900">{envelope.document.name}</p>
                <p className="text-sm text-gray-500">
                  {envelope.document.page_count} pages
                </p>
              </div>
              {envelope.status === EnvelopeStatus.COMPLETED && (
                <div className="flex gap-2">
                  <a
                    href={signingApi.downloadFinal(envelope.id, token)}
                    className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
                  >
                    <Download className="w-4 h-4" />
                    Download Signed
                  </a>
                  <a
                    href={signingApi.downloadCertificate(envelope.id, token)}
                    className="flex items-center gap-2 px-4 py-2 border rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
                  >
                    <Download className="w-4 h-4" />
                    Certificate
                  </a>
                </div>
              )}
            </div>
          </div>

          {/* Sender Variables */}
          {envelope.sender_variables &&
            Object.keys(envelope.sender_variables).length > 0 && (
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-lg font-medium text-gray-900 mb-4">
                  Sender Variables
                </h2>
                <div className="grid grid-cols-2 gap-4">
                  {Object.entries(envelope.sender_variables).map(([key, value]) => (
                    <div key={key}>
                      <p className="text-sm text-gray-500">{key}</p>
                      <p className="font-medium text-gray-900">{value}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

          {/* Timeline */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-medium text-gray-900 mb-4">Timeline</h2>
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <div className="w-2 h-2 rounded-full bg-gray-400" />
                <span className="text-sm text-gray-600">
                  Created on {formatDate(envelope.created_at)}
                </span>
              </div>
              {envelope.sent_at && (
                <div className="flex items-center gap-3">
                  <div className="w-2 h-2 rounded-full bg-blue-500" />
                  <span className="text-sm text-gray-600">
                    Sent on {formatDate(envelope.sent_at)}
                  </span>
                </div>
              )}
              {envelope.recipients.map(
                (r) =>
                  r.viewed_at && (
                    <div key={`viewed-${r.id}`} className="flex items-center gap-3">
                      <div className="w-2 h-2 rounded-full bg-yellow-500" />
                      <span className="text-sm text-gray-600">
                        {r.name} viewed on {formatDate(r.viewed_at)}
                      </span>
                    </div>
                  )
              )}
              {envelope.recipients.map(
                (r) =>
                  r.completed_at && (
                    <div key={`completed-${r.id}`} className="flex items-center gap-3">
                      <div className="w-2 h-2 rounded-full bg-green-500" />
                      <span className="text-sm text-gray-600">
                        {r.name} signed on {formatDate(r.completed_at)}
                      </span>
                    </div>
                  )
              )}
              {envelope.completed_at && (
                <div className="flex items-center gap-3">
                  <div className="w-2 h-2 rounded-full bg-green-600" />
                  <span className="text-sm text-gray-600">
                    Completed on {formatDate(envelope.completed_at)}
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
