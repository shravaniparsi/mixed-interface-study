### STAGE 1: Build ###
FROM node@sha256:300e3d2c19067c1aec9d9b2bd3acbd43d53797a5836d70a23e437a5634bcd33a AS build
WORKDIR /usr/src/app
COPY package.json ./
RUN npm install
COPY . .
RUN npm run build

### STAGE 2: Run ###
FROM nginx@sha256:17bd1698318e9c0f9ba2c5ed49f53d690684dab7fe3e8019b855c352528d57be
COPY default.conf /etc/nginx/conf.d/default.conf
COPY --from=build /usr/src/app/dist/kanban-ui /usr/share/nginx/html
EXPOSE 80