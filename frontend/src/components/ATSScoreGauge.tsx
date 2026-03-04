import type { ScoreBreakdown } from '../types';

interface Props {
  score: number;
  breakdown: ScoreBreakdown;
}

function scoreColor(score: number): string {
  if (score >= 75) return '#22c55e';
  if (score >= 50) return '#eab308';
  return '#ef4444';
}

const CATEGORIES: { key: keyof ScoreBreakdown; label: string }[] = [
  { key: 'technical_skills', label: 'Technical Skills' },
  { key: 'soft_skills', label: 'Soft Skills' },
  { key: 'qualifications', label: 'Qualifications' },
  { key: 'experience_requirements', label: 'Experience' },
];

export default function ATSScoreGauge({ score, breakdown }: Props) {
  const radius = 70;
  const circumference = 2 * Math.PI * radius;
  const progress = (score / 100) * circumference;
  const color = scoreColor(score);

  return (
    <div className="space-y-6">
      <div className="flex justify-center">
        <svg width="180" height="180" viewBox="0 0 180 180">
          <circle
            cx="90" cy="90" r={radius}
            fill="none" stroke="#e5e7eb" strokeWidth="10"
          />
          <circle
            cx="90" cy="90" r={radius}
            fill="none" stroke={color} strokeWidth="10"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={circumference - progress}
            transform="rotate(-90 90 90)"
            className="transition-all duration-700"
          />
          <text x="90" y="82" textAnchor="middle" className="text-3xl font-bold" fill={color} fontSize="36">
            {Math.round(score)}
          </text>
          <text x="90" y="105" textAnchor="middle" fill="#6b7280" fontSize="13">
            ATS Score
          </text>
        </svg>
      </div>

      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200 text-left text-gray-500">
            <th className="py-2 font-medium">Category</th>
            <th className="py-2 font-medium text-center">Matched</th>
            <th className="py-2 font-medium text-right">Rate</th>
          </tr>
        </thead>
        <tbody>
          {CATEGORIES.map(({ key, label }) => {
            const cat = breakdown[key];
            return (
              <tr key={key} className="border-b border-gray-100">
                <td className="py-2 text-gray-700">{label}</td>
                <td className="py-2 text-center text-gray-600">
                  {cat.matched} / {cat.total}
                </td>
                <td className="py-2 text-right font-medium" style={{ color: scoreColor(cat.rate * 100) }}>
                  {Math.round(cat.rate * 100)}%
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
