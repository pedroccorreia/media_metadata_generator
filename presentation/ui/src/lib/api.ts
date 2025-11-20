import { logger } from "./logger";

const API_URL = process.env.API_URL || 'http://localhost:9002';

logger.log(`Resolved API Target URL: ${API_URL}`);

async function fetchApi(path: string, options: RequestInit = {}) {
  const url = `${API_URL}${path}`;
  const res = await fetch(url, options);
  
  logger.log(`fetchAPI result: ${res}`)

  if (!res.ok) {
    const errorText = await res.text();
    logger.error(`failed to call api ${API_URL}${path}: ${errorText}`)
    throw new Error(`API call to ${path} failed with status ${res.status}: ${errorText}`);
  }

  const responseText = await res.text();
  try {
    const res = responseText ? JSON.parse(responseText) : {};
    return res
  } catch (error) {
    logger.error(`Failed to parse JSON response from ${path}:`, responseText);
    throw new Error(`API call to ${path} returned invalid JSON.`);
  }
}

export async function search(query: string) {
  logger.log(`search ${query}`);
  const searchParams = new URLSearchParams({ q: query });
  const result = await fetchApi(`/api/search?${searchParams.toString()}`)
  logger.log(`search returned results: ${result.toString()}`)
  return result ;
}

export async function getMovies() {
  logger.log(`getMovies`);
  return fetchApi('/api/movies');
}