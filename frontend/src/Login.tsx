import { FormEvent, useState } from "react";

import { login } from "./api";
import { ShieldIcon } from "./Icons";

export function Login({ onLogin }: { onLogin: () => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(username, password);
      onLogin();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-wrap">
      <form className="login-card" onSubmit={submit}>
        <div className="login-brand">
          <span className="brand-mark" aria-hidden="true">
            <ShieldIcon />
          </span>
          <span className="brand-sub">vulnerability console</span>
        </div>
        <div>
          <h1>Sign in</h1>
          <p className="login-lede">Triage, prioritize, and remediate findings across your estate.</p>
        </div>
        <label>
          Username
          <input
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            autoComplete="username"
            required
          />
        </label>
        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="current-password"
            required
          />
        </label>
        {error && <p className="error small-text">{error}</p>}
        <button className="primary" type="submit" disabled={busy}>
          {busy ? "Signing in..." : "Sign in"}
        </button>
        <p className="login-foot">Access is logged to the audit trail.</p>
      </form>
    </div>
  );
}
