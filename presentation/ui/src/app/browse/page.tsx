
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Swimlane } from '@/components/swimlane';
import { getContent } from '@/lib/data';
import type { Short, ShortWithMovieInfo, Movie } from '@/lib/types';
import { ArrowRight } from 'lucide-react';
import { Header } from '@/components/layout/header';
import { Footer } from '@/components/layout/footer';
import { logger } from '@/lib/logger';

export const dynamic = 'force-dynamic'

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

// Helper function to get a single random short for each movie that has shorts
const getShortsForSwimlane = (movies: Movie[], count: number): ShortWithMovieInfo[] => {
  const moviesWithShorts = movies.filter((movie) => movie.previews?.clips && movie.previews.clips.length > 0);
  
  // Shuffle the movies to ensure randomness
  const shuffledMovies = [...moviesWithShorts].sort(() => 0.5 - Math.random());

  return shuffledMovies.slice(0, count).map((movie) => {
    // Pick one random clip from the movie and convert it to a Short
    const randomClip = movie.previews.clips[Math.floor(Math.random() * movie.previews.clips.length)];
    const short = clipToShort(randomClip, 0, movie); // Index doesn't matter much here

    return {
      ...short,
      movie: {
        id: movie.id,
        file_name: movie.file_name,
        poster_url: movie.poster_url,
      },
    };
  });
};

export default async function BrowsePage() {
  logger.log('Rendering Browse page');
  const content = await getContent();
  const allShorts: ShortWithMovieInfo[] = content.movies.flatMap((movie) =>
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
  
  // A short to feature in the hero section
  const heroShort = allShorts.length > 0 ? allShorts[Math.floor(Math.random() * allShorts.length)] : null;

  const continueWatchingShorts = getShortsForSwimlane(content.movies, 2);
  const recommendedShorts = getShortsForSwimlane(content.movies, 10);
  const popularShorts = getShortsForSwimlane(content.movies, 10);
  const top10Shorts = getShortsForSwimlane(content.movies, 10);

  return (
    <>
      <div className="flex flex-col">
        <section className="relative w-full h-[30vh] flex items-center justify-center text-center overflow-hidden">
          {heroShort && (
             <div className="absolute inset-0 bg-black/50" />
          )}
          <div className="absolute inset-0 bg-gradient-to-b from-transparent to-background z-10" />
          <div className="relative z-20 flex flex-col items-center gap-4 px-4">
            <h1 className="text-4xl md:text-6xl lg:text-7xl font-extrabold tracking-tighter text-white">
              CineShorts
            </h1>
            <p className="max-w-2xl text-lg md:text-xl text-muted-foreground">
              Bite-sized stories from your favorite films. Reimagined.
            </p>
          </div>
        </section>

        <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-12 space-y-16">
          <Swimlane title="Continue Watching" shorts={continueWatchingShorts} />
          <Swimlane title="Recommended For You" shorts={recommendedShorts} />
          <Swimlane title="Most Popular" shorts={popularShorts} />
          <Swimlane title="Top 10" shorts={top10Shorts} />
        </div>
      </div>
    </>
  );
}
