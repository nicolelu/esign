'use client';

import { X, Trash2 } from 'lucide-react';
import { FieldType, FieldOwner, type Field } from '@/types';
import { cn, getFieldTypeLabel, getOwnerLabel, formatConfidence, getConfidenceColor } from '@/lib/utils';

interface FieldPropertiesPanelProps {
  field: Field;
  onUpdate: (updates: Partial<Field>) => void;
  onDelete: () => void;
  onClose: () => void;
}

export default function FieldPropertiesPanel({
  field,
  onUpdate,
  onDelete,
  onClose,
}: FieldPropertiesPanelProps) {
  return (
    <div className="w-80 bg-white border-l p-4 overflow-y-auto">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-medium text-gray-900">Field Properties</h3>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-gray-600"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      <div className="space-y-4">
        {/* Field Type */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Field Type
          </label>
          <select
            value={field.field_type}
            onChange={(e) => onUpdate({ field_type: e.target.value as FieldType })}
            className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            {Object.values(FieldType).map((type) => (
              <option key={type} value={type}>
                {getFieldTypeLabel(type)}
              </option>
            ))}
          </select>
        </div>

        {/* Owner */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Assigned To
          </label>
          <select
            value={field.owner}
            onChange={(e) => onUpdate({ owner: e.target.value as FieldOwner })}
            className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            {Object.values(FieldOwner).map((owner) => (
              <option key={owner} value={owner}>
                {getOwnerLabel(owner)}
              </option>
            ))}
          </select>
        </div>

        {/* Required */}
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium text-gray-700">Required</label>
          <button
            onClick={() => onUpdate({ required: !field.required })}
            className={cn(
              'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
              field.required ? 'bg-primary-600' : 'bg-gray-200'
            )}
          >
            <span
              className={cn(
                'inline-block h-4 w-4 transform rounded-full bg-white transition-transform',
                field.required ? 'translate-x-6' : 'translate-x-1'
              )}
            />
          </button>
        </div>

        {/* Label */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Label (internal)
          </label>
          <input
            type="text"
            value={field.label || ''}
            onChange={(e) => onUpdate({ label: e.target.value || null })}
            placeholder="e.g., Client Signature"
            className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        </div>

        {/* Placeholder (for text fields) */}
        {['TEXT', 'NAME', 'EMAIL'].includes(field.field_type) && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Placeholder
            </label>
            <input
              type="text"
              value={field.placeholder || ''}
              onChange={(e) => onUpdate({ placeholder: e.target.value || null })}
              placeholder="e.g., Enter your name"
              className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>
        )}

        {/* Default Value */}
        {field.owner === FieldOwner.SENDER && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Sender Variable Key
            </label>
            <input
              type="text"
              value={field.sender_variable_key || ''}
              onChange={(e) => onUpdate({ sender_variable_key: e.target.value || null })}
              placeholder="e.g., effective_date"
              className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
            <p className="text-xs text-gray-500 mt-1">
              This value will be set when sending the document
            </p>
          </div>
        )}

        {/* Confidence Scores (if available) */}
        {(field.detection_confidence !== null ||
          field.classification_confidence !== null ||
          field.owner_confidence !== null) && (
          <div className="pt-4 border-t">
            <h4 className="text-sm font-medium text-gray-700 mb-2">
              Detection Confidence
            </h4>
            <div className="space-y-1 text-sm">
              {field.detection_confidence !== null && (
                <div className="flex justify-between">
                  <span className="text-gray-500">Detection:</span>
                  <span className={getConfidenceColor(field.detection_confidence)}>
                    {formatConfidence(field.detection_confidence)}
                  </span>
                </div>
              )}
              {field.classification_confidence !== null && (
                <div className="flex justify-between">
                  <span className="text-gray-500">Classification:</span>
                  <span className={getConfidenceColor(field.classification_confidence)}>
                    {formatConfidence(field.classification_confidence)}
                  </span>
                </div>
              )}
              {field.owner_confidence !== null && (
                <div className="flex justify-between">
                  <span className="text-gray-500">Owner:</span>
                  <span className={getConfidenceColor(field.owner_confidence)}>
                    {formatConfidence(field.owner_confidence)}
                  </span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Evidence */}
        {field.evidence && (
          <div className="pt-4 border-t">
            <h4 className="text-sm font-medium text-gray-700 mb-2">
              Why this classification?
            </h4>
            <p className="text-sm text-gray-600 bg-gray-50 p-2 rounded">
              {field.evidence}
            </p>
          </div>
        )}

        {/* Delete Button */}
        <div className="pt-4 border-t">
          <button
            onClick={onDelete}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 border border-red-300 text-red-600 rounded-lg hover:bg-red-50 transition-colors"
          >
            <Trash2 className="w-4 h-4" />
            Delete Field
          </button>
        </div>
      </div>
    </div>
  );
}
