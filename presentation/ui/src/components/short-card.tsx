
'use client';

import Link from 'next/link';
import Image from 'next/image';
import { Card, CardContent } from '@/components/ui/card';
import type { ShortWithMovieInfo } from '@/lib/types';
import { PlayCircle } from 'lucide-react';
import { useRef, useEffect, useState } from 'react';

interface ShortCardProps {
  short: ShortWithMovieInfo;
}

const parseTime = (time: string | number | undefined): number | undefined => {
  if (time === undefined || time === null) return undefined;
  if (typeof time === 'number') return time;
  if (typeof time === 'string') {
    // Format is MM:SS:ms.us - we only care about MM and SS
    const parts = time.split(':').map(part => parseInt(part, 10));
    if (parts.length >= 2) {
        const minutes = parts[0] || 0;
        const seconds = parts[1] || 0;
        return (minutes * 60) + seconds;
    }
  }
  return undefined;
};


export function ShortCard({ short }: ShortCardProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isHovering, setIsHovering] = useState(false);
  const startTime = parseTime(short.startTime) ?? 0;
  const endTime = parseTime(short.endTime);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const setStartTime = () => {
      if (video.readyState >= 1) { // HAVE_METADATA or more
        video.currentTime = startTime;
      }
    };
    
    // Set time if metadata is already loaded
    if (video.readyState >= 1) {
      setStartTime();
    } else {
      // Otherwise, wait for it to load
      video.addEventListener('loadedmetadata', setStartTime, { once: true });
    }
    
    return () => {
      video.removeEventListener('loadedmetadata', setStartTime);
    };
  }, [startTime]);

  const handleMouseEnter = () => {
    setIsHovering(true);
    const video = videoRef.current;
    if (video) {
        // Ensure we're starting from the right place, especially after a pause.
        if (video.currentTime < startTime || (endTime && video.currentTime >= endTime)) {
            video.currentTime = startTime;
        }
        video.play().catch(error => console.error("Video play failed:", error));
    }
  };

  const handleMouseLeave = () => {
    setIsHovering(false);
    const video = videoRef.current;
    if (video) {
        video.pause();
    }
  };

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const handleTimeUpdate = () => {
      // If an end time is defined and the video passes it, loop back to the start.
      if (endTime && video.currentTime >= endTime) {
        video.currentTime = startTime;
      }
    };

    video.addEventListener('timeupdate', handleTimeUpdate);
    return () => {
      video.removeEventListener('timeupdate', handleTimeUpdate);
    };
  }, [startTime, endTime]);

  return (
    <Link href={`/inspire-me?id=${short.id}`} className="block group">
      <Card 
        className="overflow-hidden transition-all duration-300 ease-in-out hover:shadow-primary/20 hover:shadow-lg hover:-translate-y-1 border-transparent bg-transparent"
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
      >
        <CardContent className="p-0">
          <div className="relative aspect-video overflow-hidden rounded-lg">
             <Image
                src={short.movie.poster_url}
                alt={short.title}
                fill
                data-ai-hint="movie scene"
                className={`object-cover w-full h-full transition-opacity duration-300 group-hover:scale-105 ${isHovering ? 'opacity-0' : 'opacity-100'}`}
             />
            <video
              ref={videoRef}
              src={short.videoUrl}
              muted
              playsInline
              loop={!endTime} // Use native loop only if no custom end time is set
              preload="metadata"
              className={`object-cover w-full h-full transition-opacity duration-300 group-hover:scale-105 ${isHovering ? 'opacity-100' : 'opacity-0'}`}
            ></video>
            <div className="absolute inset-0 bg-black/20 group-hover:bg-black/40 transition-all duration-300 flex items-center justify-center">
              <PlayCircle className={`h-12 w-12 text-white/70 transition-all duration-300 ${isHovering ? 'opacity-0 scale-75' : 'group-hover:text-white group-hover:scale-110'}`} />
            </div>
          </div>
          <div className="pt-3">
            <p className="font-semibold text-sm text-foreground group-hover:text-primary transition-colors truncate">{short.movie.file_name}</p>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}

    