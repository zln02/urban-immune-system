FROM node:20-alpine

WORKDIR /app
COPY package.json .
RUN npm install
COPY tsconfig.json .
COPY next.config.js .
COPY next-env.d.ts .
COPY src ./src

CMD ["npm", "run", "dev", "--", "-H", "0.0.0.0", "-p", "3000"]
