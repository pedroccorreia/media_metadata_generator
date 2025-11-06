import {genkit} from 'genkit';
import {googleAI} from '@genkit-ai/googleai';
import {vertexAI} from '@genkit-ai/vertexai';

export const ai = genkit({
  plugins: [
    googleAI(), // Required for listing models
    vertexAI({
      location: 'us-central1', // Or any other supported region.
    }),
  ],
});
