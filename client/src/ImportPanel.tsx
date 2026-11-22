import { useEffect, useState } from 'react';
import { api } from './api';

type Term = { code: string; description: string };
type ImportJob = {
  term_code: string;
  status: 'running' | 'succeeded' | 'failed';
  section_count: number | null;
  finished_at: string | null;
  error: string | null;
};
type ApiFailure = Error & { status?: number };
const selectedTermKey = 'bannerImportTerm';

export default function ImportPanel({ checkAccess }: { checkAccess: (e: ApiFailure) => boolean }) {
  const [terms, setTerms] = useState<Term[] | null>(null);
  const [term, setTerm] = useState(() => sessionStorage.getItem(selectedTermKey) ?? '');
  const [termError, setTermError] = useState('');
  const [termAttempt, setTermAttempt] = useState(0);
  const [job, setJob] = useState<ImportJob | null>();
  const [jobError, setJobError] = useState('');
  const [jobAttempt, setJobAttempt] = useState(0);
  const [starting, setStarting] = useState(false);

  useEffect(() => {
    if (window.location.hash === '#admin-imports') document.getElementById('admin-imports')?.focus();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    setTermError('');
    api<Term[]>('/admin/imports/terms', { signal: controller.signal }).then(rows => {
      if (controller.signal.aborted) return;
      setTerms(rows);
      setTerm(current => rows.some(t => t.code === current) ? current : rows[0]?.code ?? '');
    }).catch(e => { if (!controller.signal.aborted && !checkAccess(e)) setTermError(e.message); });
    return () => controller.abort();
  }, [termAttempt, checkAccess]);

  useEffect(() => {
    setJob(undefined);
    setJobError('');
    if (!term) return;
    sessionStorage.setItem(selectedTermKey, term);
    const controller = new AbortController();
    let timeout: ReturnType<typeof setTimeout>;
    async function load() {
      try {
        const next = await api<ImportJob | null>(`/admin/imports/latest?term_code=${encodeURIComponent(term)}`, { signal: controller.signal });
        if (controller.signal.aborted) return;
        setJob(next);
        setJobError('');
        if (next?.status === 'running') timeout = setTimeout(load, 2000);
      } catch (e) {
        const failure = e as ApiFailure;
        if (!controller.signal.aborted && !checkAccess(failure)) setJobError(failure.message);
      }
    }
    void load();
    return () => { controller.abort(); clearTimeout(timeout); };
  }, [term, jobAttempt, checkAccess]);

  async function start() {
    setStarting(true);
    setJobError('');
    try {
      await api('/admin/imports', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ term_code: term }),
      });
    } catch (e) {
      const failure = e as ApiFailure;
      if (failure.status !== 409) {
        if (!checkAccess(failure)) setJobError(failure.message);
        return;
      }
    } finally {
      setStarting(false);
    }
    // Whether we started it or another admin did, follow this term's import.
    setJobAttempt(a => a + 1);
  }

  const jobTerm = terms?.find(t => t.code === job?.term_code)?.description ?? job?.term_code;
  return (
    <section aria-labelledby="admin-imports">
      <h2 id="admin-imports" tabIndex={-1}>Banner course import</h2>
      <label className="form-field">Academic term
        <select value={term} onChange={e => setTerm(e.target.value)} disabled={!terms?.length || starting}>
          {!terms?.length && <option value="">{termError ? 'Terms unavailable' : terms ? 'No terms available' : 'Loading terms…'}</option>}
          {terms?.map(t => <option key={t.code} value={t.code}>{t.description}</option>)}
        </select>
      </label>
      {termError && <p role="alert">{termError} <button type="button" onClick={() => setTermAttempt(a => a + 1)}>Retry terms</button></p>}
      <button type="button" className="primary-button" onClick={start}
        disabled={!terms?.length || !term || starting || job === undefined || job?.status === 'running'}>
        {starting ? 'Starting…' : job?.status === 'failed' ? 'Retry import' : 'Start import'}
      </button>
      {jobError && <p role="alert">{jobError} <button type="button" onClick={() => setJobAttempt(a => a + 1)}>Refresh status</button></p>}
      <div role="status">
        {job === null && <p>No imports for this term yet.</p>}
        {job?.status === 'running' && <p>Importing {jobTerm}…</p>}
        {job?.status === 'succeeded' && <p>Imported {job.section_count} sections for {jobTerm}.</p>}
        {job?.status === 'failed' && <p>Import failed for {jobTerm}. {job.error}</p>}
        {job?.finished_at && <p>Finished <time dateTime={job.finished_at}>{new Date(job.finished_at).toLocaleString()}</time></p>}
      </div>
    </section>
  );
}
