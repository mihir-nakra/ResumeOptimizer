import type { UploadResponse, StatusResponse } from './types';

export async function uploadResume(
  file: File,
  jobDescription: string,
): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('job_description', jobDescription);

  const res = await fetch('/api/v1/resume/upload', {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail ?? `Upload failed (${res.status})`);
  }

  return res.json();
}

export async function getStatus(requestId: string): Promise<StatusResponse> {
  const res = await fetch(`/api/v1/resume/status/${requestId}`);

  if (!res.ok) {
    throw new Error(`Status check failed (${res.status})`);
  }

  return res.json();
}
