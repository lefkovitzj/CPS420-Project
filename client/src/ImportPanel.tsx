import { useEffect, useState } from 'react';
import { api } from './api';

type Term = { code: string; description: string };
type ImportJob = {
  id: number;
  term_code: string;
  status: 'running' | 'succeeded' | 'failed';
  section_count: number | null;
  finished_at: string | null;
  error: string | null;
};
type ApiFailure = Error & { status?: number };

export default function ImportPanel({ checkAccess }: { checkAccess: (e: ApiFailure) => boolean }) {
  const [terms, setTerms] = useState<Term[] | null>(null);
  const [term, setTerm] = useState('');
  const [termError, setTermError] = useState('');
  const [termAttempt, setTermAttempt] = useState(0);
  const [job, setJob] = useState<ImportJob | null>();
  const [trackedId, setTrackedId] = useState<number | null>(null);
  const [jobError, setJobError] = useState('');
  const [jobAttempt, setJobAttempt] = useState(0);
  const [starting, setStarting] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    setTermError('');
    api<Term[]>('/admin/imports/terms', { signal: controller.signal }).then(rows => {
      if (controller.signal.aborted) return;
      setTerms(rows);
      setTerm(rows[0]?.code ?? '');
    }).catch(e => { if (!controller.signal.aborted && !checkAccess(e)) setTermError(e.message); });
    return () => controller.abort();
  }, [termAttempt, checkAccess]);

  useEffect(() => {
    const controller = new AbortController();
    let timeout: ReturnType<typeof setTimeout>;
    async function load(id: number | null) {
      try {
        const next = await api<ImportJob | null>(`/admin/imports/${id ?? 'latest'}`, { signal: controller.signal });
        if (controller.signal.aborted) return;
        setJob(next);
        setJobError('');
        if (next?.status === 'running') timeout = setTimeout(() => load(next.id), 2000);
      } catch (e) {
        const failure = e as ApiFailure;
        if (!controller.signal.aborted && !checkAccess(failure)) setJobError(failure.message);
      }
    }
    void load(trackedId);
    return () => { controller.abort(); clearTimeout(timeout); };
  }, [trackedId, jobAttempt, checkAccess]);

  async function start() {
    setStarting(true);
    setJobError('');
    try {
      let next: ImportJob | null;
      try {
        next = await api<ImportJob>('/admin/imports', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ term_code: term }),
        });
      } catch (e) {
        if ((e as ApiFailure).status !== 409) throw e;
        next = await api<ImportJob | null>(`/admin/imports/latest?term_code=${encodeURIComponent(term)}`);
        if (!next) throw e;
      }
      setJob(next);
      setTrackedId(next.id);
    } catch (e) {
      const failure = e as ApiFailure;
      if (!checkAccess(failure)) setJobError(failure.message);
    } finally {
      setStarting(false);
    }
  }

  const jobTerm = terms?.find(t => t.code === job?.term_code)?.description ?? job?.term_code;
  return (
    <section aria-labelledby="admin-imports">
      <h2 id="admin-imports">Banner course import</h2>
      <label className="form-field">Academic term
        <select value={term} onChange={e => setTerm(e.target.value)} disabled={!terms?.length || starting}>
          {!terms?.length && <option value="">{termError ? 'Terms unavailable' : terms ? 'No terms available' : 'Loading terms…'}</option>}
          {terms?.map(t => <option key={t.code} value={t.code}>{t.description}</option>)}
        </select>
      </label>
      {termError && <p role="alert">{termError} <button type="button" onClick={() => setTermAttempt(a => a + 1)}>Retry terms</button></p>}
      <button type="button" className="primary-button" onClick={start}
        disabled={!term || starting || job === undefined || (job?.status === 'running' && job.term_code === term)}>
        {starting ? 'Starting…' : 'Start import'}
      </button>
      {jobError && <p role="alert">{jobError} <button type="button" onClick={() => setJobAttempt(a => a + 1)}>Refresh status</button></p>}
      <div role="status">
        {job === null && <p>No imports yet.</p>}
        {job?.status === 'running' && <p>Importing {jobTerm}…</p>}
        {job?.status === 'succeeded' && <p>Imported {job.section_count} sections for {jobTerm}.</p>}
        {job?.status === 'failed' && <p>Import failed for {jobTerm}. {job.error}</p>}
        {job?.finished_at && <p>Finished <time dateTime={job.finished_at}>{new Date(job.finished_at).toLocaleString()}</time></p>}
      </div>
    </section>
  );
}
