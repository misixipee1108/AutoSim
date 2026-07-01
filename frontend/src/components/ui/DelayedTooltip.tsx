import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react';
import { createPortal } from 'react-dom';

interface Props {
  content: string;
  delayMs?: number;
  children: ReactNode;
  disabled?: boolean;
}

export function DelayedTooltip({ content, delayMs = 600, children, disabled }: Props) {
  const [visible, setVisible] = useState(false);
  const [pos, setPos] = useState({ top: 0, left: 0 });
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const anchorRef = useRef<HTMLSpanElement>(null);

  const clearTimer = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const hide = useCallback(() => {
    clearTimer();
    setVisible(false);
  }, [clearTimer]);

  const show = useCallback(() => {
    if (disabled || !content.trim()) return;
    const el = anchorRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    setPos({ top: rect.bottom + 6, left: rect.left });
    setVisible(true);
  }, [content, disabled]);

  const onEnter = useCallback(() => {
    clearTimer();
    timerRef.current = setTimeout(show, delayMs);
  }, [clearTimer, delayMs, show]);

  useEffect(() => () => clearTimer(), [clearTimer]);

  return (
    <>
      <span
        ref={anchorRef}
        className="inline-flex w-full"
        onMouseEnter={onEnter}
        onMouseLeave={hide}
        onFocus={onEnter}
        onBlur={hide}
      >
        {children}
      </span>
      {visible && content.trim() && createPortal(
        <div
          role="tooltip"
          className="fixed z-[9999] max-w-xs rounded px-2 py-1.5 text-[11px] leading-relaxed shadow-lg pointer-events-none tooltip-popup"
          style={{ top: pos.top, left: pos.left }}
        >
          {content}
        </div>,
        document.body,
      )}
    </>
  );
}
