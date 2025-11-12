import type { Movie } from './types';
import { logger } from '@/lib/logger';

export async function getMovies(): Promise<Movie[]> {
  const url = `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/movies`;
  logger.log(`Fetching movies from ${url}...`);
  try {
    const response = await fetch(url, { cache: 'no-store' });
    if (!response.ok) {
      logger.error('Failed to fetch movies:', response.status, response.statusText);
      throw new Error('Failed to fetch movies');
    }
    const movies = await response.json();
    logger.log(`Received ${movies.length} movies.`);
    return movies;
  } catch (error) {
    logger.error('Error fetching movies:', error);
    return [];
  }
}