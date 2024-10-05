# Stage 1: Build Stage
FROM node:18-alpine AS build

# Set working directory
WORKDIR /app

# Copy package.json and package-lock.json for installing dependencies
COPY package.json package-lock.json ./

# Install dependencies and cache them
RUN npm install

# Copy the rest of the application source code
COPY . .

# Build the React app (production build)
RUN npm run build

# Stage 2: Serve Stage (Final Image)
FROM nginx:alpine

# Copy the build output from the previous stage to the Nginx web server directory
COPY --from=build /app/build /usr/share/nginx/html

# Expose port 2342 for the frontend
EXPOSE 2342

# Override default Nginx configuration (optional, but useful if you need to serve React apps properly)
# You can provide your own nginx.conf if needed
COPY ./nginx.conf /etc/nginx/conf.d/default.conf

# Start Nginx server
CMD ["nginx", "-g", "daemon off;"]
