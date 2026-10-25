export const API_BASE =
  (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_BASE_URL) ||
  'http://localhost:8000';

export async function fetchCities() {
  const res = await fetch(`${API_BASE}/api/cities`);
  if (!res.ok) throw new Error('Failed to load cities');
  return res.json();
}

export async function generateItinerary(payload) {
  const res = await fetch(`${API_BASE}/api/generate-itinerary`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    let body = null;
    try {
      body = await res.json();
    } catch {
      body = null;
    }
    const error = new Error('API failed');
    error.status = res.status;
    error.body = body;
    throw error;
  }
  return res.json();
}
