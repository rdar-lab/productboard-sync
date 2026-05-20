# How to deploy

## Build the image

```bash
docker build -t productboard-sync .
```

## Run once with local backend

```bash
docker run --rm \
  --env-file .env \
  -e LOCAL_OUTPUT_DIR=/output \
  -v $(pwd)/output:/output \
  productboard-sync
```

## Run with OneDrive or SharePoint

```bash
docker run --rm --env-file .env productboard-sync
```

## Daily scheduling with docker-compose

```bash
docker compose up -d --build scheduler
```

## View logs

```bash
docker compose logs -f sync
```

## Update deployment

```bash
git pull
docker compose build --no-cache
docker compose up -d
```
