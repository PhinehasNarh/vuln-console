import type { Finding } from "./api";

interface FindingsTableProps {
  rows: Finding[];
  loading: boolean;
  error: string | null;
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export function SeverityChip({ severity }: { severity: string }) {
  return <span className={`chip sev-${severity}`}>{severity}</span>;
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
        <p className="error">{error}</p>
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
                {Array.from({ length: 6 }, (_, cell) => (
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
              <td>{finding.repository}</td>
              <td className="mono location-cell">
                {finding.file_path ?? "-"}
                {finding.line !== null ? `:${finding.line}` : ""}
              </td>
              <td className="muted">{finding.tool_names.join(", ")}</td>
              <td className="muted nums">{timeFormat.format(new Date(finding.last_seen))}</td>
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
        <th scope="col">last seen</th>
      </tr>
    </thead>
  );
}
