
'use client';

import Link from 'next/link';
import { Card, CardContent } from '@/components/ui/card';
import type { Short } from '@/lib/types';
import { PlayCircle } from 'lucide-react';
import { useRef, useEffect, useState } from 'react';
import { Badge } from '@/components/ui/badge';

interface ShortListItemProps {
  short: Short;
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


export function ShortListItem({ short }: ShortListItemProps) {
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
    
    if (video.readyState >= 1) {
      setStartTime();
    } else {
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
    <Card 
      className="overflow-hidden transition-all duration-300 ease-in-out hover:shadow-primary/20 hover:shadow-lg border-transparent hover:border-primary/50"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      <Link href={`/inspire-me?id=${short.id}`} className="block group">
        <CardContent className="p-0 flex flex-col md:flex-row">
          <div className="w-full md:w-2/3 relative aspect-video">
              <video
                ref={videoRef}
                src={short.videoUrl}
                muted
                playsInline
                loop={!endTime}
                preload="metadata"
                className="object-cover w-full h-full"
              ></video>
              <div className="absolute inset-0 bg-black/20 group-hover:bg-black/40 transition-all duration-300 flex items-center justify-center">
                <PlayCircle className={`h-12 w-12 text-white/70 transition-all duration-300 ${isHovering ? 'opacity-0 scale-75' : 'group-hover:text-white group-hover:scale-110'}`} />
              </div>
          </div>
          <div className="w-full md:w-1/3 p-4 flex flex-col justify-center">
            <h3 className="font-semibold text-lg text-foreground mb-2 group-hover:text-primary transition-colors">
              {short.title}
            </h3>
            <p className="text-sm text-muted-foreground line-clamp-3 mb-3">{short.description}</p>
             {short.categories && short.categories.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {short.categories.map((category) => (
                  <Badge
                    key={category}
                    variant="secondary"
                    className="bg-secondary text-secondary-foreground"
                  >
                    {category}
                  </Badge>
                ))}
              </div>
            )}
          </div>
        </CardContent>
      </Link>
    </Card>
  );
}

    