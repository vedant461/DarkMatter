FROM node:22-alpine
WORKDIR /app
COPY package.json vite.config.ts index.html ./
RUN npm install
COPY src ./src
CMD ["npm","run","dev"]
