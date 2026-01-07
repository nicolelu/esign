'use client';

import { useState, useMemo } from 'react';
import { X, Plus, Trash2 } from 'lucide-react';
import toast from 'react-hot-toast';

import { envelopesApi } from '@/lib/api';
import { AssigneeType, FieldOwner, type Document, type Field, type RecipientCreate, type RoleCreate } from '@/types';
import { getOwnerLabel, getRoleLabel } from '@/lib/utils';

interface SendModalProps {
  document: Document;
  fields: Field[];
  token: string;
  onClose: () => void;
  onSent: (envelopeId: string) => void;
}

interface RoleInput {
  key: string;
  display_name: string;
  color: string;
}

interface RecipientInput {
  id: string;
  email: string;
  name: string;
  role_key: string;
}

// Default colors for roles
const ROLE_COLORS = [
  '#3B82F6', // Blue
  '#10B981', // Green
  '#8B5CF6', // Purple
  '#F59E0B', // Amber
  '#EC4899', // Pink
  '#6B7280', // Gray
  '#EF4444', // Red
  '#14B8A6', // Teal
];

export default function SendModal({
  document,
  fields,
  token,
  onClose,
  onSent,
}: SendModalProps) {
  // Detect roles needed from document fields
  const detectedRoles = useMemo(() => {
    const roleMap = new Map<string, RoleInput>();

    fields.forEach((field) => {
      // Skip sender fields
      if (field.assignee_type === AssigneeType.SENDER || field.owner === FieldOwner.SENDER) {
        return;
      }

      // Use detected_role_key if available, otherwise fall back to owner
      let roleKey = field.detected_role_key;
      if (!roleKey && field.owner) {
        roleKey = field.owner.toLowerCase();
      }
      if (!roleKey) {
        roleKey = 'signer';
      }

      if (!roleMap.has(roleKey)) {
        const colorIndex = roleMap.size % ROLE_COLORS.length;
        roleMap.set(roleKey, {
          key: roleKey,
          display_name: getRoleLabel(roleKey),
          color: ROLE_COLORS[colorIndex],
        });
      }
    });

    // Ensure at least one role exists
    if (roleMap.size === 0) {
      roleMap.set('signer', {
        key: 'signer',
        display_name: 'Signer',
        color: ROLE_COLORS[0],
      });
    }

    return Array.from(roleMap.values());
  }, [fields]);

  const [envelopeName, setEnvelopeName] = useState(document.name);
  const [message, setMessage] = useState('');
  const [roles, setRoles] = useState<RoleInput[]>(detectedRoles);
  const [recipients, setRecipients] = useState<RecipientInput[]>(() => [
    { id: '1', email: '', name: '', role_key: detectedRoles[0]?.key || 'signer' },
  ]);
  const [senderVariables, setSenderVariables] = useState<Record<string, string>>({});
  const [sending, setSending] = useState(false);

  // Get sender fields that need values
  const senderFields = fields.filter(
    (f) => (f.assignee_type === AssigneeType.SENDER || f.owner === FieldOwner.SENDER) && f.sender_variable_key
  );

  const addRole = () => {
    const newIndex = roles.length + 1;
    const colorIndex = roles.length % ROLE_COLORS.length;
    setRoles([
      ...roles,
      {
        key: `signer_${newIndex}`,
        display_name: `Signer ${newIndex}`,
        color: ROLE_COLORS[colorIndex],
      },
    ]);
  };

  const removeRole = (key: string) => {
    setRoles(roles.filter((r) => r.key !== key));
    // Update recipients that had this role
    setRecipients(recipients.map((r) =>
      r.role_key === key ? { ...r, role_key: roles[0]?.key || 'signer' } : r
    ));
  };

  const updateRole = (key: string, updates: Partial<RoleInput>) => {
    setRoles(roles.map((r) => (r.key === key ? { ...r, ...updates } : r)));
  };

  const addRecipient = () => {
    setRecipients([
      ...recipients,
      {
        id: Date.now().toString(),
        email: '',
        name: '',
        role_key: roles[0]?.key || 'signer',
      },
    ]);
  };

  const removeRecipient = (id: string) => {
    setRecipients(recipients.filter((r) => r.id !== id));
  };

  const updateRecipient = (id: string, updates: Partial<RecipientInput>) => {
    setRecipients(
      recipients.map((r) => (r.id === id ? { ...r, ...updates } : r))
    );
  };

  const handleSend = async () => {
    // Validate
    if (!envelopeName.trim()) {
      toast.error('Please enter an envelope name');
      return;
    }

    if (recipients.length === 0) {
      toast.error('Please add at least one recipient');
      return;
    }

    for (const recipient of recipients) {
      if (!recipient.email || !recipient.name) {
        toast.error('Please fill in all recipient details');
        return;
      }
    }

    // Check sender variables
    for (const field of senderFields) {
      if (field.sender_variable_key && !senderVariables[field.sender_variable_key]) {
        toast.error(`Please provide a value for "${field.sender_variable_key}"`);
        return;
      }
    }

    setSending(true);
    try {
      // Create envelope with roles
      const envelope = await envelopesApi.create(
        {
          document_id: document.id,
          name: envelopeName,
          message: message || undefined,
          roles: roles.map((r) => ({
            key: r.key,
            display_name: r.display_name,
            color: r.color,
          })),
          recipients: recipients.map((r) => ({
            email: r.email,
            name: r.name,
            role_key: r.role_key,
          })),
          sender_variables: Object.keys(senderVariables).length > 0 ? senderVariables : undefined,
        },
        token
      );

      // Send the envelope
      await envelopesApi.send(envelope.id, senderVariables, token);

      toast.success('Document sent for signing!');
      onSent(envelope.id);
    } catch (error) {
      toast.error('Failed to send document');
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b flex items-center justify-between">
          <h2 className="text-xl font-semibold">Send for Signing</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* Envelope Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Envelope Name
            </label>
            <input
              type="text"
              value={envelopeName}
              onChange={(e) => setEnvelopeName(e.target.value)}
              className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>

          {/* Message */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Message to Recipients (optional)
            </label>
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              rows={3}
              placeholder="Please review and sign this document..."
              className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>

          {/* Roles */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-gray-700">
                Signer Roles
              </label>
              <button
                onClick={addRole}
                className="text-sm text-primary-600 hover:text-primary-700 flex items-center gap-1"
              >
                <Plus className="w-4 h-4" />
                Add Role
              </button>
            </div>

            <div className="flex flex-wrap gap-2 mb-3">
              {roles.map((role) => (
                <div
                  key={role.key}
                  className="flex items-center gap-2 px-3 py-1.5 rounded-full border"
                  style={{ backgroundColor: `${role.color}20`, borderColor: role.color }}
                >
                  <span
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: role.color }}
                  />
                  <input
                    type="text"
                    value={role.display_name}
                    onChange={(e) => updateRole(role.key, { display_name: e.target.value })}
                    className="bg-transparent text-sm font-medium outline-none w-24"
                    style={{ color: role.color }}
                  />
                  {roles.length > 1 && (
                    <button
                      onClick={() => removeRole(role.key)}
                      className="text-gray-400 hover:text-red-500"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Recipients */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-gray-700">
                Recipients
              </label>
              <button
                onClick={addRecipient}
                className="text-sm text-primary-600 hover:text-primary-700 flex items-center gap-1"
              >
                <Plus className="w-4 h-4" />
                Add Recipient
              </button>
            </div>

            <div className="space-y-3">
              {recipients.map((recipient, index) => (
                <div
                  key={recipient.id}
                  className="flex items-start gap-3 p-3 border rounded-lg"
                >
                  <div className="flex-1 grid grid-cols-3 gap-3">
                    <div>
                      <label className="block text-xs text-gray-500 mb-1">Name</label>
                      <input
                        type="text"
                        value={recipient.name}
                        onChange={(e) =>
                          updateRecipient(recipient.id, { name: e.target.value })
                        }
                        placeholder="John Doe"
                        className="w-full px-3 py-1.5 border rounded focus:outline-none focus:ring-2 focus:ring-primary-500"
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-gray-500 mb-1">Email</label>
                      <input
                        type="email"
                        value={recipient.email}
                        onChange={(e) =>
                          updateRecipient(recipient.id, { email: e.target.value })
                        }
                        placeholder="john@example.com"
                        className="w-full px-3 py-1.5 border rounded focus:outline-none focus:ring-2 focus:ring-primary-500"
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-gray-500 mb-1">Role</label>
                      <select
                        value={recipient.role_key}
                        onChange={(e) =>
                          updateRecipient(recipient.id, { role_key: e.target.value })
                        }
                        className="w-full px-3 py-1.5 border rounded focus:outline-none focus:ring-2 focus:ring-primary-500"
                      >
                        {roles.map((role) => (
                          <option key={role.key} value={role.key}>
                            {role.display_name}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                  {recipients.length > 1 && (
                    <button
                      onClick={() => removeRecipient(recipient.id)}
                      className="text-gray-400 hover:text-red-500 mt-5"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Sender Variables */}
          {senderFields.length > 0 && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Sender Variables
              </label>
              <p className="text-sm text-gray-500 mb-3">
                These values will be visible to signers but cannot be edited by them.
              </p>
              <div className="space-y-3">
                {senderFields.map((field) => (
                  <div key={field.id}>
                    <label className="block text-xs text-gray-500 mb-1">
                      {field.sender_variable_key}
                    </label>
                    <input
                      type="text"
                      value={senderVariables[field.sender_variable_key!] || ''}
                      onChange={(e) =>
                        setSenderVariables({
                          ...senderVariables,
                          [field.sender_variable_key!]: e.target.value,
                        })
                      }
                      placeholder={`Enter ${field.sender_variable_key}`}
                      className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                    />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Summary */}
          <div className="bg-gray-50 p-4 rounded-lg">
            <h4 className="text-sm font-medium text-gray-700 mb-2">Summary</h4>
            <ul className="text-sm text-gray-600 space-y-1">
              <li>Document: {document.name}</li>
              <li>Total fields: {fields.length}</li>
              <li>Roles: {roles.map((r) => r.display_name).join(', ')}</li>
              <li>Recipients: {recipients.length}</li>
            </ul>
          </div>
        </div>

        <div className="p-6 border-t flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 border rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSend}
            disabled={sending}
            className="flex-1 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 transition-colors"
          >
            {sending ? 'Sending...' : 'Send for Signing'}
          </button>
        </div>
      </div>
    </div>
  );
}
