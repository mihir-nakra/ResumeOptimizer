import { useState } from 'react';
import type { StatusResponse } from '../types';
import ATSScoreGauge from './ATSScoreGauge';

type Tab = 'ats' | 'optimized' | 'suggestions' | 'interview';

const TABS: { key: Tab; label: string }[] = [
  { key: 'ats', label: 'ATS Score' },
  { key: 'optimized', label: 'Optimized Resume' },
  { key: 'suggestions', label: 'Suggestions' },
  { key: 'interview', label: 'Interview Questions' },
];

const IMPACT_COLORS: Record<string, string> = {
  high: 'bg-red-100 text-red-700',
  medium: 'bg-yellow-100 text-yellow-700',
  low: 'bg-green-100 text-green-700',
};

const DIFFICULTY_COLORS: Record<string, string> = {
  easy: 'bg-green-100 text-green-700',
  medium: 'bg-yellow-100 text-yellow-700',
  hard: 'bg-red-100 text-red-700',
};

interface Props {
  status: StatusResponse;
  onReset: () => void;
}

export default function ResultsPanel({ status, onReset }: Props) {
  const [tab, setTab] = useState<Tab>('ats');

  const ats = status.stages.ats_optimization.result;
  const suggestions = status.stages.suggestions.result;
  const interview = status.stages.interview.result;

  return (
    <div className="w-full max-w-4xl mx-auto">
      <div className="flex flex-wrap gap-2 border-b border-gray-200 mb-6">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-colors ${
              tab === t.key
                ? 'bg-white border border-b-white border-gray-200 -mb-px text-blue-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="bg-white rounded-lg border border-gray-200 p-6">
        {tab === 'ats' && ats && (
          <ATSScoreGauge score={ats.ats_score} breakdown={ats.score_breakdown} />
        )}

        {tab === 'optimized' && ats && (
          <div className="space-y-4">
            {ats.optimized_sections.map((section, i) => (
              <div key={i} className="border border-gray-200 rounded-lg p-4">
                <h3 className="font-semibold text-gray-800 capitalize mb-2">
                  {section.section_name}
                </h3>
                <p className="text-sm text-gray-600 mb-3">{section.changes_summary}</p>
                <div className="bg-gray-50 rounded p-3 text-sm text-gray-700 whitespace-pre-wrap">
                  {section.optimized_content}
                </div>
                {section.keywords_incorporated.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mt-3">
                    {section.keywords_incorporated.map((kw, j) => (
                      <span key={j} className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs rounded-full">
                        {kw}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {tab === 'suggestions' && suggestions && (
          <div className="space-y-6">
            {suggestions.priority_areas.length > 0 && (
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                <h3 className="font-semibold text-amber-800 mb-2">Priority Areas</h3>
                <ul className="list-disc list-inside text-sm text-amber-700 space-y-1">
                  {suggestions.priority_areas.map((area, i) => (
                    <li key={i}>{area}</li>
                  ))}
                </ul>
              </div>
            )}
            <div className="space-y-3">
              {[...suggestions.suggestions]
                .sort((a, b) => {
                  const order = { high: 0, medium: 1, low: 2 };
                  return order[a.impact] - order[b.impact];
                })
                .map((s, i) => (
                  <div key={i} className="border border-gray-200 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${IMPACT_COLORS[s.impact]}`}>
                        {s.impact}
                      </span>
                      <span className="text-xs text-gray-400 capitalize">{s.section}</span>
                    </div>
                    <p className="text-sm text-gray-800 mb-2">{s.suggestion}</p>
                    {s.example && (
                      <div className="bg-gray-50 rounded p-2 text-xs text-gray-600">
                        <span className="font-medium">Example: </span>{s.example}
                      </div>
                    )}
                  </div>
                ))}
            </div>
          </div>
        )}

        {tab === 'interview' && interview && (
          <div className="space-y-6">
            {Object.entries(
              interview.questions.reduce<Record<string, typeof interview.questions>>((acc, q) => {
                (acc[q.category] ??= []).push(q);
                return acc;
              }, {})
            ).map(([category, questions]) => (
              <div key={category}>
                <h3 className="font-semibold text-gray-800 capitalize mb-3">{category.replace('_', ' ')}</h3>
                <div className="space-y-3">
                  {questions.map((q, i) => (
                    <div key={i} className="border border-gray-200 rounded-lg p-4">
                      <div className="flex items-center gap-2 mb-2">
                        <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${DIFFICULTY_COLORS[q.difficulty]}`}>
                          {q.difficulty}
                        </span>
                        <span className="text-xs text-gray-400">{q.skill_assessed}</span>
                      </div>
                      <p className="text-sm text-gray-800 font-medium mb-2">{q.question}</p>
                      {q.follow_ups.length > 0 && (
                        <div className="ml-4 space-y-1">
                          {q.follow_ups.map((fu, j) => (
                            <p key={j} className="text-xs text-gray-500">— {fu}</p>
                          ))}
                        </div>
                      )}
                      <p className="text-xs text-gray-400 mt-2 italic">
                        Look for: {q.what_to_look_for}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Fallback for failed stages */}
        {tab === 'ats' && !ats && status.stages.ats_optimization.status === 'failed' && (
          <p className="text-red-600 text-sm">ATS optimization failed: {status.stages.ats_optimization.error}</p>
        )}
        {tab === 'suggestions' && !suggestions && status.stages.suggestions.status === 'failed' && (
          <p className="text-red-600 text-sm">Suggestion generation failed: {status.stages.suggestions.error}</p>
        )}
        {tab === 'interview' && !interview && status.stages.interview.status === 'failed' && (
          <p className="text-red-600 text-sm">Interview generation failed: {status.stages.interview.error}</p>
        )}
      </div>

      <div className="mt-6 text-center">
        <button
          onClick={onReset}
          className="px-6 py-2 bg-gray-100 text-gray-700 font-medium rounded-lg hover:bg-gray-200 transition-colors"
        >
          Start Over
        </button>
      </div>
    </div>
  );
}
