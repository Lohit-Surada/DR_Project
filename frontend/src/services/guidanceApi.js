import { VITE_API_BASE_URL } from './api';

export async function getRecoveryGuidance(classification) {
  const response = await fetch(`${VITE_API_BASE_URL}/api/guidance/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(classification),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || 'Educational guidance is temporarily unavailable.');
  return data;
}
