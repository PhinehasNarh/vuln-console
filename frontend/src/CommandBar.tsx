import type { RefObject } from "react";

interface CommandBarProps {
  searchRef: RefObject<HTMLInputElement>;
  repository: string;
  onRepositoryChange: (value: string) => void;
  onUpload: () => void;
  onToggleTheme: () => void;
  onSignOut: () => void;
  onPalette: () => void;
  onReport: () => void;
}

export function CommandBar({
  searchRef,
  repository,
  onRepositoryChange,
  onUpload,
  onToggleTheme,
  onSignOut,
  onPalette,
  onReport,
}: CommandBarProps) {
  return (
    <header className="command-bar">
      <div className="brand">
        <span className="brand-mark" aria-hidden="true" />
        <span className="brand-name">Vulnerability Console</span>
      </div>
      <div className="bar-search">
        <input
          ref={searchRef}
          value={repository}
          onChange={(event) => onRepositoryChange(event.target.value)}
          placeholder="filter by repository"
          aria-label="Filter findings by repository"
        />
        <kbd>/</kbd>
      </div>
      <nav className="bar-actions" aria-label="Workspace actions">
        <button className="ghost small" onClick={onPalette} title="Command palette (Ctrl+K)">
          commands <kbd>ctrl k</kbd>
        </button>
        <button className="ghost small" onClick={onReport}>
          export report
        </button>
        <button className="primary small" onClick={onUpload}>
          upload report
        </button>
        <button className="ghost small" onClick={onToggleTheme} title="Toggle theme">
          theme
        </button>
        <button className="ghost small" onClick={onSignOut}>
          sign out
        </button>
      </nav>
    </header>
  );
}
