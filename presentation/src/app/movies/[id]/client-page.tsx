

'use client';

import { useState, useEffect, useRef, useMemo } from 'react';
import Image from 'next/image';
import { ShortListItem } from '@/components/short-list-item';
import { AddShortWizard } from '@/components/add-short-wizard';
import type { Movie, Short, Character, Person, Section, Utterance, TranscriptionWord } from '@/lib/types';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { PlusCircle, User, ThumbsUp, Tag, BookOpen, Clapperboard, Type, PlayCircle, Loader2, Search as SearchIcon, X, FileText, ChevronDown, ChevronUp, Bot } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Table,
  TableHeader,
  TableHead,
  TableRow,
  TableBody,
  TableCell
} from '@/components/ui/table';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { MovieChat } from '@/components/movie-chat';

const CategorySection = ({ title, items, icon }: { title: string; items: (string | Person)[] | undefined; icon: React.ReactNode }) => {
  if (!items || items.length === 0) return null;

  const renderItem = (item: string | Person) => {
    if (typeof item === 'string') {
        return item;
    }
    // This is for the 'people' array which has a different structure
    if ('person' in item) { 
        return `${item.person} (${item.role})`;
    }
    return '';
  }

  return (
    <div>
        <h3 className="text-xl font-semibold flex items-center gap-2 mb-3">
            {icon}
            {title}
        </h3>
        <div className="flex flex-wrap gap-2">
            {items.map((item, index) => (
            <Badge key={index} variant="secondary" className="text-sm">
                {renderItem(item)}
            </Badge>
            ))}
        </div>
    </div>
  );
};

