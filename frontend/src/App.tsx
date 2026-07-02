import { useEffect, useState } from "react";

import { getToken, logout } from "./api";
import { Login } from "./Login";
import { Workspace } from "./Workspace";

type Theme = "dark" | "light";

export function App() {
  const [authed, setAuthed] = useState<boolean>(() => getToken() !== null);
  const [theme, setTheme] = useState<Theme>(
    () => (localStorage.getItem("vc_theme") as Theme | null) ?? "dark",
  );

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("vc_theme", theme);
  }, [theme]);

  if (!authed) {
    return <Login onLogin={() => setAuthed(true)} />;
  }
  return (
    <Workspace
      theme={theme}
      onToggleTheme={() => setTheme(theme === "dark" ? "light" : "dark")}
      onSignOut={() => {
        logout();
        setAuthed(false);
      }}
    />
  );
}
