import { useRef, useState, type FormEvent } from "react";

import { uploadScan } from "./api";

export function UploadSheet({
  onClose,
  onUploaded,
}: {
  onClose: () => void;
  onUploaded: () => void;
}) {
  const fileInput = useRef<HTMLInputElement>(null);
  const [repository, setRepository] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const file = fileInput.current?.files?.[0];
    if (!file) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const scan = await uploadScan(file, repository);
      setMessage(`Scan accepted (${scan.id.slice(0, 8)}). Findings appear once processed.`);
      if (fileInput.current) fileInput.current.value = "";
      window.setTimeout(onUploaded, 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="upload-sheet">
      <form onSubmit={submit}>
        <span className="sheet-label">upload scan report</span>
        <input
          placeholder="repository, e.g. org/service"
          value={repository}
          onChange={(event) => setRepository(event.target.value)}
          aria-label="Repository"
          required
        />
        <input ref={fileInput} type="file" accept=".sarif,.json" aria-label="Report file" required />
        <button className="primary small" type="submit" disabled={busy}>
          {busy ? "uploading" : "upload"}
        </button>
        <button className="ghost small" type="button" onClick={onClose}>
          close
        </button>
        {message && <span className="ok">{message}</span>}
        {error && <span className="error">{error}</span>}
      </form>
    </div>
  );
}
