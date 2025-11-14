'use server';
/**
 * @fileOverview An AI agent that suggests new short video clips from a longer video.
 *
 * - suggestShort - A function that suggests a short video clip.
 * - SuggestShortInput - The input type for the suggestShort function.
 * - SuggestShortOutput - The return type for the suggestShort function.
 */

import {ai} from '@/ai/genkit';
import {z} from 'genkit';

const SuggestShortInputSchema = z.object({
  gcsUrl: z
    .string()
    .describe(
      "The full video as a Google Cloud Storage URI. Expected format: 'gs://<bucket>/<object>'"
    ),
  objective: z.string().describe('The user objective for the short. For example, "Find an action packed scene".'),
  existingShorts: z.array(z.object({
      title: z.string(),
      description: z.string(),
      startTime: z.union([z.string(), z.number()]),
      endTime: z.union([z.string(), z.number()]),
  })).describe('An array of shorts that have already been created from this video.'),
});

export type SuggestShortInput = z.infer<typeof SuggestShortInputSchema>;

const SuggestShortOutputSchema = z.object({
  title: z.string().describe('A compelling title for the new short.'),
  description: z.string().describe('A detailed, engaging description for the new short.'),
  startTime: z.string().describe('The start time of the short in MM:SS format.'),
  endTime: z.string().describe('The end time of the short in MM:SS format.'),
});

export type SuggestShortOutput = z.infer<typeof SuggestShortOutputSchema>;

export async function suggestShort(input: SuggestShortInput): Promise<SuggestShortOutput> {
  try {
    const result = await suggestShortFlow(input);
    return result;
  } catch (e) {
    console.error('Error in suggestShort flow:', e);
    throw new Error('Failed to get suggestion from AI. Please check the server logs.');
  }
}

const suggestShortPrompt = ai.definePrompt({
  name: 'suggestShortPrompt',
  input: {schema: SuggestShortInputSchema},
  output: {schema: SuggestShortOutputSchema},
  prompt: `You are a professional video editor who is an expert at identifying compelling short clips from longer videos.
Your task is to analyze a video and suggest a new short clip based on a user's objective.

User Objective: {{{objective}}}

You have been provided with a list of shorts that have ALREADY been created from this video.
You MUST suggest a NEW scene that does not overlap with the time ranges of these existing shorts.

Existing Shorts to Exclude:
{{#each existingShorts}}
- Title: "{{this.title}}" (from {{this.startTime}} to {{this.endTime}})
{{/each}}

Analyze the following video content and identify the single best scene that matches the user's objective and has not been used before.

Video: {{media url=gcsUrl}}

Based on your analysis, you must identify the single best scene and return its details in the specified JSON format.
Your response MUST be ONLY the JSON object. Do not include any other text, markdown, or explanations.`,
});

const suggestShortFlow = ai.defineFlow(
  {
    name: 'suggestShortFlow',
    inputSchema: SuggestShortInputSchema,
    outputSchema: SuggestShortOutputSchema,
  },
  async input => {
    const {output} = await suggestShortPrompt(input);
    if (!output) {
      throw new Error('The AI model did not return a valid response.');
    }
    return output;
  }
);
