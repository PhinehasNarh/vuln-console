import { useEffect, useMemo, useRef, useState } from "react";

export interface PaletteAction {
  id: string;
  label: string;
  hint?: string;
  run: () => void;
}

export function CommandPalette({
  actions,
  onClose,
}: {
  actions: PaletteAction[];
  onClose: () => void;
}) {
  const [filter, setFilter] = useState("");
  const [active, setActive] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const visible = useMemo(() => {
    const needle = filter.trim().toLowerCase();
    if (!needle) return actions;
    return actions.filter((action) => action.label.toLowerCase().includes(needle));
  }, [actions, filter]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  useEffect(() => {
    setActive(0);
  }, [filter]);

  function execute(index: number) {
    const action = visible[index];
    if (!action) return;
    onClose();
    action.run();
  }

  return (
    <div className="palette-overlay" onClick={onClose}>
      <div
        className="palette"
        role="dialog"
        aria-modal="true"
        aria-label="Command palette"
        onClick={(event) => event.stopPropagation()}
      >
        <input
          ref={inputRef}
          value={filter}
          onChange={(event) => setFilter(event.target.value)}
          placeholder="type a command"
          aria-label="Search commands"
          onKeyDown={(event) => {
            if (event.key === "ArrowDown") {
              event.preventDefault();
              setActive((current) => Math.min(visible.length - 1, current + 1));
            } else if (event.key === "ArrowUp") {
              event.preventDefault();
              setActive((current) => Math.max(0, current - 1));
            } else if (event.key === "Enter") {
              event.preventDefault();
              execute(active);
            } else if (event.key === "Escape") {
              onClose();
            }
          }}
        />
        <ul role="listbox" aria-label="Commands">
          {visible.length === 0 && <li className="palette-empty">no matching commands</li>}
          {visible.map((action, index) => (
            <li
              key={action.id}
              role="option"
              aria-selected={index === active}
              className={index === active ? "active" : undefined}
              onMouseEnter={() => setActive(index)}
              onClick={() => execute(index)}
            >
              <span>{action.label}</span>
              {action.hint && <kbd>{action.hint}</kbd>}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
