'use server';
/**
 * @fileOverview This file defines a Genkit flow for automatically generating engaging descriptions for shorts.
 *
 * - curateShortDescription - A function that takes short content and generates a description.
 * - CurateShortDescriptionInput - The input type for the curateShortDescription function.
 * - CurateShortDescriptionOutput - The return type for the curateShortDescription function.
 */

import {ai} from '@/ai/genkit';
import {z} from 'genkit';

const CurateShortDescriptionInputSchema = z.object({
  shortContent: z.string().describe('The content of the short video.'),
});
export type CurateShortDescriptionInput = z.infer<typeof CurateShortDescriptionInputSchema>;

const CurateShortDescriptionOutputSchema = z.object({
  description: z.string().describe('An engaging description of the short video.'),
});
export type CurateShortDescriptionOutput = z.infer<typeof CurateShortDescriptionOutputSchema>;

export async function curateShortDescription(input: CurateShortDescriptionInput): Promise<CurateShortDescriptionOutput> {
  return curateShortDescriptionFlow(input);
}

const curateShortDescriptionPrompt = ai.definePrompt({
  name: 'curateShortDescriptionPrompt',
  input: {schema: CurateShortDescriptionInputSchema},
  output: {schema: CurateShortDescriptionOutputSchema},
  prompt: `You are an expert in creating engaging descriptions for short videos.

  Based on the content of the short video, generate a description that will entice users to watch it.

  Short Content: {{{shortContent}}}`,
});

const curateShortDescriptionFlow = ai.defineFlow(
  {
    name: 'curateShortDescriptionFlow',
    inputSchema: CurateShortDescriptionInputSchema,
    outputSchema: CurateShortDescriptionOutputSchema,
  },
  async input => {
    const {output} = await curateShortDescriptionPrompt(input);
    return output!;
  }
);
