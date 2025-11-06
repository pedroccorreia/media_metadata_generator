'use server';
/**
 * @fileOverview A movie chat agent that uses grounded search.
 *
 * - movieChat - A function that handles the movie chat process.
 * - MovieChatInput - The input type for the movieChat function.
 * - MovieChatOutput - The return type for the movieChat function.
 */

// import { ai } from '@/ai/genkit';
import { vertexAI } from '@genkit-ai/vertexai';
import { genkit } from 'genkit';

import { z } from 'zod';

const ai = genkit({
  plugins: [vertexAI({ location: 'us-central1', projectId : 'yoursampleprojectid' })],
});

const MovieChatInputSchema = z.object({
  query: z.string().describe('The user\'s query.'),
  history: z.array(z.object({
    role: z.enum(['user', 'assistant']),
    content: z.string(),
  })).optional().describe('The conversation history.'),
});
export type MovieChatInput = z.infer<typeof MovieChatInputSchema>;

const MovieChatOutputSchema = z.object({
  answer: z.string().describe('The answer to the user\'s query.'),
});
export type MovieChatOutput = z.infer<typeof MovieChatOutputSchema>;

export async function movieChat(input: MovieChatInput): Promise<MovieChatOutput> {
  const history = (input.history || []).map(message => ({
      role: message.role === 'assistant' ? 'model' as const : 'user' as const,
      content: [{text: message.content}]
  }));

  console.log('Chat prompt '+ input.query)
  let output;
  try {
    const result = await ai.generate({
      model: vertexAI.model('gemini-2.5-flash'),
      prompt: 'You are a media expert you give users short answer and ground it on the data whenever possible. User question: '+ input.query,
    })
    

    output = result.text;
  } catch (error) {
    console.error('Error during AI generation:', error);
    throw error; // Re-throw the error after logging
  }
  
  if (!output) {

      throw new Error('The AI model did not return a valid response.');
  }

  return { answer: output };
}
