'use client';

import { useState, useEffect, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  ChevronLeft,
  ChevronRight,
  Check,
  AlertCircle,
} from 'lucide-react';
import toast from 'react-hot-toast';
import SignatureCanvas from 'react-signature-canvas';

import { signingApi } from '@/lib/api';
import { cn, getFieldTypeLabel, getOwnerColor } from '@/lib/utils';
import { FieldType, FieldOwner, type Field, type FieldValue, type FieldValueCreate } from '@/types';

export default function SigningPage() {
  const params = useParams();
  const router = useRouter();
  const signingToken = params.token as string;

  const [currentPage, setCurrentPage] = useState(1);
  const [fieldValues, setFieldValues] = useState<Record<string, FieldValueCreate>>({});
  const [showSignatureModal, setShowSignatureModal] = useState<string | null>(null);
  const signatureRef = useRef<SignatureCanvas>(null);

  // Fetch signing session
  const { data: session, isLoading, error } = useQuery({
    queryKey: ['signingSession', signingToken],
    queryFn: () => signingApi.getSession(signingToken),
    retry: false,
  });

  // Save field value mutation
  const saveFieldMutation = useMutation({
    mutationFn: (fieldValue: FieldValueCreate) =>
      signingApi.saveFieldValue(signingToken, fieldValue),
  });

  // Complete signing mutation
  const completeMutation = useMutation({
    mutationFn: (values: FieldValueCreate[]) =>
      signingApi.complete(signingToken, values),
    onSuccess: (data) => {
      if (data.all_completed) {
        toast.success('All parties have signed! Document is complete.');
      } else {
        toast.success('Your signature has been recorded. Waiting for other parties.');
      }
      router.push('/sign/complete');
    },
    onError: () => {
      toast.error('Failed to complete signing');
    },
  });

  // Initialize field values from session
  useEffect(() => {
    if (session) {
      const values: Record<string, FieldValueCreate> = {};

      // Pre-fill sender variables
      for (const field of session.fields) {
        if (field.owner === FieldOwner.SENDER && field.sender_variable_key) {
          const value = session.sender_variables?.[field.sender_variable_key];
          if (value) {
            values[field.id] = { field_id: field.id, value };
          }
        }
      }

      // Load existing values
      for (const fv of session.field_values) {
        values[fv.field_id] = {
          field_id: fv.field_id,
          value: fv.value || undefined,
          signature_data: fv.signature_data || undefined,
        };
      }

      setFieldValues(values);
    }
  }, [session]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-100">
        <div className="text-gray-500">Loading signing session...</div>
      </div>
    );
  }

  if (error || !session) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-100">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 mx-auto mb-4 text-red-500" />
          <h1 className="text-xl font-semibold text-gray-900 mb-2">
            Invalid or Expired Link
          </h1>
          <p className="text-gray-500">
            This signing link is no longer valid.
          </p>
        </div>
      </div>
    );
  }

  const myFields = session.fields.filter((f) => f.owner === session.recipient_role);
  const senderFields = session.fields.filter((f) => f.owner === FieldOwner.SENDER);
  const currentPageFields = [...myFields, ...senderFields].filter(
    (f) => f.page_number === currentPage
  );

  const allRequiredFieldsFilled = myFields
    .filter((f) => f.required)
    .every((f) => {
      const fv = fieldValues[f.id];
      return fv && (fv.value || fv.signature_data);
    });

  const handleFieldChange = (fieldId: string, value: string) => {
    const newValue = { field_id: fieldId, value };
    setFieldValues({ ...fieldValues, [fieldId]: newValue });

    // Auto-save
    saveFieldMutation.mutate(newValue);
  };

  const handleSignatureComplete = () => {
    if (!signatureRef.current || !showSignatureModal) return;

    const signatureData = signatureRef.current.toDataURL('image/png');
    const newValue = {
      field_id: showSignatureModal,
      signature_data: signatureData,
    };
    setFieldValues({ ...fieldValues, [showSignatureModal]: newValue });
    saveFieldMutation.mutate(newValue);
    setShowSignatureModal(null);
  };

  const handleComplete = () => {
    const values = Object.values(fieldValues);
    completeMutation.mutate(values);
  };

  const getFieldValue = (fieldId: string) => {
    return fieldValues[fieldId]?.value || '';
  };

  const getSignatureData = (fieldId: string) => {
    return fieldValues[fieldId]?.signature_data;
  };

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col">
      {/* Header */}
      <header className="bg-white border-b px-4 py-4">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="font-semibold text-gray-900">{session.document_name}</h1>
            <p className="text-sm text-gray-500">
              Signing as {session.recipient_name}
            </p>
          </div>
          <button
            onClick={handleComplete}
            disabled={!allRequiredFieldsFilled || completeMutation.isPending}
            className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Check className="w-4 h-4" />
            {completeMutation.isPending ? 'Completing...' : 'Complete Signing'}
          </button>
        </div>
      </header>

      {/* Progress */}
      <div className="bg-white border-b px-4 py-2">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-center gap-2 text-sm">
            <span className="text-gray-500">Fields to complete:</span>
            {myFields.map((field) => {
              const fv = fieldValues[field.id];
              const isFilled = fv && (fv.value || fv.signature_data);
              return (
                <button
                  key={field.id}
                  onClick={() => setCurrentPage(field.page_number)}
                  className={cn(
                    'px-2 py-1 rounded text-xs font-medium',
                    isFilled
                      ? 'bg-green-100 text-green-700'
                      : field.required
                      ? 'bg-red-100 text-red-700'
                      : 'bg-gray-100 text-gray-700'
                  )}
                >
                  {getFieldTypeLabel(field.field_type)}
                  {field.required && !isFilled && '*'}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Document Viewer */}
      <div className="flex-1 overflow-auto p-8">
        <div className="max-w-4xl mx-auto">
          {/* Page Navigation */}
          <div className="flex items-center justify-center gap-4 mb-4">
            <button
              onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
              disabled={currentPage <= 1}
              className="p-1 rounded hover:bg-gray-200 disabled:opacity-50"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
            <span className="text-sm">
              Page {currentPage} of {session.page_count}
            </span>
            <button
              onClick={() => setCurrentPage(Math.min(session.page_count, currentPage + 1))}
              disabled={currentPage >= session.page_count}
              className="p-1 rounded hover:bg-gray-200 disabled:opacity-50"
            >
              <ChevronRight className="w-5 h-5" />
            </button>
          </div>

          {/* Document with Fields */}
          <div className="relative bg-white shadow-lg">
            {session.page_images[currentPage - 1] && (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={session.page_images[currentPage - 1]}
                alt={`Page ${currentPage}`}
                className="block w-full"
              />
            )}

            {/* Field Overlays */}
            {currentPageFields.map((field) => {
              const isMine = field.owner === session.recipient_role;
              const signatureData = getSignatureData(field.id);

              return (
                <div
                  key={field.id}
                  className={cn(
                    'absolute border-2 rounded',
                    isMine ? 'border-blue-500 bg-blue-50' : 'border-gray-300 bg-gray-50',
                    !isMine && 'opacity-75'
                  )}
                  style={{
                    left: field.bbox.x,
                    top: field.bbox.y,
                    width: field.bbox.width,
                    height: field.bbox.height,
                  }}
                >
                  {/* Sender fields - read only */}
                  {field.owner === FieldOwner.SENDER && (
                    <div className="w-full h-full flex items-center px-2 text-sm text-gray-700">
                      {field.sender_variable_key &&
                        session.sender_variables?.[field.sender_variable_key]}
                    </div>
                  )}

                  {/* My fields - editable */}
                  {isMine && (
                    <>
                      {/* Text/Name/Email fields */}
                      {[FieldType.TEXT, FieldType.NAME, FieldType.EMAIL].includes(
                        field.field_type
                      ) && (
                        <input
                          type={field.field_type === FieldType.EMAIL ? 'email' : 'text'}
                          value={getFieldValue(field.id)}
                          onChange={(e) => handleFieldChange(field.id, e.target.value)}
                          placeholder={field.placeholder || getFieldTypeLabel(field.field_type)}
                          className="w-full h-full px-2 bg-transparent text-sm focus:outline-none"
                        />
                      )}

                      {/* Date Signed - auto-fills */}
                      {field.field_type === FieldType.DATE_SIGNED && (
                        <div className="w-full h-full flex items-center px-2 text-sm text-gray-500">
                          {new Date().toLocaleDateString()}
                        </div>
                      )}

                      {/* Checkbox */}
                      {field.field_type === FieldType.CHECKBOX && (
                        <label className="w-full h-full flex items-center justify-center cursor-pointer">
                          <input
                            type="checkbox"
                            checked={getFieldValue(field.id) === 'true'}
                            onChange={(e) =>
                              handleFieldChange(field.id, e.target.checked ? 'true' : '')
                            }
                            className="w-5 h-5"
                          />
                        </label>
                      )}

                      {/* Signature/Initials */}
                      {[FieldType.SIGNATURE, FieldType.INITIALS].includes(
                        field.field_type
                      ) && (
                        <button
                          onClick={() => setShowSignatureModal(field.id)}
                          className="w-full h-full flex items-center justify-center"
                        >
                          {signatureData ? (
                            // eslint-disable-next-line @next/next/no-img-element
                            <img
                              src={signatureData}
                              alt="Signature"
                              className="max-w-full max-h-full object-contain"
                            />
                          ) : (
                            <span className="text-sm text-blue-600">
                              Click to {field.field_type === FieldType.SIGNATURE ? 'sign' : 'initial'}
                            </span>
                          )}
                        </button>
                      )}
                    </>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Signature Modal */}
      {showSignatureModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md">
            <h3 className="text-lg font-medium mb-4">Draw Your Signature</h3>
            <div className="border rounded-lg overflow-hidden mb-4">
              <SignatureCanvas
                ref={signatureRef}
                canvasProps={{
                  className: 'signature-canvas w-full',
                  style: { width: '100%', height: '200px' },
                }}
                backgroundColor="white"
              />
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => signatureRef.current?.clear()}
                className="flex-1 px-4 py-2 border rounded-lg text-gray-700 hover:bg-gray-50"
              >
                Clear
              </button>
              <button
                onClick={() => setShowSignatureModal(null)}
                className="flex-1 px-4 py-2 border rounded-lg text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleSignatureComplete}
                className="flex-1 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
              >
                Apply
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
