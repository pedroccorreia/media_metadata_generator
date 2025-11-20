FROM node:22

# Create and change to the app directory.
WORKDIR /app

# Copy application dependency manifests to the container image.
# A wildcard is used to ensure both package.json AND package-lock.json are copied.
# Copying this separately prevents re-running npm install on every code change.
COPY package*.json ./

# Install production dependencies.
RUN npm install

# Copy local business logic to the container image.
COPY . .

# Build the Next.js application.
RUN npm run build

# Tell the world that this container is listening on port 3000.
EXPOSE 3000

# Run the web service on container startup.
CMD [ "npm", "start" ]
