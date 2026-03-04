import type { StatusResponse, StageName, StageStatus } from '../types';

const STAGES: { key: StageName; label: string }[] = [
  { key: 'parsing', label: 'Parsing Resume' },
  { key: 'ats_optimization', label: 'ATS Optimization' },
  { key: 'suggestions', label: 'Generating Suggestions' },
  { key: 'interview', label: 'Interview Questions' },
];

function statusIcon(status: StageStatus) {
  switch (status) {
    case 'completed':
      return (
        <svg className="h-5 w-5 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
        </svg>
      );
    case 'running':
      return (
        <div className="h-5 w-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
      );
    case 'failed':
      return (
        <svg className="h-5 w-5 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      );
    default:
      return <div className="h-5 w-5 rounded-full border-2 border-gray-300" />;
  }
}

interface Props {
  status: StatusResponse;
}

export default function ProgressTracker({ status }: Props) {
  return (
    <div className="w-full max-w-md mx-auto">
      <div className="space-y-4">
        {STAGES.map((stage, i) => {
          const s = status.stages[stage.key];
          return (
            <div key={stage.key} className="flex items-center gap-4">
              <div className="flex flex-col items-center">
                <div className="flex items-center justify-center w-8 h-8">
                  {statusIcon(s.status)}
                </div>
                {i < STAGES.length - 1 && (
                  <div className={`w-0.5 h-6 mt-1 ${
                    s.status === 'completed' ? 'bg-green-300' : 'bg-gray-200'
                  }`} />
                )}
              </div>
              <div className="flex-1 pb-2">
                <p className={`font-medium text-sm ${
                  s.status === 'running' ? 'text-blue-700' :
                  s.status === 'completed' ? 'text-green-700' :
                  s.status === 'failed' ? 'text-red-700' :
                  'text-gray-400'
                }`}>
                  {stage.label}
                </p>
                {s.error && (
                  <p className="text-xs text-red-500 mt-0.5">{s.error}</p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
