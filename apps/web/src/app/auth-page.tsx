import { useState } from 'react';
import type { FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AlertCircle, ArrowRight, KeyRound } from 'lucide-react';

import { authenticate, ApiError } from '@/lib/api';
import { BrandLockup, Button, Card, Field } from '@/components/ui';

export function AuthPage() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [challenge, setChallenge] = useState<string | null>(null);
  const [form, setForm] = useState({ email: '', password: '', display_name: '', code: '' });
  const [error, setError] = useState('');
  const update = (key: keyof typeof form, value: string) => setForm((current) => ({ ...current, [key]: value }));
  const submit = async (event: FormEvent) => { event.preventDefault(); setError(''); try { if (challenge) { await authenticate('verify', { challenge_id: challenge, code: form.code }); navigate('/'); return; } const result = await authenticate(mode, mode === 'login' ? { email: form.email, password: form.password } : form); setChallenge(result.challenge_id ?? null); } catch (cause) { setError(cause instanceof ApiError ? cause.message : 'Authentication failed.'); } };
  return <main className="flex min-h-screen items-center justify-center bg-background px-5 py-12"><Card className="w-full max-w-md p-8"><Link to="/home" className="mb-10 inline-flex"><BrandLockup className="h-10 max-w-[160px]" /></Link><div className="flex size-10 items-center justify-center rounded-xl bg-citation text-primary"><KeyRound size={18} /></div><h1 className="mt-5 text-2xl font-semibold">{challenge ? 'Verify your email' : mode === 'login' ? 'Welcome back' : 'Create your workspace'}</h1><p className="mt-2 text-sm leading-6 text-muted">{challenge ? 'Enter the six-digit code sent to your email.' : 'Sign in to keep your documents and research private.'}</p>{error ? <div className="mt-5 flex gap-2 rounded-xl border border-error/20 bg-error/5 p-3 text-sm text-error"><AlertCircle size={16} />{error}</div> : null}<form onSubmit={submit} className="mt-6 space-y-4">{challenge ? <Field label="Verification code" value={form.code} onChange={(event) => update('code', event.target.value)} inputMode="numeric" maxLength={6} required /> : <><Field label="Email" type="email" value={form.email} onChange={(event) => update('email', event.target.value)} required /><Field label="Password" type="password" value={form.password} onChange={(event) => update('password', event.target.value)} minLength={8} required />{mode === 'register' ? <Field label="Display name" value={form.display_name} onChange={(event) => update('display_name', event.target.value)} required /> : null}</>}<Button className="w-full" type="submit">{challenge ? 'Verify and continue' : mode === 'login' ? 'Continue' : 'Create account'}<ArrowRight size={15} /></Button></form>{!challenge ? <button type="button" className="mt-6 w-full text-center text-sm text-muted hover:text-foreground" onClick={() => setMode(mode === 'login' ? 'register' : 'login')}>{mode === 'login' ? 'Create a new account' : 'Already have an account? Sign in'}</button> : null}</Card></main>;
}
