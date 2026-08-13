FROM node:22-alpine AS build
WORKDIR /web
COPY package*.json ./
RUN npm ci --ignore-scripts
COPY . .
RUN npm run build

FROM nginxinc/nginx-unprivileged:1.29.1-alpine
USER root
RUN apk upgrade --no-cache
COPY --from=build /web/dist /usr/share/nginx/html
COPY nginx.conf.template /etc/nginx/default.conf.template
COPY config.js.template /usr/share/nginx/html/config.js.template
COPY focus-entrypoint.sh /focus-entrypoint.sh
RUN chmod +x /focus-entrypoint.sh
RUN chown -R 101:101 /usr/share/nginx/html /etc/nginx/conf.d
USER 101
EXPOSE 8080
CMD ["/focus-entrypoint.sh"]
