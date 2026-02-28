FROM node:20-slim
WORKDIR /app
COPY package.json package-lock.json* ./
# Use npm install to allow building without a package-lock.json
RUN npm install --silent
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "run", "start"]