const CharacterTable = ({ characters }: { characters: Character[] | undefined }) => {
    if (!characters || characters.length === 0) return null;

    return (
        <div>
            <h3 className="text-xl font-semibold flex items-center gap-2 mb-3">
                <User />
                Characters
            </h3>
            <Card>
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead>Name</TableHead>
                            <TableHead>Description</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {characters.map((character, index) => (
                            <TableRow key={index}>
                                <TableCell className="font-medium">{character.name}</TableCell>
                                <TableCell>{character.description}</TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </Card>
        </div>
    );
};

const parseTimeToSeconds = (time: string | number): number => {
    if (typeof time === 'number') return time;
    if (!time || typeof time !== 'string') return 0;
    const parts = time.split(/[:.]/).map(part => parseInt(part, 10));
    // Handles HH:MM:SS.ms, MM:SS:ms, and MM:SS
    if (parts.length >= 2) {
      if (parts.length >= 3) {
         const [p1, p2, p3] = parts;
         // Handle MM:SS:ms format
         if (p1 <= 59 && p2 <= 59) {
             return (p1 * 60) + p2;
         }
         // Handle HH:MM:SS format
         return (p1 * 3600) + (p2 * 60) + p3;
      }
      // MM:SS
      const [minutes, seconds] = parts;
      return (minutes * 60) + seconds;
    }
    return 0; // Default case
};


const formatTime = (timeInSeconds: number): string => {
    if (isNaN(timeInSeconds) || timeInSeconds < 0) return '00:00';
    const minutes = Math.floor(timeInSeconds / 60);
    const seconds = Math.floor(timeInSeconds % 60);
    return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
};

const formatTimeFromParts = (time: string | number): string => {
    if (typeof time === 'number') {
        return formatTime(time);
    }
    if (!time || typeof time !== 'string') return '00:00';
    const parts = time.split(':');
    if (parts.length >= 2) {
        return `${parts[0]}:${parts[1]}`;
    }
    return time;
};


const ChapterTable = ({ sections, onSeek }: { sections: Section[] | undefined, onSeek: (time: number, displayTime: string, segment: number) => void }) => {
    const [searchQuery, setSearchQuery] = useState('');
    const [typeFilter, setTypeFilter] = useState<string | null>(null);
    const [filteredSections, setFilteredSections] = useState(sections || []);

    const chapterTypes = useMemo(() => {
        if (!sections) return [];
        const types = sections.map(s => s.type);
        return [...new Set(types)];
    }, [sections]);

    useEffect(() => {
        if (!sections) return;

        let newFilteredSections = sections;

        if (typeFilter) {
            newFilteredSections = newFilteredSections.filter(s => s.type === typeFilter);
        }

        if (searchQuery) {
            newFilteredSections = newFilteredSections.filter(s =>
                (s.reason || s.summary || '').toLowerCase().includes(searchQuery.toLowerCase())
            );
        }

        setFilteredSections(newFilteredSections);
    }, [searchQuery, typeFilter, sections]);

    if (!sections || sections.length === 0) return null;

    return (
        <div>
            <h2 className="text-3xl font-bold tracking-tight mb-6">Chapters</h2>

            <div className="flex flex-col sm:flex-row gap-4 mb-6">
                <div className="relative w-full sm:max-w-xs">
                    <Input
                        placeholder="Search descriptions..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="pl-10"
                    />
                    <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                </div>
                <div className="flex flex-wrap gap-2 items-center">
                     <p className="text-sm font-medium text-muted-foreground">Filter by type:</p>
                    {chapterTypes.map(type => (
                        <Button
                            key={type}
                            variant={typeFilter === type ? 'default' : 'outline'}
                            size="sm"
                            onClick={() => setTypeFilter(typeFilter === type ? null : type)}
                            className="capitalize"
                        >
                            {type.replace(/_/g, ' ')}
                            {typeFilter === type && <X className="ml-2 h-4 w-4" />}
                        </Button>
                    ))}
                </div>
            </div>

            <Card>
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead className="w-[100px]">Segment</TableHead>
                            <TableHead className="w-[120px]">Start Time</TableHead>
                            <TableHead className="w-[120px]">End Time</TableHead>
                            <TableHead className="w-[150px]">Type</TableHead>
                            <TableHead>Description</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {filteredSections.map((section, index) => (
                            <TableRow key={index}>
                                <TableCell>
                                    <Button variant="link" className="p-0" onClick={() => onSeek(parseTimeToSeconds(section.start_time), formatTimeFromParts(section.start_time), index + 1)}>
                                        {index + 1}
                                    </Button>
                                </TableCell>
                                <TableCell className="font-mono">
                                    {formatTimeFromParts(section.start_time)}
                                </TableCell>
                                <TableCell className="font-mono">{formatTimeFromParts(section.end_time)}</TableCell>
                                <TableCell><Badge variant="outline">{section.type}</Badge></TableCell>
                                <TableCell>{section.reason || section.summary}</TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
                 {filteredSections.length === 0 && (
                    <div className="text-center p-10 text-muted-foreground">
                        No chapters found matching your criteria.
                    </div>
                )}
            </Card>
        </div>
    );
};

const TranscriptionView = ({ words, onSeek }: { words: TranscriptionWord[] | undefined; onSeek: (time: number, displayTime: string, segment: number) => void }) => {
    const [searchQuery, setSearchQuery] = useState('');
    const [isExpanded, setIsExpanded] = useState(false);

    const highlightedWords = useMemo(() => {
        if (!words) return [];
        if (!searchQuery) return words.map(w => ({ ...w, highlighted: false }));

        const query = searchQuery.toLowerCase();
        return words.map(w => ({
            ...w,
            highlighted: w.word.toLowerCase().includes(query)
        }));
    }, [words, searchQuery]);
    
    if (!words || words.length === 0) {
        return (
            <div className="text-center py-10 border-2 border-dashed rounded-lg">
                <FileText className="mx-auto h-12 w-12 text-muted-foreground" />
                <h3 className="mt-4 text-lg font-semibold">No transcription available</h3>
                <p className="mt-1 text-sm text-muted-foreground">The transcription for this video could not be loaded.</p>
            </div>
        );
    }

    const getWordTime = (word: TranscriptionWord) => {
        return (word.start_time?.seconds || 0) + (word.start_time?.nanos || 0) / 1e9;
    };

    const WordComponent = ({ word, index }: { word: (typeof highlightedWords)[0], index: number }) => {
        const time = getWordTime(word);
        return (
            <span
                key={index}
                onClick={() => onSeek(time, formatTime(time), 0)}
                className={`cursor-pointer transition-colors duration-200 hover:text-primary hover:bg-primary/10 rounded px-1 py-0.5 ${word.highlighted ? 'bg-primary/20 text-primary' : ''}`}
            >
                {word.word}{' '}
            </span>
        );
    };

    return (
        <div>
            <h2 className="text-3xl font-bold tracking-tight mb-6">Transcription</h2>
            <div className="flex flex-col sm:flex-row gap-4 mb-6">
                 <div className="relative w-full sm:max-w-xs">
                    <Input
                        placeholder="Search transcription..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="pl-10"
                    />
                    <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                </div>
            </div>

            <Card>
                <CardContent className="p-6 relative">
                     <div className={`text-lg leading-relaxed ${!isExpanded ? 'max-h-48 overflow-hidden' : ''}`}>
                        <p>
                        {highlightedWords.map((word, index) => (
                            <WordComponent key={index} word={word} index={index} />
                        ))}
                        </p>
                    </div>
                    {!isExpanded && (
                         <div className="absolute bottom-6 left-6 right-6 h-24 bg-gradient-to-t from-card to-transparent pointer-events-none" />
                    )}
                    <div className="flex justify-center pt-4">
                        <Button
                            variant="link"
                            onClick={() => setIsExpanded(!isExpanded)}
                        >
                            {isExpanded ? (
                                <>
                                 <ChevronUp className="mr-2" />
                                 Show Less
                                </>
                            ) : (
                                <>
                                <ChevronDown className="mr-2" />
                                Show More
                                </>
                            )}
                        </Button>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
};


interface LoadingState {
    isLoading: boolean;
    segment: number;
    timestamp: string;
}

export function MovieClientPage({ movie }: { movie: Movie }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [loadingState, setLoadingState] = useState<LoadingState>({ isLoading: false, segment: 0, timestamp: '00:00' });
  const loadingTimeoutRef = useRef<NodeJS.Timeout | null>(null);


  const handleAddShort = (newShort: Short) => {
    // This functionality is now deprecated as shorts are derived from `previews`
  };

  const handleSeekTo = (timeInSeconds: number, displayTime: string, segment: number) => {
      const video = videoRef.current;
      if (video) {
          setLoadingState({ isLoading: true, segment: segment, timestamp: displayTime });
          
          const onSeeked = () => {
              video.play();
              if (loadingTimeoutRef.current) {
                  clearTimeout(loadingTimeoutRef.current);
              }
              loadingTimeoutRef.current = setTimeout(() => {
                  setLoadingState({ isLoading: false, segment: 0, timestamp: '00:00' });
              }, 1500); // Shorter delay after playback starts
              video.removeEventListener('seeked', onSeeked);
          };

          video.addEventListener('seeked', onSeeked, { once: true });
          video.currentTime = timeInSeconds;
      }
  };

  useEffect(() => {
      // Clear timeout on unmount
      return () => {
          if (loadingTimeoutRef.current) {
              clearTimeout(loadingTimeoutRef.current);
          }
      };
  }, []);

  return (
    <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="flex flex-col md:flex-row gap-8 md:gap-12 mb-12">
        <div className="w-full md:w-1/3 lg:w-1/4 flex-shrink-0">
          <Image
            src={movie.poster_url}
            alt={movie.file_name}
            data-ai-hint="movie poster"
            width={500}
            height={750}
            className="rounded-lg shadow-2xl w-full"
          />
        </div>
        <div className="flex-grow">
            <div className="flex justify-between items-start">
                <h1 className="text-4xl lg:text-5xl font-extrabold tracking-tight mb-4">
                    {movie.file_name}
                </h1>
                <Dialog>
                    <DialogTrigger asChild>
                        <Button variant="outline">
                            <Bot className="mr-2 h-5 w-5" />
                            Ask AI
                        </Button>
                    </DialogTrigger>
                    <DialogContent className="sm:max-w-2xl">
                        <DialogHeader>
                            <DialogTitle>Ask AI about {movie.file_name}</DialogTitle>
                            <DialogDescription>
                                You can ask questions about actors, plot points, reviews, or anything else you can think of.
                            </DialogDescription>
                        </DialogHeader>
                        <MovieChat
                            initialQuery={`Tell me more about the movie "${movie.file_name}". What is it about and who are the main actors?`}
                        />
                    </DialogContent>
                </Dialog>
            </div>
          <div className="flex flex-wrap gap-2 mb-4">
            {movie.summary.video_mood?.map(mood => <Badge key={mood} variant="secondary">{mood}</Badge>)}
          </div>
          <p className="text-lg text-muted-foreground mt-4">
            {movie.summary.summary}
          </p>
        </div>
      </div>

       <div className="mb-12">
            <h2 className="text-3xl font-bold tracking-tight mb-4">Full Video</h2>
            <div className="relative aspect-video w-full bg-black rounded-lg overflow-hidden">
                <video
                    ref={videoRef}
                    src={movie.public_url}
                    controls
                    className="w-full h-full"
                />
                 {loadingState.isLoading && (
                    <div className="absolute inset-0 flex items-center justify-center bg-black/60 backdrop-blur-sm transition-opacity duration-300 z-10">
                        <div className="flex flex-col items-center gap-4 text-white">
                            <Loader2 className="h-10 w-10 animate-spin" />
                            <p className="text-lg font-semibold">
                                {loadingState.segment > 0 ? `Loading segment ${loadingState.segment}`: 'Seeking to time'}
                            </p>
                            <p className="text-2xl font-mono bg-black/50 px-3 py-1 rounded-md">
                                {loadingState.timestamp}
                            </p>
                        </div>
                    </div>
                )}
            </div>
        </div>
      
      <Tabs defaultValue="shorts" className="w-full">
        <TabsList className="grid w-full grid-cols-4 max-w-lg mb-6">
            <TabsTrigger value="shorts">Shorts</TabsTrigger>
            <TabsTrigger value="chapters">Chapters</TabsTrigger>
            <TabsTrigger value="transcription">Transcription</TabsTrigger>
            <TabsTrigger value="categorization">Categorization</TabsTrigger>
        </TabsList>
        <TabsContent value="shorts">
            <div className="flex justify-between items-center mb-6">
                <h2 className="text-3xl font-bold tracking-tight">Shorts</h2>
                <AddShortWizard movie={movie} onAddShort={handleAddShort}>
                    <Button disabled>
                    <PlusCircle className="mr-2 h-5 w-5" />
                    Add Short (Auto-generated)
                    </Button>
                </AddShortWizard>
            </div>
            <div className="flex flex-col gap-4">
                {movie.previews.clips.map((clip, index) => (
                    <ShortListItem key={`${movie.id}-short-${index}`} short={{
                        id: `${movie.id}-short-${index}`,
                        title: clip.summary,
                        description: clip.user_description,
                        startTime: clip.start_timecode,
                        endTime: clip.end_timecode,
                        videoUrl: movie.public_url,
                        thumbnailUrl: movie.poster_url, // Use main poster as fallback
                        categories: clip.emotions_triggered,
                    }} />
                ))}
                {movie.previews.clips.length === 0 && (
                    <div className="text-center py-10 border-2 border-dashed rounded-lg">
                    <p className="text-muted-foreground">No shorts have been generated for this movie yet.</p>
                    </div>
                )}
            </div>
        </TabsContent>
         <TabsContent value="chapters">
            <ChapterTable sections={movie.summary.sections} onSeek={handleSeekTo}/>
        </TabsContent>
        <TabsContent value="transcription">
            <TranscriptionView words={movie.transcription?.words} onSeek={handleSeekTo} />
        </TabsContent>
        <TabsContent value="categorization">
             <h2 className="text-3xl font-bold tracking-tight mb-6">Details</h2>
            <Card>
                <CardContent className="p-6 space-y-8">
                    <CharacterTable characters={movie.summary.character} />
                    <CategorySection title="Video Mood" items={movie.summary.video_mood} icon={<ThumbsUp />} />
                    <CategorySection title="Themes" items={movie.summary.theme} icon={<BookOpen />} />
                    <CategorySection title="Subjects" items={movie.summary.subject} icon={<Tag />} />
                    <CategorySection title="Practices" items={movie.summary.practice} icon={<Clapperboard />} />
                </CardContent>
            </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
