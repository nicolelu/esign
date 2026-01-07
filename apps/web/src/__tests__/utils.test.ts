/**
 * Utility function tests
 */

import {
  cn,
  formatDate,
  formatFileSize,
  getFieldTypeLabel,
  getOwnerLabel,
  getOwnerColor,
  getStatusColor,
  formatConfidence,
  getRoleLabel,
  getRoleColor,
} from '@/lib/utils';

describe('cn utility', () => {
  it('should merge class names', () => {
    expect(cn('foo', 'bar')).toBe('foo bar');
  });

  it('should handle conditional classes', () => {
    expect(cn('foo', true && 'bar', false && 'baz')).toBe('foo bar');
  });

  it('should merge tailwind classes correctly', () => {
    expect(cn('p-2', 'p-4')).toBe('p-4');
  });
});

describe('formatFileSize', () => {
  it('should format bytes correctly', () => {
    expect(formatFileSize(0)).toBe('0 Bytes');
    expect(formatFileSize(500)).toBe('500 Bytes');
    expect(formatFileSize(1024)).toBe('1 KB');
    expect(formatFileSize(1024 * 1024)).toBe('1 MB');
    expect(formatFileSize(1024 * 1024 * 1024)).toBe('1 GB');
  });
});

describe('getFieldTypeLabel', () => {
  it('should return correct labels', () => {
    expect(getFieldTypeLabel('TEXT')).toBe('Text');
    expect(getFieldTypeLabel('SIGNATURE')).toBe('Signature');
    expect(getFieldTypeLabel('DATE_SIGNED')).toBe('Date Signed');
    expect(getFieldTypeLabel('CHECKBOX')).toBe('Checkbox');
  });

  it('should return input for unknown types', () => {
    expect(getFieldTypeLabel('UNKNOWN')).toBe('UNKNOWN');
  });
});

describe('getOwnerLabel', () => {
  it('should return correct labels', () => {
    expect(getOwnerLabel('SENDER')).toBe('Sender');
    expect(getOwnerLabel('SIGNER_1')).toBe('Signer 1');
    expect(getOwnerLabel('SIGNER_2')).toBe('Signer 2');
  });
});

describe('getOwnerColor', () => {
  it('should return color classes for owners', () => {
    expect(getOwnerColor('SENDER')).toContain('purple');
    expect(getOwnerColor('SIGNER_1')).toContain('blue');
    expect(getOwnerColor('SIGNER_2')).toContain('green');
  });
});

describe('getStatusColor', () => {
  it('should return color classes for statuses', () => {
    expect(getStatusColor('DRAFT')).toContain('gray');
    expect(getStatusColor('SENT')).toContain('blue');
    expect(getStatusColor('COMPLETED')).toContain('green');
    expect(getStatusColor('VOIDED')).toContain('red');
  });
});

describe('formatConfidence', () => {
  it('should format confidence as percentage', () => {
    expect(formatConfidence(0.5)).toBe('50%');
    expect(formatConfidence(0.85)).toBe('85%');
    expect(formatConfidence(1.0)).toBe('100%');
  });

  it('should handle null', () => {
    expect(formatConfidence(null)).toBe('N/A');
  });
});

describe('getRoleLabel', () => {
  it('should return display_name when provided', () => {
    expect(getRoleLabel('client', 'The Client')).toBe('The Client');
    expect(getRoleLabel('landlord', 'Property Owner')).toBe('Property Owner');
  });

  it('should convert role_key to title case when no display_name', () => {
    expect(getRoleLabel('client')).toBe('Client');
    expect(getRoleLabel('signer_1')).toBe('Signer 1');
    expect(getRoleLabel('witness_2')).toBe('Witness 2');
  });

  it('should handle single word role keys', () => {
    expect(getRoleLabel('buyer')).toBe('Buyer');
    expect(getRoleLabel('seller')).toBe('Seller');
  });
});

describe('getRoleColor', () => {
  it('should return default colors for known roles', () => {
    expect(getRoleColor('client')).toContain('blue');
    expect(getRoleColor('contractor')).toContain('green');
    expect(getRoleColor('company')).toContain('violet');
    expect(getRoleColor('sender')).toContain('purple');
  });

  it('should return gray for unknown roles', () => {
    expect(getRoleColor('unknown_role')).toContain('gray');
  });

  it('should be case insensitive', () => {
    expect(getRoleColor('CLIENT')).toContain('blue');
    expect(getRoleColor('Client')).toContain('blue');
  });

  it('should handle legacy signer_1 and signer_2 keys', () => {
    expect(getRoleColor('signer_1')).toContain('blue');
    expect(getRoleColor('signer_2')).toContain('green');
  });
});
