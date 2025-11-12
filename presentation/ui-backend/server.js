
const express = require('express');
const http =require('http');
const { Server } = require('socket.io');
const cors = require('cors');
const { movieChat } = require('./movie-chat');
const logger = require('./logger');

const app = express();
app.use(cors());
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
3