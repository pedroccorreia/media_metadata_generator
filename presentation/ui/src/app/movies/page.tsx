
import Link from 'next/link';
import { getContent } from '@/lib/data';
import { MovieCard } from '@/components/movie-card';
import { logger } from '@/lib/logger';

export const dynamic = 'force-dynamic'

export default async function MoviesPage() {
  logger.log('Rendering MoviesPage...');
  const content = await getContent();
  const movies = content.movies;
  logger.log(`MoviesPage received ${movies.length} videos.`);

  return (
    <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="mb-8">
        <h1 className="text-4xl font-extrabold tracking-tight">All Movies</h1>
        <p className="text-muted-foreground mt-2">
          Browse our collection and discover amazing shorts.
        </p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4 md:gap-6">
        {movies.map((movie) => (
          <MovieCard key={movie.id} movie={movie} />
        ))}
      </div>
    </div>
  );
}
