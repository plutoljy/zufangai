import { getCurrentSession } from './authService';

export async function buildAuthenticatedHeaders(
  initialHeaders?: HeadersInit
): Promise<Headers> {
  const headers = new Headers(initialHeaders);

  try {
    const session = await getCurrentSession();
    if (session?.access_token) {
      headers.set('Authorization', `Bearer ${session.access_token}`);
    }
  } catch (error) {
    console.warn('Unable to load auth session for API request', error);
  }

  return headers;
}
