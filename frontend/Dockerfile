FROM node:22-alpine
WORKDIR /app
COPY package.json package-lock.json vite.config.ts index.html ./
RUN npm ci
COPY src ./src
CMD ["npm","run","dev"]
