import { useEffect, useRef, useState } from 'react';
import { DelayedTooltip } from '../ui/DelayedTooltip';

export interface SelectOption {
  value: string;
  label: string;
  help?: string;
}

interface Props {
  value: string;
  onChange: (value: string) => void;
  options: SelectOption[];
  disabled?: boolean;
  className?: string;
}

export function SelectWithHelp({ value, onChange, options, disabled, className = '' }: Props) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  const selected = options.find((o) => o.value === value) ?? options[0];

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, [open]);

  return (
    <div ref={rootRef} className={`relative ${className}`}>
      <DelayedTooltip content={selected?.help ?? ''} disabled={disabled}>
        <button
          type="button"
          disabled={disabled}
          onClick={() => setOpen((o) => !o)}
          className="w-full text-left px-2 py-1 rounded border border-default bg-input text-xs text-primary disabled:opacity-50"
        >
          {selected?.label ?? value}
        </button>
      </DelayedTooltip>
      {open && !disabled && (
        <ul className="absolute z-50 mt-1 w-full max-h-48 overflow-y-auto rounded border border-default bg-panel-solid shadow-lg">
          {options.map((o) => (
            <li key={o.value}>
              <DelayedTooltip content={o.help ?? ''}>
                <button
                  type="button"
                  className={`w-full text-left px-2 py-1.5 text-xs bg-hover ${
                    o.value === value ? 'text-accent-strong' : 'text-primary'
                  }`}
                  style={o.value === value ? { backgroundColor: 'var(--bg-tab-active)' } : undefined}
                  onClick={() => {
                    onChange(o.value);
                    setOpen(false);
                  }}
                >
                  {o.label}
                </button>
              </DelayedTooltip>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
