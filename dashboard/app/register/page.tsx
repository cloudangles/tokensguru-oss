"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { register } from "@/lib/api";
import { saveSession } from "@/lib/auth";
import { Button, Card } from "@/components/ui";

export default function RegisterPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [apiKey, setApiKey] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await register(email, password);
      saveSession(res.access_token, res.email);
      setApiKey(res.api_key);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setBusy(false);
    }
  }

  if (apiKey) {
    return (
      <div className="flex min-h-screen items-center justify-center p-6">
        <Card padding="lg" className="w-full max-w-md">
          <h1 className="mb-2 font-display text-xl font-bold text-fg-strong">
            Account created
          </h1>
          <p className="mb-3 text-sm text-fg-muted">
            Save your API key now -- it won't be shown again. Use it as
            <code className="mx-1 rounded bg-surface-2 px-1 py-0.5 text-xs">X-API-Key</code>
            when calling the SDK/API directly.
          </p>
          <code className="mb-6 block break-all rounded-lg border border-line bg-surface-2 p-3 text-xs text-fg">
            {apiKey}
          </code>
          <Button variant="primary" fullWidth onClick={() => router.push("/")}>
            Go to dashboard
          </Button>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-6">
      <Card padding="lg" className="w-full max-w-sm">
        <h1 className="mb-1 font-display text-2xl font-bold text-fg-strong">TokenSight</h1>
        <p className="mb-6 text-sm text-fg-muted">Create your account.</p>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <input
            type="email"
            required
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="h-10 rounded-lg border border-line bg-surface-2 px-3 text-sm text-fg outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
          <input
            type="password"
            required
            minLength={8}
            placeholder="Password (min 8 characters)"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="h-10 rounded-lg border border-line bg-surface-2 px-3 text-sm text-fg outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
          {error && <p className="text-sm text-danger">{error}</p>}
          <Button type="submit" variant="primary" loading={busy} fullWidth>
            Register
          </Button>
        </form>
        <p className="mt-4 text-center text-xs text-fg-subtle">
          Already have an account?{" "}
          <Link href="/login" className="text-brand hover:underline">
            Log in
          </Link>
        </p>
      </Card>
    </div>
  );
}
