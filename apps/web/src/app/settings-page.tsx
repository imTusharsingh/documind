import { useEffect, useState } from 'react';
import { Check, KeyRound, Settings2, SlidersHorizontal } from 'lucide-react';

import { Badge, Button, Card, Field, PageHeader, SectionHeading } from '@/components/ui';

interface Preferences { chunkTokens: string; overlapTokens: string; maxUploadMb: string; model: string; }
const defaults: Preferences = { chunkTokens: '350', overlapTokens: '50', maxUploadMb: '25', model: 'text-embedding-3-small' };

export function SettingsPage() {
  const [preferences, setPreferences] = useState<Preferences>(defaults);
  const [saved, setSaved] = useState(false);
  useEffect(() => { const stored = localStorage.getItem('documind.preferences'); if (stored) setPreferences({ ...defaults, ...JSON.parse(stored) as Partial<Preferences> }); }, []);
  function update(key: keyof Preferences, value: string) { setSaved(false); setPreferences((current) => ({ ...current, [key]: value })); }
  function save() { localStorage.setItem('documind.preferences', JSON.stringify(preferences)); setSaved(true); }

  return <div className="space-y-8">
    <PageHeader eyebrow="Workspace settings" title="Settings" description="Configure the defaults that shape document extraction, retrieval, and your research workspace." action={saved ? <Badge tone="success"><Check size={12} />Saved</Badge> : null} />
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_320px]">
      <div className="space-y-5">
        <Card className="p-6"><SectionHeading title="AI provider" description="Provider credentials stay on the API server and are never exposed to the browser." /><div className="mt-6 rounded-xl border border-border bg-background p-4"><div className="flex items-start gap-3"><span className="flex size-9 items-center justify-center rounded-lg bg-citation text-primary"><KeyRound size={17} /></span><div className="min-w-0"><p className="text-sm font-semibold">OpenAI API token</p><p className="mt-1 text-xs leading-5 text-muted">Managed through <code className="font-mono">OPENAI_API_KEY</code> in the API environment.</p></div><Badge tone="success">Configured</Badge></div><div className="mt-4 flex items-center justify-between gap-3 border-t border-border pt-4"><span className="font-mono text-xs text-muted">••••••••••••••••</span><Button variant="secondary" size="sm" onClick={() => window.open('/api/docs', '_blank', 'noopener,noreferrer')}>API docs</Button></div></div><div className="mt-4 grid gap-4 sm:grid-cols-2"><Field label="Chat model" value="gpt-4.1-mini" readOnly hint="Configured by the API environment." /><Field label="Embedding model" value={preferences.model} onChange={(event) => update('model', event.target.value)} hint="Changing this requires reprocessing existing documents." /></div></Card>
        <Card className="p-6"><SectionHeading title="Extraction defaults" description="These defaults are saved for this workspace in your browser. Server limits remain authoritative." /><div className="mt-6 grid gap-4 sm:grid-cols-3"><Field label="Chunk size" type="number" value={preferences.chunkTokens} onChange={(event) => update('chunkTokens', event.target.value)} hint="Tokens per chunk" /><Field label="Overlap" type="number" value={preferences.overlapTokens} onChange={(event) => update('overlapTokens', event.target.value)} hint="Tokens between chunks" /><Field label="Upload limit" type="number" value={preferences.maxUploadMb} onChange={(event) => update('maxUploadMb', event.target.value)} hint="MB per PDF" /></div></Card>
        <Card className="p-6"><SectionHeading title="Interface" description="Keep the workspace calm and focused while you research." /><div className="mt-5 flex items-center justify-between rounded-xl border border-border bg-background p-4"><div className="flex items-center gap-3"><span className="flex size-9 items-center justify-center rounded-lg bg-citation text-primary"><SlidersHorizontal size={17} /></span><div><p className="text-sm font-medium">Compact document cards</p><p className="text-xs text-muted">Use denser rows in the document library.</p></div></div><input type="checkbox" className="size-4 accent-primary" defaultChecked aria-label="Compact document cards" /></div></Card>
        <Button onClick={save}><Settings2 size={15} />Save preferences</Button>
      </div>
      <Card className="h-fit p-6"><p className="text-xs font-semibold uppercase tracking-[0.14em] text-primary">Security note</p><h2 className="mt-3 text-lg font-semibold">Secrets belong on the server</h2><p className="mt-2 text-sm leading-6 text-muted">DocuMind intentionally does not persist API keys in browser storage. Configure provider credentials in the API environment and restart the API and worker together.</p><div className="mt-5 space-y-3 border-t border-border pt-5 text-xs leading-5 text-muted"><p><strong className="text-foreground">Never</strong> paste a production token into client-side settings.</p><p><strong className="text-foreground">Always</strong> rotate keys if they are exposed.</p></div></Card>
    </div>
  </div>;
}
