
import { z } from 'zod';

export interface Clip {
  summary: string;
  user_description: string;
  end_timecode: string;
  start_timecode: string;
  emotions_triggered: string[];
}

export interface Short {
  id: string;
  title: string;
  videoUrl: string;
  description: string;
  thumbnailUrl: string;
  startTime?: string | number;
  endTime?: string | number;
  categories?: string[];
}

export interface Character {
    name: string;
    description: string;
}

export interface Person {
    role: string;
    person: string;
}

export interface Section {
    reason?: string;
    summary?: string;
    start_time: string;
    end_time: string;
    type: string;
}

export interface Utterance {
    start: number;
    end: number;
    transcript: string;
}

export interface TranscriptionWord {
    word: string;
    start_time: { seconds: number; nanos: number };
    end_time: { seconds: number; nanos: number };
}

export interface Transcription {
    status: string;
    error_message?: string;
    utterances?: Utterance[]; // Keep for backwards compatibility if some data uses it
    text?: string;
    words?: TranscriptionWord[];
}


export interface MovieSummary {
  summary: string;
  video_mood: string[];
  subject_topics: string[];
  character?: Character[];
  practice?: string[];
  subject?: string[];
  theme?: string[];
  people?: Person[];
  sections?: Section[];
}

export interface MoviePreviews {
  clips: Clip[];
}

export interface Movie {
  id: string;
  file_name: string;
  poster_url: string;
  public_url: string;
  summary: MovieSummary;
  previews: MoviePreviews;
  transcription?: Transcription;
  is_dummy?: boolean;
  contentType: 'tv_show' | 'movie' | 'sports' | 'highlight';
}

export interface ShortWithMovieInfo extends Short {
  movie: {
    id: string;
    file_name: string;
    poster_url: string;
  };
}

// Search Schemas
export const SearchInputSchema = z.object({
    query: z.string().describe('The search query from the user.'),
});
export type SearchInput = z.infer<typeof SearchInputSchema>;

export const SearchResultSchema = z.object({
    title: z.string(),
    url: z.string(),
    snippet: z.string().optional(),
    posterUrl: z.string().optional(),
});
export type SearchResult = z.infer<typeof SearchResultSchema>;

export const SearchOutputSchema = z.object({
  summary: z.string().describe('A summary of the search results.'),
  results: z.array(SearchResultSchema),
  rawResponse: z.any().optional().describe('The full raw response from the search API.'),
});
export type SearchOutput = z.infer<typeof SearchOutputSchema>;
