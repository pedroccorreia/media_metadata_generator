
const express = require('express');
const admin = require('firebase-admin');
const { movieChat, MovieChatInputSchema } = require('./movie-chat.js');

// TODO: Replace with your service account key
admin.initializeApp();

const db = admin.firestore();
const app = express();
const port = process.env.PORT || 8080;

app.use(express.json());

app.get('/api/movies', async (req, res) => {
  const collectionName = process.env.FIRESTORE_COLLECTION || 'media_assets';
  try {
    const moviesCollection = db.collection(collectionName);
    const movieSnapshot = await moviesCollection.get();
    const movieList = movieSnapshot.docs.map(doc => ({
      id: doc.id,
      ...doc.data()
    }));
    res.json(movieList);
  } catch (error) {
    console.error(`Error fetching '${collectionName}' from Firestore:`, error);
    res.status(500).send('Error fetching data from Firestore');
  }
});

app.post('/api/chat', async (req, res) => {
    try {
        const validationResult = MovieChatInputSchema.safeParse(req.body);
        if (!validationResult.success) {
            return res.status(400).json({ error: validationResult.error.flatten() });
        }
        const output = await movieChat(validationResult.data);
        res.json(output);
    } catch (error) {
        console.error('Error in /api/chat:', error);
        res.status(500).send('Error processing chat request');
    }
});

app.listen(port, () => {
  console.log(`Server listening on port ${port}`);
});
