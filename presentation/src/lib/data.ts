
import { content as localContent } from '@/data/content';
import { getMovies } from './firestore';
import type { Movie } from './types';
import { logger } from '@/lib/logger';

const dataSource = 'remote';

export async function getContent() {
  logger.log(`Fetching content from ${dataSource} data source...`);
  if (dataSource === 'remote') {
    logger.log("Using remote data source.");
    const movies = await getMovies();
    return { movies };
  } else {
    logger.log("Using local data source.");
    return localContent;
  }
}
