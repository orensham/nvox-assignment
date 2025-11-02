FROM node:20-alpine AS builder

WORKDIR /app

COPY apps/nvox-fe/package*.json ./

RUN npm ci

COPY apps/nvox-fe/ ./

RUN npm run build

FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html

COPY apps/nvox-fe/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
