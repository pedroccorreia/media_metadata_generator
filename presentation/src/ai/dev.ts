import { config } from 'dotenv';
config();

import '@/ai/flows/curate-short-descriptions.ts';
import '@/ai/flows/classify-shorts.ts';
import '@/ai/flows/suggest-short.ts';
import '@/ai/flows/movie-chat.ts';
import '@/ai/flows/search.ts';
