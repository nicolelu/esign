/**
 * TypeScript types for the AI E-Sign application.
 */

export enum FieldType {
  TEXT = 'TEXT',
  NAME = 'NAME',
  EMAIL = 'EMAIL',
  DATE_SIGNED = 'DATE_SIGNED',
  CHECKBOX = 'CHECKBOX',
  SIGNATURE = 'SIGNATURE',
  INITIALS = 'INITIALS',
}

// DEPRECATED: Use AssigneeType + Role instead
export enum FieldOwner {
  SENDER = 'SENDER',
  SIGNER_1 = 'SIGNER_1',
  SIGNER_2 = 'SIGNER_2',
}

// NEW: N-signer assignee type
export enum AssigneeType {
  SENDER = 'SENDER',
  ROLE = 'ROLE',
}

export enum DocumentStatus {
  DRAFT = 'DRAFT',
  TEMPLATE = 'TEMPLATE',
  SENT = 'SENT',
  COMPLETED = 'COMPLETED',
  VOIDED = 'VOIDED',
}

export enum EnvelopeStatus {
  DRAFT = 'DRAFT',
  SENT = 'SENT',
  IN_PROGRESS = 'IN_PROGRESS',
  COMPLETED = 'COMPLETED',
  VOIDED = 'VOIDED',
  EXPIRED = 'EXPIRED',
}

export enum RecipientStatus {
  PENDING = 'PENDING',
  SENT = 'SENT',
  VIEWED = 'VIEWED',
  SIGNING = 'SIGNING',
  COMPLETED = 'COMPLETED',
  DECLINED = 'DECLINED',
}

export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

// NEW: Role interface for N-signer support
export interface Role {
  id: string;
  envelope_id: string;
  key: string;
  display_name: string;
  color: string;
  signing_order: number | null;
  created_at: string;
}

export interface RoleCreate {
  key: string;
  display_name: string;
  color?: string;
  signing_order?: number;
}

export interface User {
  id: string;
  email: string;
  name: string | null;
  is_active: boolean;
  created_at: string;
}

export interface Document {
  id: string;
  owner_id: string;
  name: string;
  original_filename: string;
  file_size: number;
  mime_type: string;
  page_count: number;
  status: DocumentStatus;
  created_at: string;
  updated_at: string;
}

export interface DocumentDetail extends Document {
  fields: Field[];
  page_images: string[] | null;
}

export interface Field {
  id: string;
  document_id: string;
  page_number: number;
  bbox: BoundingBox;
  field_type: FieldType;

  // DEPRECATED: Use assignee_type + role_id instead
  owner: FieldOwner | null;

  // NEW: N-signer assignee model
  assignee_type: AssigneeType;
  role_id: string | null;
  detected_role_key: string | null;

  required: boolean;
  label: string | null;
  placeholder: string | null;
  default_value: string | null;
  sender_variable_key: string | null;
  detection_confidence: number | null;
  classification_confidence: number | null;
  owner_confidence: number | null;
  role_confidence: number | null;
  evidence: string | null;
  created_at: string;
}

export interface FieldCreate {
  page_number: number;
  bbox: BoundingBox;
  field_type: FieldType;

  // DEPRECATED
  owner?: FieldOwner;

  // NEW
  assignee_type?: AssigneeType;
  role_key?: string;
  detected_role_key?: string;

  required?: boolean;
  label?: string;
  placeholder?: string;
  default_value?: string;
  sender_variable_key?: string;
}

export interface FieldUpdate {
  page_number?: number;
  bbox?: BoundingBox;
  field_type?: FieldType;

  // DEPRECATED
  owner?: FieldOwner;

  // NEW
  assignee_type?: AssigneeType;
  role_key?: string;

  required?: boolean;
  label?: string;
  placeholder?: string;
  default_value?: string;
  sender_variable_key?: string;
}

export interface Recipient {
  id: string;
  email: string;
  name: string;

  // DEPRECATED
  role: FieldOwner | null;

  // NEW: N-signer role reference
  role_id: string | null;
  role_info: Role | null;

  order: number;
  status: RecipientStatus;
  sent_at: string | null;
  viewed_at: string | null;
  completed_at: string | null;
}

export interface RecipientCreate {
  email: string;
  name: string;

  // DEPRECATED
  role?: FieldOwner;

  // NEW
  role_key?: string;
}

export interface Envelope {
  id: string;
  sender_id: string;
  document_id: string;
  name: string;
  message: string | null;
  status: EnvelopeStatus;
  sender_variables: Record<string, string> | null;
  sent_at: string | null;
  completed_at: string | null;
  created_at: string;

  // NEW: Roles defined for this envelope
  roles: Role[];

  recipients: Recipient[];
}

export interface EnvelopeDetail extends Envelope {
  document: Document;
  field_values: FieldValue[];
}

export interface EnvelopeCreate {
  document_id: string;
  name: string;
  message?: string;

  // NEW: Define roles for this envelope
  roles?: RoleCreate[];

  recipients: RecipientCreate[];
  sender_variables?: Record<string, string>;
}

export interface FieldValue {
  id: string;
  envelope_id: string;
  field_id: string;
  value: string | null;
  signature_data: string | null;

  // DEPRECATED
  filled_by_role: FieldOwner | null;

  // NEW
  filled_by_role_id: string | null;

  filled_at: string | null;
}

export interface FieldValueCreate {
  field_id: string;
  value?: string;
  signature_data?: string;
}

export interface SigningSession {
  envelope_id: string;
  document_name: string;
  recipient_name: string;

  // DEPRECATED
  recipient_role: FieldOwner | null;

  // NEW
  recipient_role_id: string | null;
  recipient_role_info: Role | null;

  fields: Field[];
  field_values: FieldValue[];
  sender_variables: Record<string, string> | null;
  page_images: string[];
  page_count: number;
}

export interface DetectedField {
  page_number: number;
  bbox: BoundingBox;
  field_type: FieldType;

  // DEPRECATED
  owner: FieldOwner | null;

  // NEW
  assignee_type: AssigneeType;
  detected_role_key: string | null;

  detection_confidence: number;
  classification_confidence: number;
  owner_confidence: number;
  role_confidence: number;
  evidence: string;
  label: string | null;
  suggested_placeholder: string | null;
}

export interface FieldDetectionResponse {
  document_id: string;
  detected_fields: DetectedField[];
  detection_time_ms: number;
  total_candidates: number;
  filtered_candidates: number;
}

export interface SigningLink {
  recipient_id: string;
  email: string;
  name: string;
  role: string;
  status: string;
  signing_url: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
}
