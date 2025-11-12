
import { content as localContent } from '@/data/content';
import { getMovies } from './firestore';
import type { Movie } from './types';

const dataSource = 'remote';

export async function getContent() {
  console.log(`Fetching content from ${dataSource} data source...`);
  if (dataSource === 'remote') {
    console.log("Using remote data source.");
    const movies = await getMovies();
    return { movies };
  } else {
    console.log("Using local data source.");
    return localContent;
  }
}
