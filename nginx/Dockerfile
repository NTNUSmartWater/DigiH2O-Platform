FROM nginx:alpine
WORKDIR /usr/share/nginx/html
# Remove default nginx static assets
RUN rm -rf ./*
# Copy frontend (index.html + assets)
COPY frontend/ .
COPY nginx/default.conf /etc/nginx/conf.d/default.conf
EXPOSE 80