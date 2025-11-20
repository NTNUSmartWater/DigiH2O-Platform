FROM nginx:alpine
WORKDIR /usr/share/nginx/html
# Remove default HTML folder
RUN rm -rf ./*
# Copy frontend build
COPY frontend/ /usr/share/nginx/html/
# Copy nginx config
COPY nginx/nginx.conf /etc/nginx/nginx.conf
EXPOSE 80