import type { RefObject } from "react";

import {
  CommandIcon,
  MoonIcon,
  ReportIcon,
  SearchIcon,
  ShieldIcon,
  SignOutIcon,
  SunIcon,
  UploadIcon,
} from "./Icons";

interface CommandBarProps {
  searchRef: RefObject<HTMLInputElement>;
  repository: string;
  theme: "dark" | "light";
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
  theme,
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
        <span className="brand-mark" aria-hidden="true">
          <ShieldIcon />
        </span>
        <span className="brand-text">
          <span className="brand-name">Vulnerability Console</span>
          <span className="brand-sub">triage</span>
        </span>
      </div>
      <div className="bar-search">
        <SearchIcon className="search-icon" />
        <input
          ref={searchRef}
          value={repository}
          onChange={(event) => onRepositoryChange(event.target.value)}
          placeholder="filter by repository"
          aria-label="Filter findings by repository"
        />
        <kbd aria-hidden="true">/</kbd>
      </div>
      <nav className="bar-actions" aria-label="Workspace actions">
        <button
          className="ghost small command-trigger"
          onClick={onPalette}
          title="Command palette (Ctrl+K)"
        >
          <CommandIcon />
          commands
          <kbd aria-hidden="true">ctrl k</kbd>
        </button>
        <button className="ghost small command-trigger" onClick={onReport}>
          <ReportIcon />
          export report
        </button>
        <button className="primary small command-trigger" onClick={onUpload}>
          <UploadIcon />
          upload report
        </button>
        <span className="bar-divider" aria-hidden="true" />
        <button
          className="icon-button"
          onClick={onToggleTheme}
          title={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
          aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
        >
          {theme === "dark" ? <SunIcon /> : <MoonIcon />}
        </button>
        <button
          className="icon-button"
          onClick={onSignOut}
          title="Sign out"
          aria-label="Sign out"
        >
          <SignOutIcon />
        </button>
      </nav>
    </header>
  );
}
