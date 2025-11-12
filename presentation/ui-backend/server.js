
const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const cors = require('cors');
const { movieChat } = require('./movie-chat');
const logger = require('./logger');
const admin = require('firebase-admin');

admin.initializeApp({
  credential: admin.credential.applicationDefault()
});

const db = admin.firestore();

const app = express();
app.use(cors());
app.use(express.json());

const { Storage } = require('@google-cloud/storage');
const storage = new Storage();

app.get('/api/movies', async (req, res) => {
  try {
    const collectionName = process.env.FIRESTORE_COLLECTION || 'media_assets';
    const moviesCollection = db.collection(collectionName);
    const snapshot = await moviesCollection.get();
    if (snapshot.empty) {
      logger.log('No matching documents.');
      return res.status(404).send('No movies found');
    }
    const movies = snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));

    const moviesWithSignedUrls = await Promise.all(movies.map(async (movie) => {
      if ((!movie.public_url || !movie.public_url.startsWith('https://storage.googleapis.com/')) && movie.file_path) {
        try {
          const [bucketName, ...filePathParts] = movie.file_path.replace('gs://', '').split('/');
          const gcsPath = filePathParts.join('/');
          const options = {
            version: 'v4',
            action: 'read',
            expires: Date.now() + 15 * 60 * 1000, // 15 minutes
          };
          const [url] = await storage.bucket(bucketName).file(gcsPath).getSignedUrl(options);
          movie.public_url = url;
        } catch (error) {
          logger.error(`Error generating signed URL for ${movie.file_path}:`, error);
          // Leave public_url as is if signing fails
        }
      }
      return movie;
    }));

    res.json(moviesWithSignedUrls);
  } catch (error) {
    logger.error('Error fetching movies:', error);
    res.status(500).send('Error fetching movies');
  }
});

const server = http.createServer(app);
const io = new Server(server, {
  cors: {
    origin: '*'
  }
});

const PORT = process.env.PORT || 3001;

io.on('connection', (socket) => {
  logger.log('a user connected');

  socket.on('disconnect', () => {
    logger.log('user disconnected');
  });

  socket.on('chat message', async (msg) => {
    try {
      const result = await movieChat(msg);
      socket.emit('chat message', result);
    } catch (e) {
      logger.error(e);
      socket.emit('error', 'An error occurred');
    }
  });
});

server.listen(PORT, () => {
  logger.log(`Server is running on port ${PORT}`);
});