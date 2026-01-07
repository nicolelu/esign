/**
 * Utility functions.
 */

import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(date: string | Date): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  return d.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

export function getFieldTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    TEXT: 'Text',
    NAME: 'Name',
    EMAIL: 'Email',
    DATE_SIGNED: 'Date Signed',
    CHECKBOX: 'Checkbox',
    SIGNATURE: 'Signature',
    INITIALS: 'Initials',
  };
  return labels[type] || type;
}

// DEPRECATED: Use getRoleLabel/getRoleColor instead for N-signer support
export function getOwnerLabel(owner: string): string {
  const labels: Record<string, string> = {
    SENDER: 'Sender',
    SIGNER_1: 'Signer 1',
    SIGNER_2: 'Signer 2',
  };
  return labels[owner] || owner;
}

// DEPRECATED: Use getRoleLabel/getRoleColor instead for N-signer support
export function getOwnerColor(owner: string): string {
  const colors: Record<string, string> = {
    SENDER: 'bg-purple-100 border-purple-500 text-purple-700',
    SIGNER_1: 'bg-blue-100 border-blue-500 text-blue-700',
    SIGNER_2: 'bg-green-100 border-green-500 text-green-700',
  };
  return colors[owner] || 'bg-gray-100 border-gray-500 text-gray-700';
}

// NEW: Role-based label and color functions

const DEFAULT_ROLE_COLORS: Record<string, string> = {
  sender: 'bg-purple-100 border-purple-500 text-purple-700',
  client: 'bg-blue-100 border-blue-500 text-blue-700',
  contractor: 'bg-green-100 border-green-500 text-green-700',
  company: 'bg-violet-100 border-violet-500 text-violet-700',
  employee: 'bg-cyan-100 border-cyan-500 text-cyan-700',
  landlord: 'bg-amber-100 border-amber-500 text-amber-700',
  tenant: 'bg-pink-100 border-pink-500 text-pink-700',
  witness: 'bg-gray-100 border-gray-500 text-gray-700',
  guarantor: 'bg-orange-100 border-orange-500 text-orange-700',
  signer_1: 'bg-blue-100 border-blue-500 text-blue-700',
  signer_2: 'bg-green-100 border-green-500 text-green-700',
  signer: 'bg-blue-100 border-blue-500 text-blue-700',
};

export function getRoleLabel(roleKey: string, displayName?: string): string {
  if (displayName) return displayName;

  // Convert role_key to Title Case
  return roleKey
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

export function getRoleColor(roleKey: string, customColor?: string): string {
  if (customColor) {
    // Convert hex color to tailwind-like classes
    return `border-2`;
  }
  return DEFAULT_ROLE_COLORS[roleKey.toLowerCase()] || 'bg-gray-100 border-gray-500 text-gray-700';
}

export function getRoleColorStyle(customColor?: string): React.CSSProperties {
  if (customColor) {
    return {
      backgroundColor: `${customColor}20`,
      borderColor: customColor,
      color: customColor,
    };
  }
  return {};
}

export function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    DRAFT: 'bg-gray-100 text-gray-700',
    SENT: 'bg-blue-100 text-blue-700',
    IN_PROGRESS: 'bg-yellow-100 text-yellow-700',
    COMPLETED: 'bg-green-100 text-green-700',
    VOIDED: 'bg-red-100 text-red-700',
    EXPIRED: 'bg-orange-100 text-orange-700',
    PENDING: 'bg-gray-100 text-gray-700',
    VIEWED: 'bg-blue-100 text-blue-700',
    SIGNING: 'bg-yellow-100 text-yellow-700',
    DECLINED: 'bg-red-100 text-red-700',
  };
  return colors[status] || 'bg-gray-100 text-gray-700';
}

export function getConfidenceColor(confidence: number | null): string {
  if (confidence === null) return 'text-gray-400';
  if (confidence >= 0.8) return 'text-green-600';
  if (confidence >= 0.6) return 'text-yellow-600';
  return 'text-red-600';
}

export function formatConfidence(confidence: number | null): string {
  if (confidence === null) return 'N/A';
  return `${Math.round(confidence * 100)}%`;
}
