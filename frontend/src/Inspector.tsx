import { useQuery } from "@tanstack/react-query";

import { getFinding } from "./api";
import { SeverityChip } from "./FindingsTable";

const timeFormat = new Intl.DateTimeFormat(undefined, {
  year: "numeric",
  month: "short",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
});

export function Inspector({ findingId, onClose }: { findingId: string; onClose: () => void }) {
  const query = useQuery({
    queryKey: ["finding", findingId],
    queryFn: () => getFinding(findingId),
  });
  const finding = query.data;

  return (
    <aside className="inspector" aria-label="Finding details">
      <div className="inspector-head">
        <span className="inspector-kicker">finding</span>
        <button className="ghost small" onClick={onClose} aria-label="Close details">
          esc
        </button>
      </div>
      {query.isLoading && (
        <div className="inspector-body">
          <span className="skeleton wide" />
          <span className="skeleton" />
          <span className="skeleton" />
        </div>
      )}
      {query.isError && <p className="error">{(query.error as Error).message}</p>}
      {finding && (
        <div className="inspector-body">
          <div className="inspector-title">
            <SeverityChip severity={finding.severity} />
            <h2>{finding.title}</h2>
          </div>
          <dl className="meta-grid">
            <dt>status</dt>
            <dd>{finding.status}</dd>
            <dt>repository</dt>
            <dd>{finding.repository}</dd>
            <dt>rule</dt>
            <dd className="mono">{finding.rule_key}</dd>
            <dt>location</dt>
            <dd className="mono">
              {finding.file_path ?? "-"}
              {finding.line !== null ? `:${finding.line}` : ""}
            </dd>
            <dt>class</dt>
            <dd>{finding.finding_class}</dd>
            <dt>reported by</dt>
            <dd>{finding.tool_names.join(", ")}</dd>
            <dt>first seen</dt>
            <dd className="nums">{timeFormat.format(new Date(finding.first_seen))}</dd>
            <dt>last seen</dt>
            <dd className="nums">{timeFormat.format(new Date(finding.last_seen))}</dd>
            <dt>fingerprint</dt>
            <dd className="mono fingerprint" title={finding.fingerprint}>
              {finding.fingerprint.slice(0, 16)}...
            </dd>
          </dl>
          <section className="inspector-section">
            <h3>source scans</h3>
            <p className="muted small-text">
              Every raw scanner result that fed this canonical finding. Re-uploads land here
              instead of creating duplicates.
            </p>
            <ul className="source-list">
              {finding.sources.map((source) => (
                <li key={source.raw_finding_id}>
                  <span className="mono">{source.scan_id.slice(0, 8)}</span>
                  <span className="muted nums">
                    {timeFormat.format(new Date(source.created_at))}
                  </span>
                </li>
              ))}
            </ul>
          </section>
        </div>
      )}
    </aside>
  );
}
