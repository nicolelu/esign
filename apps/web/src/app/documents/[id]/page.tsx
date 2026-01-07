'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeft,
  Save,
  Send,
  Trash2,
  Plus,
  Wand2,
  ChevronLeft,
  ChevronRight,
  ZoomIn,
  ZoomOut,
} from 'lucide-react';
import toast from 'react-hot-toast';

import { documentsApi, fieldsApi } from '@/lib/api';
import { useAuthStore, useEditorStore } from '@/lib/store';
import { cn, getFieldTypeLabel, getOwnerLabel, getOwnerColor } from '@/lib/utils';
import { FieldType, FieldOwner, type Field, type FieldCreate, type BoundingBox } from '@/types';

import FieldOverlay from '@/components/FieldOverlay';
import FieldPropertiesPanel from '@/components/FieldPropertiesPanel';
import SendModal from '@/components/SendModal';

export default function DocumentEditorPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const documentId = params.id as string;

  const { token } = useAuthStore();
  const {
    fields,
    setFields,
    addField,
    updateField,
    removeField,
    selectedFieldId,
    setSelectedFieldId,
    currentPage,
    setCurrentPage,
    zoom,
    setZoom,
    isDrawing,
    setIsDrawing,
    drawingFieldType,
    setDrawingFieldType,
    reset,
  } = useEditorStore();

  const [showSendModal, setShowSendModal] = useState(false);
  const [drawStart, setDrawStart] = useState<{ x: number; y: number } | null>(null);
  const [currentRect, setCurrentRect] = useState<BoundingBox | null>(null);

  // Fetch document
  const { data: document, isLoading } = useQuery({
    queryKey: ['document', documentId],
    queryFn: () => documentsApi.get(documentId, token!),
    enabled: !!token,
    onSuccess: (data) => {
      setFields(data.fields);
    },
  });

  // Create field mutation
  const createFieldMutation = useMutation({
    mutationFn: (field: FieldCreate) => fieldsApi.create(documentId, field, token!),
    onSuccess: (newField) => {
      addField(newField);
      setSelectedFieldId(newField.id);
      toast.success('Field created');
    },
    onError: () => toast.error('Failed to create field'),
  });

  // Update field mutation
  const updateFieldMutation = useMutation({
    mutationFn: ({ fieldId, updates }: { fieldId: string; updates: Partial<Field> }) =>
      fieldsApi.update(documentId, fieldId, updates, token!),
    onSuccess: (updatedField) => {
      updateField(updatedField.id, updatedField);
    },
    onError: () => toast.error('Failed to update field'),
  });

  // Delete field mutation
  const deleteFieldMutation = useMutation({
    mutationFn: (fieldId: string) => fieldsApi.delete(documentId, fieldId, token!),
    onSuccess: (_, fieldId) => {
      removeField(fieldId);
      toast.success('Field deleted');
    },
    onError: () => toast.error('Failed to delete field'),
  });

  // Reset on unmount
  useEffect(() => {
    return () => reset();
  }, [reset]);

  if (!token) {
    router.push('/');
    return null;
  }

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-gray-500">Loading document...</div>
      </div>
    );
  }

  if (!document) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-gray-500">Document not found</div>
      </div>
    );
  }

  const currentPageFields = fields.filter((f) => f.page_number === currentPage);
  const selectedField = fields.find((f) => f.id === selectedFieldId);
  const pageImageUrl = document.page_images?.[currentPage - 1];

  const handleStartDrawing = (type: FieldType) => {
    setDrawingFieldType(type);
    setIsDrawing(true);
  };

  const handleCanvasMouseDown = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!isDrawing || !drawingFieldType) return;

    const rect = e.currentTarget.getBoundingClientRect();
    const x = (e.clientX - rect.left) / zoom;
    const y = (e.clientY - rect.top) / zoom;

    setDrawStart({ x, y });
    setSelectedFieldId(null);
  };

  const handleCanvasMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!isDrawing || !drawStart) return;

    const rect = e.currentTarget.getBoundingClientRect();
    const x = (e.clientX - rect.left) / zoom;
    const y = (e.clientY - rect.top) / zoom;

    setCurrentRect({
      x: Math.min(drawStart.x, x),
      y: Math.min(drawStart.y, y),
      width: Math.abs(x - drawStart.x),
      height: Math.abs(y - drawStart.y),
    });
  };

  const handleCanvasMouseUp = () => {
    if (!isDrawing || !currentRect || !drawingFieldType) {
      setDrawStart(null);
      setCurrentRect(null);
      return;
    }

    // Minimum size check
    if (currentRect.width < 20 || currentRect.height < 10) {
      setDrawStart(null);
      setCurrentRect(null);
      toast.error('Field too small');
      return;
    }

    // Create the field
    createFieldMutation.mutate({
      page_number: currentPage,
      bbox: currentRect,
      field_type: drawingFieldType as FieldType,
      owner: FieldOwner.SIGNER_1,
      required: true,
    });

    setDrawStart(null);
    setCurrentRect(null);
    setIsDrawing(false);
    setDrawingFieldType(null);
  };

  const handleFieldUpdate = (fieldId: string, updates: Partial<Field>) => {
    updateFieldMutation.mutate({ fieldId, updates });
  };

  const handleFieldDelete = (fieldId: string) => {
    deleteFieldMutation.mutate(fieldId);
  };

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col">
      {/* Header */}
      <header className="bg-white border-b px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => router.push('/')}
            className="text-gray-500 hover:text-gray-700"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="font-semibold text-gray-900">{document.name}</h1>
            <p className="text-sm text-gray-500">
              {fields.length} fields | Page {currentPage} of {document.page_count}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowSendModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
          >
            <Send className="w-4 h-4" />
            Send for Signing
          </button>
        </div>
      </header>

      <div className="flex-1 flex">
        {/* Left Toolbar */}
        <div className="w-64 bg-white border-r p-4 overflow-y-auto">
          <h3 className="font-medium text-gray-900 mb-3">Add Fields</h3>
          <p className="text-sm text-gray-500 mb-4">
            Click a field type, then draw on the document
          </p>

          <div className="space-y-2">
            {Object.values(FieldType).map((type) => (
              <button
                key={type}
                onClick={() => handleStartDrawing(type)}
                className={cn(
                  'w-full px-3 py-2 text-left text-sm rounded-lg border transition-colors',
                  isDrawing && drawingFieldType === type
                    ? 'border-primary-500 bg-primary-50 text-primary-700'
                    : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                )}
              >
                {getFieldTypeLabel(type)}
              </button>
            ))}
          </div>

          <hr className="my-4" />

          <h3 className="font-medium text-gray-900 mb-3">Fields on Page</h3>
          {currentPageFields.length === 0 ? (
            <p className="text-sm text-gray-500">No fields on this page</p>
          ) : (
            <div className="space-y-2">
              {currentPageFields.map((field) => (
                <div
                  key={field.id}
                  onClick={() => setSelectedFieldId(field.id)}
                  className={cn(
                    'px-3 py-2 rounded-lg border cursor-pointer transition-colors',
                    selectedFieldId === field.id
                      ? 'border-primary-500 bg-primary-50'
                      : 'border-gray-200 hover:border-gray-300'
                  )}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">
                      {getFieldTypeLabel(field.field_type)}
                    </span>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleFieldDelete(field.id);
                      }}
                      className="text-gray-400 hover:text-red-500"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                  <div className={cn('text-xs mt-1 px-2 py-0.5 rounded inline-block', getOwnerColor(field.owner))}>
                    {getOwnerLabel(field.owner)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Document Viewer */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Viewer Toolbar */}
          <div className="bg-white border-b px-4 py-2 flex items-center justify-center gap-4">
            <button
              onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
              disabled={currentPage <= 1}
              className="p-1 rounded hover:bg-gray-100 disabled:opacity-50"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
            <span className="text-sm">
              Page {currentPage} of {document.page_count}
            </span>
            <button
              onClick={() => setCurrentPage(Math.min(document.page_count, currentPage + 1))}
              disabled={currentPage >= document.page_count}
              className="p-1 rounded hover:bg-gray-100 disabled:opacity-50"
            >
              <ChevronRight className="w-5 h-5" />
            </button>

            <div className="border-l pl-4 flex items-center gap-2">
              <button
                onClick={() => setZoom(Math.max(0.5, zoom - 0.1))}
                className="p-1 rounded hover:bg-gray-100"
              >
                <ZoomOut className="w-5 h-5" />
              </button>
              <span className="text-sm w-16 text-center">{Math.round(zoom * 100)}%</span>
              <button
                onClick={() => setZoom(Math.min(2, zoom + 0.1))}
                className="p-1 rounded hover:bg-gray-100"
              >
                <ZoomIn className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Document Canvas */}
          <div className="flex-1 overflow-auto bg-gray-200 p-8">
            <div
              className="relative mx-auto bg-white shadow-lg"
              style={{
                transform: `scale(${zoom})`,
                transformOrigin: 'top center',
              }}
              onMouseDown={handleCanvasMouseDown}
              onMouseMove={handleCanvasMouseMove}
              onMouseUp={handleCanvasMouseUp}
              onMouseLeave={handleCanvasMouseUp}
            >
              {pageImageUrl && (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={pageImageUrl}
                  alt={`Page ${currentPage}`}
                  className="block"
                  draggable={false}
                />
              )}

              {/* Field overlays */}
              {currentPageFields.map((field) => (
                <FieldOverlay
                  key={field.id}
                  field={field}
                  isSelected={field.id === selectedFieldId}
                  onClick={() => setSelectedFieldId(field.id)}
                  onUpdate={(updates) => handleFieldUpdate(field.id, updates)}
                />
              ))}

              {/* Drawing rectangle */}
              {currentRect && (
                <div
                  className="absolute border-2 border-dashed border-primary-500 bg-primary-100 bg-opacity-30"
                  style={{
                    left: currentRect.x,
                    top: currentRect.y,
                    width: currentRect.width,
                    height: currentRect.height,
                  }}
                />
              )}
            </div>
          </div>
        </div>

        {/* Right Panel - Properties */}
        {selectedField && (
          <FieldPropertiesPanel
            field={selectedField}
            onUpdate={(updates) => handleFieldUpdate(selectedField.id, updates)}
            onDelete={() => handleFieldDelete(selectedField.id)}
            onClose={() => setSelectedFieldId(null)}
          />
        )}
      </div>

      {/* Send Modal */}
      {showSendModal && (
        <SendModal
          document={document}
          fields={fields}
          token={token}
          onClose={() => setShowSendModal(false)}
          onSent={(envelopeId) => {
            setShowSendModal(false);
            router.push(`/envelopes/${envelopeId}`);
          }}
        />
      )}
    </div>
  );
}
