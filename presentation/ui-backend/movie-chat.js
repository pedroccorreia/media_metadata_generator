
const { vertexAI } = require('@genkit-ai/vertexai');
const { genkit } = require('genkit');
const { z } = require('zod');

const ai = genkit({
  plugins: [vertexAI({ location: process.env.GCP_REGION || 'us-central1', projectId: process.env.GCP_PROJECT_ID })],
});

const MovieChatInputSchema = z.object({
  query: z.string().describe('The user\'s query.'),
  history: z.array(z.object({
    role: z.enum(['user', 'assistant']),
    content: z.string(),
  })).optional().describe('The conversation history.'),
});

const MovieChatOutputSchema = z.object({
  answer: z.string().describe('The answer to the user\'s query.'),
});

async function movieChat(input) {
  const history = (input.history || []).map(message => ({
    role: message.role === 'assistant' ? 'model' : 'user',
    content: [{ text: message.content }]
  }));

  console.log('Chat prompt ' + input.query)

  let output;
  try {
    const prompt = `You are a media expert you give users short answer and ground it on the data whenever possible. User question: ${input.query}`;
    const result = await ai.generate({
      model: vertexAI.model('gemini-1.5-flash'),
      prompt: prompt,
    })


    output = result.text();
  } catch (error) {
    console.error('Error during AI generation:', error);
    throw error; // Re-throw the error after logging
  }

  if (!output) {

    throw new Error('The AI model did not return a valid response.');
  }

  return { answer: output };
}

module.exports = { movieChat, MovieChatInputSchema };
