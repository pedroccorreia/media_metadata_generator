
import { Suspense } from 'react';
import { InspireMeClientPage } from './client-page';
import { getContent } from '@/lib/data';
import type { Short, ShortWithMovieInfo, Movie } from '@/lib/types';

// Helper to convert a Clip to a Short
const clipToShort = (clip: any, index: number, movie: Movie): Short => ({
  id: `${movie.id}-short-${index}`,
  title: clip.summary,
  description: clip.user_description,
  startTime: clip.start_timecode,
  endTime: clip.end_timecode,
  videoUrl: movie.public_url,
  thumbnailUrl: movie.poster_url, // Use main poster as fallback
  categories: clip.emotions_triggered,
});

export default async function InspireMePage() {
  const content = await getContent();
  const shorts: ShortWithMovieInfo[] = content.movies.flatMap((movie) =>
    (movie.previews?.clips || []).map((clip, index) => {
      const short = clipToShort(clip, index, movie);
      return {
        ...short,
        movie: {
          id: movie.id,
          file_name: movie.file_name,
          poster_url: movie.poster_url,
        },
      };
    })
  );

  return (
    <Suspense
      fallback={
        <div className="h-screen w-screen bg-black flex items-center justify-center text-white">
          Loading What to Watch...
        </div>
      }
    >
      <InspireMeClientPage shorts={shorts} />
    </Suspense>
  );
}
