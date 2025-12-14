FROM node:20-alpine

# Set build-time arguments
ARG VITE_BACKEND_URL
ARG VITE_WEBSOCKET_URL
ARG VITE_ENVIRONMENT

# Set environment variables based on the build arguments
ENV VITE_BACKEND_URL=$VITE_BACKEND_URL
ENV VITE_WEBSOCKET_URL=$VITE_WEBSOCKET_URL
ENV VITE_ENVIRONMENT=$VITE_ENVIRONMENT

# Set the working directory
WORKDIR /app

# Copy all files to the Docker image
COPY . /app

# Install dependencies
RUN npm install --legacy-peer-deps

# Build the frontend
RUN VITE_BACKEND_URL=$VITE_BACKEND_URL VITE_WEBSOCKET_URL=$VITE_WEBSOCKET_URL VITE_ENVIRONMENT=$VITE_ENVIRONMENT npm run build

# Install a lightweight static file server
RUN npm install -g serve

# Expose the port for the static server
EXPOSE 5173

# Serve the production build
CMD ["serve", "-s", "dist", "-l", "5173"]
