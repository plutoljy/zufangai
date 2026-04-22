export interface LocationLike {
  hostname: string;
  protocol: string;
  port?: string;
}

const API_PORT = Number(import.meta.env.VITE_API_PORT ?? '8000');

export function resolveApiBaseUrl(
  locationLike?: LocationLike | null
): string {
  const currentLocation =
    locationLike ??
    (typeof window !== 'undefined'
      ? {
          hostname: window.location.hostname,
          protocol: window.location.protocol,
          port: window.location.port,
        }
      : null);

  if (!currentLocation || !currentLocation.hostname) {
    return `http://localhost:${API_PORT}/api`;
  }

  if (
    (currentLocation.hostname === 'localhost' ||
      currentLocation.hostname === '127.0.0.1') &&
    (currentLocation.port === '3000' || currentLocation.port === '3001' || currentLocation.port === '5173')
  ) {
    return `http://localhost:${API_PORT}/api`;
  }

  const protocol =
    currentLocation.protocol === 'https:' ? 'https:' : 'http:';

  return `${protocol}//${currentLocation.hostname}:${API_PORT}/api`;
}
