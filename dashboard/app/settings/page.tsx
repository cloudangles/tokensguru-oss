"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { RequireAuth } from "@/components/RequireAuth";
import { fetchProviderKeys, saveProviderKey, deleteProviderKey, PROVIDERS } from "@/lib/api";
import { Card, SectionHeading, Button, Badge, EmptyState } from "@/components/ui";

export default function SettingsPage() {
  return (
    <RequireAuth>
      <Settings />
    </RequireAuth>
  );
}

function Settings() {
  const qc = useQueryClient();
  const keys = useQuery({ queryKey: ["provider-keys"], queryFn: fetchProviderKeys });

  const [provider, setProvider] = useState<string>(PROVIDERS[0]);
  const [apiKey, setApiKey] = useState("");
  const [error, setError] = useState<string | null>(null);

  const save = useMutation({
    mutationFn: () => saveProviderKey(provider, apiKey),
    onSuccess: () => {
      setApiKey("");
      setError(null);
      qc.invalidateQueries({ queryKey: ["provider-keys"] });
    },
    onError: (err) => setError(err instanceof Error ? err.message : "Failed to save key"),
  });

  const remove = useMutation({
    mutationFn: (p: string) => deleteProviderKey(p),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["provider-keys"] }),
  });

  return (
    <div className="flex flex-col gap-8 max-w-2xl">
      <div>
        <SectionHeading>Settings</SectionHeading>
        <p className="text-sm text-fg-muted">
          Add your own provider API keys to test the Playground and SDK without editing
          <code className="mx-1 rounded bg-surface-2 px-1 py-0.5 text-xs">.env</code>
          or restarting the container. Keys are stored per-tenant in your self-hosted
          ClickHouse instance — nothing leaves your deployment.
        </p>
      </div>

      <Card>
        <p className="mb-4 text-xs font-semibold uppercase tracking-wider text-fg-muted">
          Add / update a provider key
        </p>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <div className="flex flex-col gap-1">
            <label className="text-xs text-fg-subtle">Provider</label>
            <select
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              className="h-10 w-44 rounded-lg border border-line bg-surface-2 px-3 text-sm text-fg"
            >
              {PROVIDERS.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </div>
          <div className="flex flex-1 flex-col gap-1">
            <label className="text-xs text-fg-subtle">API key</label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder={provider === "ollama" ? "optional -- Ollama has no key by default" : "sk-..."}
              className="h-10 rounded-lg border border-line bg-surface-2 px-3 font-mono text-sm text-fg outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
          </div>
          <Button
            variant="primary"
            loading={save.isPending}
            disabled={!apiKey.trim()}
            onClick={() => save.mutate()}
          >
            Save
          </Button>
        </div>
        {error && <p className="mt-2 text-sm text-danger">{error}</p>}
      </Card>

      <div>
        <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-fg-muted">
          Configured providers
        </p>
        <Card padding="none">
          {keys.isLoading ? (
            <div className="p-6 text-sm text-fg-muted">Loading…</div>
          ) : !keys.data || keys.data.length === 0 ? (
            <EmptyState
              title="No provider keys yet"
              description="Add one above to run real Playground requests against that provider."
            />
          ) : (
            <div className="divide-y divide-line">
              {keys.data.map((k) => (
                <div key={k.provider} className="flex items-center justify-between px-4 py-3">
                  <div className="flex items-center gap-3">
                    <Badge tone="brand">{k.provider}</Badge>
                    <span className="font-mono text-sm text-fg-muted">{k.masked_key}</span>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    loading={remove.isPending && remove.variables === k.provider}
                    onClick={() => remove.mutate(k.provider)}
                  >
                    Remove
                  </Button>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      <Card tone="warning">
        <p className="text-xs text-fg-muted">
          <strong className="text-warning">Note:</strong> keys are stored in plaintext in
          ClickHouse (a deliberate OSS simplification — no vault/KMS). Use test/dev keys with
          spend limits if you're unsure about your deployment's security posture, same as you
          would for any self-hosted tool.
        </p>
      </Card>
    </div>
  );
}
