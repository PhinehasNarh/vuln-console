import type { Finding } from "./api";
import { AlertIcon, InboxIcon } from "./Icons";

interface FindingsTableProps {
  rows: Finding[];
  loading: boolean;
  error: string | null;
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export function SeverityChip({ severity }: { severity: string }) {
  return (
    <span className={`chip sev-${severity}`}>
      <span className="dot" aria-hidden="true" />
      {severity}
    </span>
  );
}

const STATUS_LABEL: Record<string, string> = {
  new: "new",
  triaged: "triaged",
  in_remediation: "in remediation",
  fixed: "fixed",
  risk_accepted: "risk accepted",
  false_positive: "false positive",
  suppressed: "suppressed",
  reopened: "reopened",
};

export function StatusChip({ status }: { status: string }) {
  return <span className={`chip status-${status}`}>{STATUS_LABEL[status] ?? status}</span>;
}

// Up to two initials from an owner handle, for the avatar beside an assignment.
export function initials(owner: string): string {
  const parts = owner
    .split(/[\s._@-]+/)
    .filter(Boolean)
    .slice(0, 2);
  if (parts.length === 0) return "?";
  return parts.map((part) => part[0]).join("");
}

const timeFormat = new Intl.DateTimeFormat(undefined, {
  month: "short",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
});

export function FindingsTable({ rows, loading, error, selectedId, onSelect }: FindingsTableProps) {
  if (error) {
    return (
      <div className="state-block">
        <span className="state-icon is-error" aria-hidden="true">
          <AlertIcon />
        </span>
        <p className="empty-title">Could not load findings.</p>
        <p className="empty-hint error">{error}</p>
      </div>
    );
  }
  if (loading) {
    return (
      <div className="table-scroll" aria-busy="true">
        <table className="findings">
          <TableHead />
          <tbody>
            {Array.from({ length: 8 }, (_, index) => (
              <tr key={index} className="skeleton-row">
                {Array.from({ length: 7 }, (_, cell) => (
                  <td key={cell}>
                    <span className="skeleton" />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }
  if (rows.length === 0) {
    return (
      <div className="state-block">
        <span className="state-icon" aria-hidden="true">
          <InboxIcon />
        </span>
        <p className="empty-title">No findings match this view.</p>
        <p className="empty-hint">Clear a filter, or upload a scan report to get started.</p>
      </div>
    );
  }
  return (
    <div className="table-scroll">
      <table className="findings">
        <TableHead />
        <tbody>
          {rows.map((finding) => (
            <tr
              key={finding.id}
              className={finding.id === selectedId ? "selected" : undefined}
              aria-selected={finding.id === selectedId}
              onClick={() => onSelect(finding.id)}
            >
              <td>
                <SeverityChip severity={finding.severity} />
              </td>
              <td className="title-cell">
                <span className="finding-title">{finding.title}</span>
                <span className="finding-rule mono">{finding.rule_key}</span>
              </td>
              <td className="repo-cell" title={finding.repository}>
                {finding.repository}
              </td>
              <td className="mono location-cell">
                {finding.package ??
                  `${finding.file_path ?? "-"}${finding.line !== null ? `:${finding.line}` : ""}`}
              </td>
              <td className="muted">{finding.tool_names.join(", ")}</td>
              <td>
                {finding.owner ? (
                  <span className="owner-tag">
                    <span className="avatar" aria-hidden="true">
                      {initials(finding.owner)}
                    </span>
                    {finding.owner}
                  </span>
                ) : (
                  <span className="muted">unassigned</span>
                )}
              </td>
              <td>
                {finding.sla_status === "overdue" && <span className="chip sla-overdue">overdue</span>}
                {finding.sla_status === "due_soon" && (
                  <span className="chip sla-due_soon">due soon</span>
                )}
                {(finding.sla_status === "on_track" || finding.sla_status === "none") && (
                  <span className="muted nums">{timeFormat.format(new Date(finding.last_seen))}</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function TableHead() {
  return (
    <thead>
      <tr>
        <th scope="col">severity</th>
        <th scope="col">finding</th>
        <th scope="col">repository</th>
        <th scope="col">location</th>
        <th scope="col">tools</th>
        <th scope="col">owner</th>
        <th scope="col">sla / last seen</th>
      </tr>
    </thead>
  );
}
