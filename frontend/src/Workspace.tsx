import { useQuery } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { listFindings } from "./api";
import { CommandBar } from "./CommandBar";
import { CommandPalette, type PaletteAction } from "./CommandPalette";
import { FindingsTable } from "./FindingsTable";
import { Inspector } from "./Inspector";
import { UploadSheet } from "./UploadSheet";

interface WorkspaceProps {
  theme: "dark" | "light";
  onToggleTheme: () => void;
  onSignOut: () => void;
}

export function Workspace({ theme, onToggleTheme, onSignOut }: WorkspaceProps) {
  const [repository, setRepository] = useState("");
  const [severity, setSeverity] = useState("");
  const [cursor, setCursor] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const searchRef = useRef<HTMLInputElement>(null);

  const params = useMemo(() => {
    const search = new URLSearchParams();
    if (severity) search.set("severity", severity);
    if (repository) search.set("repository", repository);
    if (cursor) search.set("cursor", cursor);
    return search;
  }, [severity, repository, cursor]);

  const query = useQuery({
    queryKey: ["findings", severity, repository, cursor],
    queryFn: () => listFindings(params),
  });
  const rows = useMemo(() => query.data?.data ?? [], [query.data]);

  const moveSelection = useCallback(
    (delta: number) => {
      if (rows.length === 0) return;
      const index = rows.findIndex((row) => row.id === selectedId);
      const next = index === -1 ? (delta > 0 ? 0 : rows.length - 1) : index + delta;
      const clamped = Math.max(0, Math.min(rows.length - 1, next));
      setSelectedId(rows[clamped].id);
    },
    [rows, selectedId],
  );

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setPaletteOpen((open) => !open);
        return;
      }
      const target = event.target as HTMLElement;
      const inField = ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName);
      if (inField) {
        if (event.key === "Escape") (target as HTMLInputElement).blur();
        return;
      }
      if (paletteOpen) return; // the palette handles its own keys
      switch (event.key) {
        case "/":
          event.preventDefault();
          searchRef.current?.focus();
          break;
        case "j":
        case "ArrowDown":
          event.preventDefault();
          moveSelection(1);
          break;
        case "k":
        case "ArrowUp":
          event.preventDefault();
          moveSelection(-1);
          break;
        case "Escape":
          setSelectedId(null);
          setUploadOpen(false);
          break;
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [moveSelection, paletteOpen]);

  const resetPaging = useCallback(() => setCursor(null), []);

  const paletteActions: PaletteAction[] = useMemo(
    () => [
      { id: "search", label: "Focus repository search", hint: "/", run: () => searchRef.current?.focus() },
      { id: "upload", label: "Upload scan report", run: () => setUploadOpen(true) },
      {
        id: "sev-critical",
        label: "Filter severity: critical only",
        run: () => {
          resetPaging();
          setSeverity("critical");
        },
      },
      {
        id: "sev-high",
        label: "Filter severity: critical and high",
        run: () => {
          resetPaging();
          setSeverity("critical,high");
        },
      },
      {
        id: "clear",
        label: "Clear all filters",
        run: () => {
          resetPaging();
          setSeverity("");
          setRepository("");
        },
      },
      {
        id: "theme",
        label: `Switch to ${theme === "dark" ? "light" : "dark"} theme`,
        run: onToggleTheme,
      },
      { id: "signout", label: "Sign out", run: onSignOut },
    ],
    [theme, onToggleTheme, onSignOut, resetPaging],
  );

  return (
    <div className="shell">
      <a className="skip-link" href="#findings">
        Skip to findings
      </a>
      <CommandBar
        searchRef={searchRef}
        repository={repository}
        onRepositoryChange={(value) => {
          resetPaging();
          setRepository(value);
        }}
        onUpload={() => setUploadOpen((open) => !open)}
        onToggleTheme={onToggleTheme}
        onSignOut={onSignOut}
        onPalette={() => setPaletteOpen(true)}
      />
      {uploadOpen && (
        <UploadSheet
          onClose={() => setUploadOpen(false)}
          onUploaded={() => {
            void query.refetch();
          }}
        />
      )}
      <main className="workspace" id="findings">
        <section className="table-pane">
          <div className="toolbar">
            <span aria-live="polite" className="result-count">
              {query.data
                ? `${rows.length}${query.data.pagination.has_more ? "+" : ""} findings`
                : "loading"}
            </span>
            <select
              aria-label="Severity filter"
              value={severity}
              onChange={(event) => {
                resetPaging();
                setSeverity(event.target.value);
              }}
            >
              <option value="">all severities</option>
              <option value="critical">critical</option>
              <option value="critical,high">critical + high</option>
              <option value="medium">medium</option>
              <option value="low,info">low + info</option>
            </select>
            {(severity || repository || cursor) && (
              <button
                className="ghost small"
                onClick={() => {
                  resetPaging();
                  setSeverity("");
                  setRepository("");
                }}
              >
                clear
              </button>
            )}
            <span className="spacer" />
            {cursor && (
              <button className="ghost small" onClick={resetPaging}>
                back to start
              </button>
            )}
            {query.data?.pagination.has_more && (
              <button
                className="ghost small"
                onClick={() => setCursor(query.data.pagination.next_cursor)}
              >
                next page
              </button>
            )}
          </div>
          <FindingsTable
            rows={rows}
            loading={query.isLoading}
            error={query.isError ? (query.error as Error).message : null}
            selectedId={selectedId}
            onSelect={setSelectedId}
          />
        </section>
        {selectedId && <Inspector findingId={selectedId} onClose={() => setSelectedId(null)} />}
      </main>
      {paletteOpen && (
        <CommandPalette actions={paletteActions} onClose={() => setPaletteOpen(false)} />
      )}
    </div>
  );
}
