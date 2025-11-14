
'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import type { ShortWithMovieInfo } from '@/lib/types';
import { Volume2, VolumeX, Play, VideoOff } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

interface VideoPlayerProps {
  short: ShortWithMovieInfo;
  isFirst?: boolean;
}

const parseTime = (time: string | number | undefined): number | undefined => {
  if (time === undefined || time === null) return undefined;
  if (typeof time === 'number') return time;
  if (typeof time === 'string') {
    // Format is MM:SS:ms.us or similar - we only care about MM and SS
    const parts = time.split(':').map(part => parseInt(part, 10));
    if (parts.length >= 2) {
        const minutes = parts[0] || 0;
        const seconds = parts[1] || 0;
        return (minutes * 60) + seconds;
    }
  }
  return undefined;
};


export function VideoPlayer({ short, isFirst = false }: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [isPlaying, setIsPlaying] = useState(isFirst);
  const [isMuted, setIsMuted] = useState(false); // Sound on by default
  const [videoError, setVideoError] = useState(false);

  // Standardize the URL by removing any query parameters like authuser
  const cleanVideoUrl = short.videoUrl.split('?')[0];

  const startTime = parseTime(short.startTime);
  const endTime = parseTime(short.endTime);

  const handleVideoError = (e: React.SyntheticEvent<HTMLVideoElement, Event>) => {
    console.error('Video Error:', {
        message: "Failed to load video.",
        short,
        errorEvent: e.nativeEvent
    });
    setVideoError(true);
    setIsPlaying(false);
  };
  
  const playVideo = useCallback(() => {
    const video = videoRef.current;
    if (video && !videoError) {
      if (startTime !== undefined && (video.currentTime < startTime || (endTime !== undefined && video.currentTime >= endTime))) {
        video.currentTime = startTime;
      }
      video.play().catch(error => {
          // Autoplay with sound often fails. We can try to play muted as a fallback.
          if (error.name === 'NotAllowedError' && video.muted === false) {
              console.warn('Autoplay with sound failed. Retrying muted.');
              video.muted = true;
              setIsMuted(true);
              video.play().catch(err => {
                 console.error("Video play failed even when muted:", err);
                 setIsPlaying(false);
              })
          } else {
            console.error("Video play failed:", error);
            setIsPlaying(false);
          }
      });
      setIsPlaying(true);
    }
  }, [startTime, endTime, videoError]);

  const pauseVideo = useCallback(() => {
    const video = videoRef.current;
    if (video) {
      video.pause();
      setIsPlaying(false);
    }
  }, []);

  // Intersection Observer for auto-play/pause
  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          playVideo();
        } else {
          pauseVideo();
        }
      },
      {
        threshold: 0.5, // Play when at least 50% of the video is visible
      }
    );

    const currentContainer = containerRef.current;
    if (currentContainer) {
      observer.observe(currentContainer);
    }

    return () => {
      if (currentContainer) {
        observer.unobserve(currentContainer);
      }
    };
  }, [playVideo, pauseVideo]);

  // Set initial start time
  useEffect(() => {
    const video = videoRef.current;
    if (!video || startTime === undefined) return;

    const setupVideo = () => {
      video.currentTime = startTime;
    };
    
    if (video.readyState >= 1) { // HAVE_METADATA
        setupVideo();
    } else {
        video.addEventListener('loadedmetadata', setupVideo, { once: true });
    }
    
    return () => video.removeEventListener('loadedmetadata', setupVideo);
  }, [startTime]);

  // Loop functionality
  useEffect(() => {
    const video = videoRef.current;
    if (!video || startTime === undefined || endTime === undefined) return;

    const handleTimeUpdate = () => {
        if (video.currentTime >= endTime) {
            video.currentTime = startTime;
            if (!isPlaying) {
                // If it was paused when it ended, keep it paused at the start
                video.pause();
            }
        }
    };
    video.addEventListener('timeupdate', handleTimeUpdate);
    return () => video.removeEventListener('timeupdate', handleTimeUpdate);
  }, [startTime, endTime, isPlaying]);

  const togglePlay = () => {
    if (videoError) return;
    if (videoRef.current?.paused) {
      playVideo();
    } else {
      pauseVideo();
    }
  };

  const toggleMute = (e: React.MouseEvent) => {
    e.stopPropagation();
    const video = videoRef.current;
    if (video) {
      video.muted = !video.muted;
      setIsMuted(video.muted);
    }
  };

  return (
    <div ref={containerRef} className="relative h-full w-full">
      <video
        key={cleanVideoUrl} // Force re-render on short change
        ref={videoRef}
        src={cleanVideoUrl}
        muted={isMuted}
        playsInline
        loop={endTime === undefined} // Native loop only if no custom end time
        className="h-full w-full object-contain bg-black"
        // crossOrigin="use-credentials"
        onError={handleVideoError}
        onClick={togglePlay}
      >
        {/* Subtitles are not part of the new data structure yet */}
      </video>

      <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/60 to-transparent p-4 text-white pointer-events-none">
        <div className="flex items-center gap-3 mb-2 group pointer-events-auto w-fit">
          <Link href={`/movies/${short.movie.id}`} className="flex items-center gap-3">
            <div className="relative h-10 w-10 flex-shrink-0">
                <Image
                src={short.movie.poster_url}
                alt={short.movie.file_name}
                data-ai-hint="movie poster"
                fill
                className="rounded-full object-cover border-2 border-transparent group-hover:border-primary transition-all"
                />
            </div>
            <div className="font-semibold group-hover:text-primary transition-colors">{short.movie.file_name}</div>
          </Link>
        </div>
        <h3 className="text-lg font-bold">{short.title}</h3>
        <p className="text-sm text-gray-300 mb-2 line-clamp-2">{short.description}</p>
        {short.categories && short.categories.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {short.categories.map((category) => (
              <Badge
                key={category}
                variant="secondary"
                className="bg-white/20 text-white border-transparent backdrop-blur-sm"
              >
                {category}
              </Badge>
            ))}
          </div>
        )}
      </div>
      <div className="absolute top-4 right-4">
        <Button variant="ghost" size="icon" onClick={toggleMute} className="text-white bg-black/30 hover:bg-black/50 hover:text-white">
          {isMuted ? <VolumeX /> : <Volume2 />}
        </Button>
      </div>
       {videoError ? (
           <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/80 text-center p-4 sm:p-6 rounded-lg text-white pointer-events-none">
            <VideoOff className="h-12 w-12 text-destructive mb-4" />
            <p className="font-semibold text-base">This video could not be played.</p>
          </div>
        ) : !isPlaying && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div
            className="pointer-events-auto p-4 rounded-full bg-black/30 hover:bg-black/50 transition-colors cursor-pointer"
            aria-label="Play video"
            onClick={togglePlay}
          >
            <Play className="h-16 w-16 text-white/80" />
          </div>
        </div>
      )}
    </div>
  );
}
