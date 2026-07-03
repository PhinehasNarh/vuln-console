import { useState, type FormEvent } from "react";

import { openAuditReport } from "./api";

function isoDaysAgo(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

export function ReportDialog({ onClose }: { onClose: () => void }) {
  const [since, setSince] = useState(() => isoDaysAgo(30));
  const [until, setUntil] = useState(() => today());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await openAuditReport(since, until);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not generate report");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="palette-overlay" onClick={onClose}>
      <div
        className="report-dialog"
        role="dialog"
        aria-modal="true"
        aria-label="Export audit report"
        onClick={(event) => event.stopPropagation()}
      >
        <h2>Export audit report</h2>
        <p className="muted small-text">
          A branded, confidential report for the selected period: executive summary, findings,
          and the incident timeline. Opens in a new tab; print to PDF from there.
        </p>
        <form onSubmit={submit}>
          <label>
            from
            <input type="date" value={since} max={until} onChange={(e) => setSince(e.target.value)} />
          </label>
          <label>
            to
            <input type="date" value={until} min={since} max={today()} onChange={(e) => setUntil(e.target.value)} />
          </label>
          {error && <p className="error">{error}</p>}
          <div className="report-actions">
            <button type="button" className="ghost small" onClick={onClose}>
              cancel
            </button>
            <button type="submit" className="primary small" disabled={busy}>
              {busy ? "generating" : "generate report"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
