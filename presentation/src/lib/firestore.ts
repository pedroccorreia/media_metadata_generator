import type { Movie } from './types';

export async function getMovies(): Promise<Movie[]> {
  const url = `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/movies`;
  console.log(`Fetching movies from ${url}...`);
  try {
    const response = await fetch(url);
    if (!response.ok) {
      console.error('Failed to fetch movies:', response.status, response.statusText);
      throw new Error('Failed to fetch movies');
    }
    const movies = await response.json();
    console.log(`Received ${movies.length} movies.`);
    return movies;
  } catch (error) {
    console.error('Error fetching movies:', error);
    return [];
  }
}