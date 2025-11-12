
'use client';

import { useState, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import { VideoPlayer } from '@/components/video-player';
import type { ShortWithMovieInfo } from '@/lib/types';

interface InspireMeClientPageProps {
  shorts: ShortWithMovieInfo[];
}

export function InspireMeClientPage({ shorts }: InspireMeClientPageProps) {
  const searchParams = useSearchParams();
  const startId = searchParams.get('id');
  const [orderedShorts, setOrderedShorts] = useState<ShortWithMovieInfo[]>([]);

  // The key is to run the randomization only on the client, after hydration.
  useEffect(() => {
    if (!shorts || shorts.length === 0) {
      setOrderedShorts([]);
      return;
    }

    let shortsToDisplay: ShortWithMovieInfo[] = [];
    if (startId) {
      const startIndex = shorts.findIndex((short) => short.id === startId);
      if (startIndex !== -1) {
        const startShort = shorts[startIndex];
        const restOfShorts = shorts.filter((s) => s.id !== startId);
        // This shuffling now happens only on the client
        const shuffledRest = restOfShorts.sort(() => Math.random() - 0.5);
        shortsToDisplay = [startShort, ...shuffledRest];
      } else {
        // If startId is invalid, shuffle everything
        shortsToDisplay = [...shorts].sort(() => Math.random() - 0.5);
      }
    } else {
      // If no startId, shuffle everything
      shortsToDisplay = [...shorts].sort(() => Math.random() - 0.5);
    }
    setOrderedShorts(shortsToDisplay);
  }, [startId, shorts]);

  if (!shorts || shorts.length === 0) {
    return (
      <div className="h-screen w-screen bg-black flex items-center justify-center text-white">
        <div className="text-center p-4">
            <h2 className="text-2xl font-bold mb-2">No shorts found</h2>
            <p className="text-muted-foreground">There are no shorts available to watch.</p>
        </div>
      </div>
    );
  }

  // Before the client-side effect runs, `orderedShorts` is empty.
  // We render a loading state to prevent the hydration error.
  if (orderedShorts.length === 0) {
    return (
       <div className="h-screen w-screen bg-black flex items-center justify-center text-white">
        Loading What to Watch...
      </div>
    )
  }

  return (
    <div className="h-screen w-screen snap-y snap-mandatory overflow-y-scroll overflow-x-hidden bg-black">
      {orderedShorts.map((short, index) => (
        <div key={short.id} className="h-full w-full snap-center flex items-center justify-center relative p-4 md:p-8 lg:p-16">
          <VideoPlayer short={short} isFirst={index === 0} />
        </div>
      ))}
    </div>
  );
}
