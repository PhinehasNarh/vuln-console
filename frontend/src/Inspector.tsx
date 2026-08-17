import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { assignFinding, getFinding, transitionFinding } from "./api";
import { initials, SeverityChip, StatusChip } from "./FindingsTable";
import { CloseIcon } from "./Icons";

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

const timeFormat = new Intl.DateTimeFormat(undefined, {
  year: "numeric",
  month: "short",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
});

const SLA_LABEL: Record<string, string> = {
  overdue: "overdue",
  due_soon: "due soon",
  on_track: "on track",
  none: "no SLA",
};

export function Inspector({ findingId, onClose }: { findingId: string; onClose: () => void }) {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["finding", findingId],
    queryFn: () => getFinding(findingId),
  });
  const finding = query.data;

  const [ownerDraft, setOwnerDraft] = useState("");
  useEffect(() => {
    setOwnerDraft(finding?.owner ?? "");
  }, [finding?.owner, findingId]);

  const assign = useMutation({
    mutationFn: (owner: string | null) => assignFinding(findingId, owner),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["finding", findingId] });
      void queryClient.invalidateQueries({ queryKey: ["findings"] });
    },
  });

  const [target, setTarget] = useState("");
  const [reason, setReason] = useState("");
  const [expiry, setExpiry] = useState("");
  useEffect(() => {
    setTarget("");
    setReason("");
    setExpiry("");
  }, [findingId]);

  const transition = useMutation({
    mutationFn: () =>
      transitionFinding(findingId, {
        status: target,
        reason: reason.trim(),
        risk_accepted_until:
          target === "risk_accepted" && expiry ? `${expiry}T23:59:59Z` : null,
      }),
    onSuccess: () => {
      setTarget("");
      setReason("");
      setExpiry("");
      void queryClient.invalidateQueries({ queryKey: ["finding", findingId] });
      void queryClient.invalidateQueries({ queryKey: ["findings"] });
    },
  });

  return (
    <aside className="inspector" aria-label="Finding details">
      <div className="inspector-head">
        <span className="inspector-kicker">finding</span>
        <button className="icon-button" onClick={onClose} aria-label="Close details" title="Close (Esc)">
          <CloseIcon />
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
            <dd>
              <StatusChip status={finding.status} />
            </dd>
            <dt>owner</dt>
            <dd>
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
            </dd>
            {finding.sla_status !== "none" && (
              <>
                <dt>sla</dt>
                <dd>
                  <span className={`chip sla-${finding.sla_status}`}>
                    {SLA_LABEL[finding.sla_status]}
                  </span>
                  {finding.sla_due_at && (
                    <span className="muted nums sla-due">
                      {" "}
                      due {timeFormat.format(new Date(finding.sla_due_at))}
                    </span>
                  )}
                </dd>
              </>
            )}
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
            {finding.package && (
              <>
                <dt>package</dt>
                <dd className="mono">{finding.package}</dd>
              </>
            )}
            {finding.cve_id && (
              <>
                <dt>cve</dt>
                <dd className="mono">{finding.cve_id}</dd>
              </>
            )}
            {finding.fixed_version && (
              <>
                <dt>fixed in</dt>
                <dd className="mono">{finding.fixed_version}</dd>
              </>
            )}
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
            <h3>assign owner</h3>
            <p className="muted small-text">
              The engineer responsible for the fix. Assigning notifies your configured channels.
            </p>
            <div className="assign-row">
              <input
                value={ownerDraft}
                placeholder="username or email"
                onChange={(event) => setOwnerDraft(event.target.value)}
                aria-label="Owner"
              />
              <button
                className="primary small"
                disabled={assign.isPending || !ownerDraft.trim()}
                onClick={() => assign.mutate(ownerDraft.trim())}
              >
                {assign.isPending ? "saving" : "assign"}
              </button>
              {finding.owner && (
                <button
                  className="ghost small"
                  disabled={assign.isPending}
                  onClick={() => assign.mutate(null)}
                >
                  clear
                </button>
              )}
            </div>
            {assign.isError && <p className="error small-text">{(assign.error as Error).message}</p>}
          </section>

          <section className="inspector-section">
            <h3>disposition</h3>
            {finding.status_reason && (
              <p className="muted small-text">
                {STATUS_LABEL[finding.status] ?? finding.status} by{" "}
                {finding.status_changed_by ?? "unknown"}: {finding.status_reason}
                {finding.risk_accepted_until &&
                  ` (expires ${new Date(finding.risk_accepted_until).toLocaleDateString()})`}
              </p>
            )}
            {finding.allowed_transitions.length === 0 ? (
              <p className="muted small-text">No transitions available from this state.</p>
            ) : (
              <div className="disposition">
                <select value={target} onChange={(event) => setTarget(event.target.value)}>
                  <option value="">change status to...</option>
                  {finding.allowed_transitions.map((status) => (
                    <option key={status} value={status}>
                      {STATUS_LABEL[status] ?? status}
                    </option>
                  ))}
                </select>
                {target && (
                  <>
                    <textarea
                      value={reason}
                      placeholder="justification (required)"
                      rows={2}
                      onChange={(event) => setReason(event.target.value)}
                    />
                    {target === "risk_accepted" && (
                      <label className="expiry-label">
                        accept until
                        <input
                          type="date"
                          value={expiry}
                          onChange={(event) => setExpiry(event.target.value)}
                        />
                      </label>
                    )}
                    <button
                      className="primary small"
                      disabled={
                        transition.isPending ||
                        !reason.trim() ||
                        (target === "risk_accepted" && !expiry)
                      }
                      onClick={() => transition.mutate()}
                    >
                      {transition.isPending ? "saving" : `mark ${STATUS_LABEL[target] ?? target}`}
                    </button>
                  </>
                )}
                {transition.isError && (
                  <p className="error small-text">{(transition.error as Error).message}</p>
                )}
              </div>
            )}
          </section>

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
