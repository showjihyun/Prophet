/**
 * LoginPage — Simple username/password auth form.
 * @spec docs/spec/06_API_SPEC.md
 */
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Brain, LogIn, UserPlus } from "lucide-react";
import { apiClient } from "../api/client";
import { LS_KEY_TOKEN, LS_KEY_USERNAME } from "@/config/constants";

export default function LoginPage() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleLogin() {
    setError(null);
    setLoading(true);
    try {
      const res = await apiClient.auth.login(username, password);
      localStorage.setItem(LS_KEY_TOKEN, res.token);
      localStorage.setItem(LS_KEY_USERNAME, res.username);
      navigate("/projects");
    } catch {
      setError("Invalid username or password.");
    } finally {
      setLoading(false);
    }
  }

  async function handleRegister() {
    setError(null);
    setLoading(true);
    try {
      await apiClient.auth.register(username, password);
      // Auto-login after register
      const res = await apiClient.auth.login(username, password);
      localStorage.setItem(LS_KEY_TOKEN, res.token);
      localStorage.setItem(LS_KEY_USERNAME, res.username);
      navigate("/projects");
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg.includes("409") ? "Username already taken." : "Registration failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="h-screen w-screen flex items-center justify-center bg-[var(--background)]">
      <div className="w-full max-w-sm bg-[var(--card)] border border-[var(--border)] rounded-xl p-8 flex flex-col gap-6 shadow-lg">
        {/* Logo */}
        <div className="flex items-center gap-2.5">
          <Brain className="w-6 h-6 text-[var(--foreground)]" />
          <span className="text-lg font-bold text-[var(--foreground)]">MCASP Prophet</span>
        </div>

        <div className="flex flex-col gap-1">
          <h1 className="text-xl font-semibold text-[var(--foreground)]">Sign in</h1>
          <p className="text-sm text-[var(--muted-foreground)]">Enter your credentials to continue.</p>
        </div>

        {/* Form */}
        <div className="flex flex-col gap-3">
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-[var(--muted-foreground)]">Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleLogin()}
              placeholder="username"
              className="h-10 px-3 rounded-md border border-[var(--input)] bg-[var(--background)] text-[var(--foreground)] text-sm focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-[var(--muted-foreground)]">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleLogin()}
              placeholder="password"
              className="h-10 px-3 rounded-md border border-[var(--input)] bg-[var(--background)] text-[var(--foreground)] text-sm focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
            />
          </div>

          {error && (
            <p className="text-xs text-[var(--destructive)]">{error}</p>
          )}
        </div>

        {/* Actions */}
        <div className="flex gap-2">
          <button
            onClick={handleLogin}
            disabled={loading || !username || !password}
            className="flex-1 h-10 flex items-center justify-center gap-2 rounded-md bg-[var(--primary)] text-[var(--primary-foreground)] text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-50 disabled:pointer-events-none"
          >
            <LogIn className="w-4 h-4" />
            Login
          </button>
          <button
            onClick={handleRegister}
            disabled={loading || !username || !password}
            className="flex-1 h-10 flex items-center justify-center gap-2 rounded-md border border-[var(--border)] text-[var(--foreground)] text-sm font-medium hover:bg-[var(--accent)] transition-colors disabled:opacity-50 disabled:pointer-events-none"
          >
            <UserPlus className="w-4 h-4" />
            Register
          </button>
        </div>
      </div>
    </div>
  );
}
