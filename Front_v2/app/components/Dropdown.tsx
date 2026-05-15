import { useState, useRef, useEffect } from 'react';
import { ChevronDown } from 'lucide-react';

interface DropdownOption {
  value: string;
  label: string;
  icon?: string;
}

interface DropdownProps {
  options: DropdownOption[];
  value: string;
  onChange: (value: string) => void;
  label?: string;
}

export default function Dropdown({ options, value, onChange, label }: DropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const selectedOption = options.find((opt) => opt.value === value);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div ref={dropdownRef} className="relative">
      {label && (
        <div style={{ fontSize: '12px', lineHeight: '16px', color: 'var(--text-tertiary)', marginBottom: '4px' }}>
          {label}
        </div>
      )}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-4 py-2 rounded-lg transition-all duration-150 w-full sm:w-auto"
        style={{
          backgroundColor: 'var(--bg-elev-1)',
          border: '1px solid var(--border-default)',
          color: 'var(--text-primary)',
          fontSize: '14px',
          fontWeight: 700,
          minWidth: '140px',
        }}
      >
        {selectedOption?.icon && <span>{selectedOption.icon}</span>}
        <span className="flex-1 text-left">{selectedOption?.label}</span>
        <ChevronDown
          size={16}
          style={{
            color: 'var(--text-tertiary)',
            transform: isOpen ? 'rotate(180deg)' : 'rotate(0)',
            transition: 'transform 120ms ease-out',
          }}
        />
      </button>

      {isOpen && (
        <div
          className="absolute top-full left-0 mt-2 rounded-lg overflow-hidden z-50"
          style={{
            backgroundColor: 'var(--bg-base)',
            border: '1px solid var(--border-default)',
            boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
            minWidth: '100%',
          }}
        >
          {options.map((option) => (
            <button
              key={option.value}
              onClick={() => {
                onChange(option.value);
                setIsOpen(false);
              }}
              className={`flex items-center gap-2 w-full px-4 py-2 transition-colors duration-150 ${
                option.value === value
                  ? 'bg-[var(--bg-elev-1)]'
                  : 'hover:bg-[var(--bg-elev-1)]'
              }`}
              style={{
                color: 'var(--text-primary)',
                fontSize: '14px',
                fontWeight: option.value === value ? 700 : 400,
              }}
            >
              {option.icon && <span>{option.icon}</span>}
              <span>{option.label}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
