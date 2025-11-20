
import { content as localContent } from '@/data/content';
import { getMovies } from './api';
import { logger } from '@/lib/logger';

const dataSource = 'remote';

export async function getContent() {
  
  if (dataSource === 'remote') {
    logger.log(`getContent from remote`)
    const movies = await getMovies();
    return { movies };
  } else {
    
    return localContent;
  }
}
