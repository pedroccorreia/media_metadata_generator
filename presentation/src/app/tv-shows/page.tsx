
import Link from 'next/link';
import { getContent } from '@/lib/data';
import { MovieCard } from '@/components/movie-card';

export default async function TvShowsPage() {
  const content = await getContent();
  const tvShows = content.movies.filter(movie => movie.contentType === 'tv_show');

  return (
    <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="mb-8">
        <h1 className="text-4xl font-extrabold tracking-tight">TV Shows</h1>
        <p className="text-muted-foreground mt-2">
          Browse our collection of amazing TV shows.
        </p>
      </div>

      {tvShows.length > 0 ? (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4 md:gap-6">
          {tvShows.map((movie) => (
            <MovieCard key={movie.id} movie={movie} />
          ))}
        </div>
      ) : (
        <div className="flex items-center justify-center h-64 border-2 border-dashed rounded-lg">
            <p className="text-muted-foreground">No TV shows available at the moment.</p>
        </div>
      )}
    </div>
  );
}
