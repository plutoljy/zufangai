export interface LocationLike {
  hostname: string;
  protocol: string;
  port?: string;
}

const viteEnv = (import.meta as ImportMeta & { env?: Record<string, string> }).env;
const API_PORT = Number(viteEnv?.VITE_API_PORT ?? '8000');
const API_BASE_URL_OVERRIDE = viteEnv?.VITE_API_BASE_URL?.trim();

export function resolveApiBaseUrl(
  locationLike?: LocationLike | null,
  apiPort = API_PORT,
  baseUrlOverride = API_BASE_URL_OVERRIDE
): string {
  if (baseUrlOverride) {
    return baseUrlOverride.endsWith('/')
      ? baseUrlOverride.slice(0, -1)
      : baseUrlOverride;
  }

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
    return `http://localhost:${apiPort}/api`;
  }

  const hostname =
    currentLocation.hostname === '0.0.0.0' ? 'localhost' : currentLocation.hostname;

  if (
    (hostname === 'localhost' ||
      hostname === '0.0.0.0' ||
      hostname === '127.0.0.1') &&
    (currentLocation.port === '3000' || currentLocation.port === '3001' || currentLocation.port === '5173')
  ) {
    return '/api';
  }

  const protocol =
    currentLocation.protocol === 'https:' ? 'https:' : 'http:';

  return `${protocol}//${hostname}:${apiPort}/api`;
}
