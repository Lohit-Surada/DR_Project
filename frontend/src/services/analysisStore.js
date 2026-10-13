import { onValue, push, query, ref, orderByChild, set } from 'firebase/database';
import { realtimeDb } from './firebase';

const localHistoryKey = (userId) => `retinaiq-analyses:${String(userId)}`;

function readLocalHistory(userId) {
  try {
    return JSON.parse(window.localStorage.getItem(localHistoryKey(userId)) || '[]');
  } catch {
    return [];
  }
}

function writeLocalHistory(userId, analysis) {
  try {
    const current = readLocalHistory(userId).filter((item) => item.id !== analysis.id);
    window.localStorage.setItem(localHistoryKey(userId), JSON.stringify([analysis, ...current].slice(0, 50)));
  } catch {
    // Firebase remains the remote history source when local storage is unavailable.
  }
}

function mergeHistory(remote, local) {
  const identity = (item) => `${item.userId}:${item.createdAt}:${item.image?.name || ''}`;
  const entries = new Map(local.map((item) => [identity(item), item]));
  remote.forEach((item) => entries.set(identity(item), item));
  return [...entries.values()].sort((first, second) => new Date(second.createdAt) - new Date(first.createdAt));
}

export function subscribeToUserAnalyses(userId, onChange, onError) {
  const analysesQuery = query(ref(realtimeDb, `analyses/${String(userId)}`), orderByChild('createdAt'));
  onChange(readLocalHistory(userId));

  return onValue(analysesQuery, (snapshot) => {
    const remoteAnalyses = Object.entries(snapshot.val() || {})
      .map(([id, data]) => ({ id, ...data }))
    onChange(mergeHistory(remoteAnalyses, readLocalHistory(userId)));
  }, (error) => {
    onChange(readLocalHistory(userId));
    onError(error);
  });
}

export function saveAnalysis({ userId, userEmail, image }) {
  const analysis = {
    id: `local-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    userId: String(userId),
    userEmail,
    image,
    uploadedAt: new Date().toISOString(),
    createdAt: new Date().toISOString(),
  };
  writeLocalHistory(userId, analysis);
  const analysisRef = push(ref(realtimeDb, `analyses/${String(userId)}`));
  const { id: _localId, ...remoteAnalysis } = analysis;
  return set(analysisRef, remoteAnalysis);
}
