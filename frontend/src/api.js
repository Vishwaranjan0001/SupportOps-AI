// One helper for every React → FastAPI request.
export async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.detail || 'Request failed');
  return result;
}

export function post(path, data = {}) {
  return api(path, { method: 'POST', body: JSON.stringify(data) });
}
