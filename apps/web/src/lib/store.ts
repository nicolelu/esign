/**
 * Zustand store for global state management.
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

import type { Document, Field, User } from '@/types';

interface AuthState {
  token: string | null;
  user: User | null;
  setToken: (token: string | null) => void;
  setUser: (user: User | null) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      setToken: (token) => set({ token }),
      setUser: (user) => set({ user }),
      logout: () => set({ token: null, user: null }),
    }),
    {
      name: 'auth-storage',
    }
  )
);

interface EditorState {
  currentDocument: Document | null;
  fields: Field[];
  selectedFieldId: string | null;
  currentPage: number;
  zoom: number;
  isDrawing: boolean;
  drawingFieldType: string | null;
  setCurrentDocument: (doc: Document | null) => void;
  setFields: (fields: Field[]) => void;
  addField: (field: Field) => void;
  updateField: (fieldId: string, updates: Partial<Field>) => void;
  removeField: (fieldId: string) => void;
  setSelectedFieldId: (id: string | null) => void;
  setCurrentPage: (page: number) => void;
  setZoom: (zoom: number) => void;
  setIsDrawing: (isDrawing: boolean) => void;
  setDrawingFieldType: (type: string | null) => void;
  reset: () => void;
}

const initialEditorState = {
  currentDocument: null,
  fields: [],
  selectedFieldId: null,
  currentPage: 1,
  zoom: 1,
  isDrawing: false,
  drawingFieldType: null,
};

export const useEditorStore = create<EditorState>()((set) => ({
  ...initialEditorState,
  setCurrentDocument: (doc) => set({ currentDocument: doc }),
  setFields: (fields) => set({ fields }),
  addField: (field) => set((state) => ({ fields: [...state.fields, field] })),
  updateField: (fieldId, updates) =>
    set((state) => ({
      fields: state.fields.map((f) =>
        f.id === fieldId ? { ...f, ...updates } : f
      ),
    })),
  removeField: (fieldId) =>
    set((state) => ({
      fields: state.fields.filter((f) => f.id !== fieldId),
      selectedFieldId:
        state.selectedFieldId === fieldId ? null : state.selectedFieldId,
    })),
  setSelectedFieldId: (id) => set({ selectedFieldId: id }),
  setCurrentPage: (page) => set({ currentPage: page }),
  setZoom: (zoom) => set({ zoom }),
  setIsDrawing: (isDrawing) => set({ isDrawing }),
  setDrawingFieldType: (type) => set({ drawingFieldType: type }),
  reset: () => set(initialEditorState),
}));
