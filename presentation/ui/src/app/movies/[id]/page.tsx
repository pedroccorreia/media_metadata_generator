
import { getContent } from '@/lib/data';
import { notFound } from 'next/navigation';
import { MovieClientPage } from './client-page';
import type { Movie } from '@/lib/types';

export const dynamic = 'force-dynamic'

export default async function MovieDetailPage({ params }: { params: { id: string } }) {
  const content = await getContent();
  
  // This code will now work because params.id is known at build time
  const { id } = await params; 
  const movie = content.movies.find((m) => m.id === id) || null;

  if (!movie) {
    notFound();
  }

  // Sanitize the movie object to ensure it's a plain object for the client component.
  // This prevents errors with non-serializable data like Firestore Timestamps.
  const serializableMovie: Movie = JSON.parse(JSON.stringify(movie));

  return <MovieClientPage movie={serializableMovie} />;
}
