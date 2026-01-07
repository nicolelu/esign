'use client';

import { useState, useRef } from 'react';
import { cn, getOwnerColor, getFieldTypeLabel } from '@/lib/utils';
import type { Field, BoundingBox } from '@/types';

interface FieldOverlayProps {
  field: Field;
  isSelected: boolean;
  onClick: () => void;
  onUpdate: (updates: { bbox: BoundingBox }) => void;
}

export default function FieldOverlay({
  field,
  isSelected,
  onClick,
  onUpdate,
}: FieldOverlayProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [isResizing, setIsResizing] = useState<string | null>(null);
  const [dragStart, setDragStart] = useState<{ x: number; y: number } | null>(null);
  const [initialBbox, setInitialBbox] = useState<BoundingBox | null>(null);
  const elementRef = useRef<HTMLDivElement>(null);

  const ownerColorClass = getOwnerColor(field.owner);

  const handleMouseDown = (e: React.MouseEvent) => {
    e.stopPropagation();
    onClick();

    if (!isSelected) return;

    setIsDragging(true);
    setDragStart({ x: e.clientX, y: e.clientY });
    setInitialBbox(field.bbox);
  };

  const handleResizeStart = (e: React.MouseEvent, handle: string) => {
    e.stopPropagation();
    setIsResizing(handle);
    setDragStart({ x: e.clientX, y: e.clientY });
    setInitialBbox(field.bbox);
  };

  const handleMouseMove = (e: MouseEvent) => {
    if (!dragStart || !initialBbox) return;

    const dx = e.clientX - dragStart.x;
    const dy = e.clientY - dragStart.y;

    if (isDragging) {
      onUpdate({
        bbox: {
          ...initialBbox,
          x: initialBbox.x + dx,
          y: initialBbox.y + dy,
        },
      });
    } else if (isResizing) {
      let newBbox = { ...initialBbox };

      if (isResizing.includes('e')) {
        newBbox.width = Math.max(20, initialBbox.width + dx);
      }
      if (isResizing.includes('w')) {
        newBbox.x = initialBbox.x + dx;
        newBbox.width = Math.max(20, initialBbox.width - dx);
      }
      if (isResizing.includes('s')) {
        newBbox.height = Math.max(10, initialBbox.height + dy);
      }
      if (isResizing.includes('n')) {
        newBbox.y = initialBbox.y + dy;
        newBbox.height = Math.max(10, initialBbox.height - dy);
      }

      onUpdate({ bbox: newBbox });
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
    setIsResizing(null);
    setDragStart(null);
    setInitialBbox(null);
  };

  // Add global mouse listeners when dragging
  if (isDragging || isResizing) {
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  } else {
    document.removeEventListener('mousemove', handleMouseMove);
    document.removeEventListener('mouseup', handleMouseUp);
  }

  return (
    <div
      ref={elementRef}
      className={cn(
        'field-overlay',
        ownerColorClass,
        isSelected && 'selected'
      )}
      style={{
        left: field.bbox.x,
        top: field.bbox.y,
        width: field.bbox.width,
        height: field.bbox.height,
        cursor: isSelected ? 'move' : 'pointer',
      }}
      onMouseDown={handleMouseDown}
    >
      {/* Field type label */}
      <div
        className="absolute -top-5 left-0 text-xs whitespace-nowrap px-1 rounded"
        style={{ fontSize: '10px' }}
      >
        {getFieldTypeLabel(field.field_type)}
        {field.required && <span className="text-red-500 ml-0.5">*</span>}
      </div>

      {/* Resize handles (only when selected) */}
      {isSelected && (
        <>
          <div
            className="resize-handle nw"
            onMouseDown={(e) => handleResizeStart(e, 'nw')}
          />
          <div
            className="resize-handle ne"
            onMouseDown={(e) => handleResizeStart(e, 'ne')}
          />
          <div
            className="resize-handle sw"
            onMouseDown={(e) => handleResizeStart(e, 'sw')}
          />
          <div
            className="resize-handle se"
            onMouseDown={(e) => handleResizeStart(e, 'se')}
          />
        </>
      )}
    </div>
  );
}
