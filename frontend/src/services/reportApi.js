import { auth } from './firebase';
import { VITE_API_BASE_URL } from './api';

const reportClientIdKey = 'retinaiq-report-client-id';

function getReportClientId() {
  let clientId = window.localStorage.getItem(reportClientIdKey);
  if (!clientId) {
    clientId = crypto.randomUUID();
    window.localStorage.setItem(reportClientIdKey, clientId);
  }
  return clientId;
}

async function authHeaders() {
  const user = auth.currentUser;
  if (!user) throw new Error('Sign in to access medical reports.');
  return {
    Authorization: `Bearer ${await user.getIdToken()}`,
    'X-Report-Client-ID': getReportClientId(),
  };
}

export async function createReport({ image, classification, lesions, guidance, gradcam, profile }) {
  const formData = new FormData();
  formData.append('image', image);
  formData.append('payload', JSON.stringify({
    classification,
    lesions: {
      ...lesions,
      image_path: lesions.image_url,
    },
    guidance: guidance || { tips: [], medications: [] },
    gradcam: {
      ...gradcam,
      combined_path: gradcam.combined,
    },
    metadata: {
      generated_at: new Date().toISOString(),
      report_date: new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' }),
      model: 'RetinaIQ CNN + YOLO26 analysis pipeline',
      profile: Object.fromEntries(
        Object.entries({
          full_name: profile?.fullName,
          age: profile?.age,
          sex: profile?.sex,
          dob: profile?.dob || profile?.dateOfBirth,
          email: profile?.email,
          contact_no: profile?.contactNo || profile?.phone,
          address: profile?.address,
          blood_group: profile?.bloodGroup,
        }).filter(([, value]) => value !== undefined && value !== null && String(value).trim() !== ''),
      ),
    },
  }));
  const response = await fetch(`${VITE_API_BASE_URL}/api/reports/`, {
    method: 'POST',
    headers: await authHeaders(),
    body: formData,
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Unable to prepare the medical report.');
  return data;
}

async function getReportBlob(analysisId, disposition) {
  const response = await fetch(`${VITE_API_BASE_URL}/api/reports/${analysisId}/${disposition}/`, {
    headers: await authHeaders(),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.error || 'Unable to load the medical report.');
  }
  return response.blob();
}

export function getReportViewBlob(analysisId) {
  return getReportBlob(analysisId, 'view');
}

export function downloadReportPdf(analysisId) {
  return getReportBlob(analysisId, 'download');
}