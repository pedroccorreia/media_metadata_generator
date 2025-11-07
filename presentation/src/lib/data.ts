
import { content as localContent } from '@/data/content';
import { getMovies } from './firestore';
import type { Movie } from './types';

// const dataSource = process.env.DATA_SOURCE || 'local';
const dataSource = 'remote';

let contentPromise: Promise<{ movies: Movie[] }>;

// console.log("env variable %s", process.env.DATA_S0OURCE)

if (dataSource === 'remote') {
  
  console.log("Using remote data source.");
  contentPromise = getMovies().then(movies => ({ movies }));
} else {
  console.log("Using local data source.");
  contentPromise = Promise.resolve(localContent);
}

export async function getContent() {
  console.log(`Fetching content from ${dataSource} data source...`);
  const content = await contentPromise;
  console.log(`Fetched ${content.movies.length} movies.`);
  return content;
}
