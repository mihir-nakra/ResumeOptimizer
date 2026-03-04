import { useState, useEffect, useRef, useCallback } from 'react';
import type { StatusResponse } from './types';
import { uploadResume, getStatus } from './api';
import UploadForm from './components/UploadForm';
import ProgressTracker from './components/ProgressTracker';
import ResultsPanel from './components/ResultsPanel';

type Phase = 'idle' | 'processing' | 'done';

const MAX_POLLS = 150;
const POLL_INTERVAL = 2000;
const MAX_CONSECUTIVE_ERRORS = 3;

export default function App() {
  const [phase, setPhase] = useState<Phase>('idle');
  const [status, setStatus] = useState<StatusResponse | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [pollError, setPollError] = useState<string | null>(null);

  const pollCount = useRef(0);
  const errorCount = useRef(0);
  const timerRef = useRef<number | null>(null);

  const stopPolling = useCallback(() => {
    if (timerRef.current !== null) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const poll = useCallback(async (id: string) => {
    if (pollCount.current >= MAX_POLLS) {
      setPollError('Timed out waiting for results.');
      setPhase('done');
      return;
    }

    pollCount.current++;

    try {
      const data = await getStatus(id);
      setStatus(data);
      errorCount.current = 0;

      if (data.status === 'completed' || data.status === 'failed') {
        setPhase('done');
        return;
      }

      timerRef.current = window.setTimeout(() => poll(id), POLL_INTERVAL);
    } catch {
      errorCount.current++;
      if (errorCount.current >= MAX_CONSECUTIVE_ERRORS) {
        setPollError('Lost connection to server.');
        setPhase('done');
        return;
      }
      timerRef.current = window.setTimeout(() => poll(id), POLL_INTERVAL);
    }
  }, []);

  useEffect(() => {
    return stopPolling;
  }, [stopPolling]);

  const handleUpload = async (file: File, jobDescription: string) => {
    setUploadError(null);
    setPollError(null);

    try {
      const res = await uploadResume(file, jobDescription);
      setPhase('processing');
      pollCount.current = 0;
      errorCount.current = 0;
      poll(res.request_id);
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : 'Upload failed');
    }
  };

  const handleReset = () => {
    stopPolling();
    setPhase('idle');
    setStatus(null);
    setUploadError(null);
    setPollError(null);
  };

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <header className="border-b border-gray-200 bg-white">
        <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between">
          <h1 className="text-lg font-bold text-gray-900">ResumeOptimizer</h1>
          {phase !== 'idle' && (
            <button
              onClick={handleReset}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              Start Over
            </button>
          )}
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-10">
        {pollError && (
          <div className="mb-6 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm max-w-2xl mx-auto">
            {pollError}
          </div>
        )}

        {phase === 'idle' && (
          <div>
            <div className="text-center mb-8">
              <h2 className="text-2xl font-bold text-gray-900 mb-2">Optimize Your Resume</h2>
              <p className="text-gray-500">Upload your resume and paste a job description to get ATS optimization, improvement suggestions, and interview prep questions.</p>
            </div>
            <UploadForm onSubmit={handleUpload} error={uploadError} />
          </div>
        )}

        {phase === 'processing' && status && (
          <div className="text-center">
            <h2 className="text-xl font-bold text-gray-900 mb-6">Analyzing your resume...</h2>
            <ProgressTracker status={status} />
          </div>
        )}

        {phase === 'processing' && !status && (
          <div className="text-center">
            <div className="h-8 w-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
            <p className="text-gray-500">Starting analysis...</p>
          </div>
        )}

        {phase === 'done' && status && (
          <ResultsPanel status={status} onReset={handleReset} />
        )}
      </main>
    </div>
  );
}
