FROM python:3.10-alpine

WORKDIR /app

COPY . .

EXPOSE 3000

RUN apk update && apk --no-cache add openssl bash curl &&\
    chmod +x app.py start.sh
    
CMD ["python3", "app.py"]
