/**
 * Utility functions for safe API calls with error handling
 */

export interface ApiResponse<T> {
  ok: boolean;
  data?: T;
  error?: string;
  status?: number;
}

/**
 * Safely fetch JSON data with proper error handling
 */
export async function safeFetch<T>(
  url: string,
  options?: RequestInit
): Promise<ApiResponse<T>> {
  try {
    const response = await fetch(url, options);

    if (!response.ok) {
      let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
      try {
        const errorData = await response.json();
        errorMessage = errorData.detail || errorData.error || errorMessage;
      } catch {
        // If response isn't JSON, use status text
      }
      return {
        ok: false,
        error: errorMessage,
        status: response.status,
      };
    }

    const data = await response.json();
    return {
      ok: true,
      data,
      status: response.status,
    };
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    console.error(`API Error: ${url}`, errorMessage);
    return {
      ok: false,
      error: `Network error: ${errorMessage}`,
    };
  }
}

/**
 * Safely post data with JSON body
 */
export async function safePost<T>(
  url: string,
  body: any,
  options?: Omit<RequestInit, 'method' | 'body'>
): Promise<ApiResponse<T>> {
  return safeFetch<T>(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    body: JSON.stringify(body),
    ...options,
  });
}

/**
 * Safely get data
 */
export async function safeGet<T>(
  url: string,
  options?: Omit<RequestInit, 'method'>
): Promise<ApiResponse<T>> {
  return safeFetch<T>(url, {
    method: 'GET',
    ...options,
  });
}
