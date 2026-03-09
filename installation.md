# Installation

This repository contains two override trees for Home Assistant container users:

- `homeassistant/components/yamaha`
- `python/rxv`

The `yamaha` integration code belongs inside the Home Assistant source tree in the container:

- `/usr/src/homeassistant/homeassistant/components/yamaha`

The `rxv` package is a separate Python package and must also be made available on `PYTHONPATH`.

## Option 1: Bind mount overrides into a test container

If you launch Home Assistant yourself with `docker run`, mount both override paths:

```sh
docker run --rm -d \
  --name homeassistant-yamaha-test \
  -p 8123:8123 \
  -e PYTHONPATH="/opt/yamaha_override/rxv" \
  -v /path/to/ha-config:/config \
  -v /path/to/ha-yamaha/homeassistant/components/yamaha:/usr/src/homeassistant/homeassistant/components/yamaha:ro \
  -v /path/to/ha-yamaha/python/rxv:/opt/yamaha_override/rxv:ro \
  ghcr.io/home-assistant/home-assistant:stable
```

In this repository, you can use:

```sh
./skeleton/run_ha_yamaha_override.sh /path/to/ha-config
```

That script mounts the same two override paths automatically and replaces the config with `skeleton/configuration.yaml`.

## Option 2: Patch an existing Home Assistant container

If Home Assistant is already running in a container, copy the files into the container and restart it.

Example container name:

```sh
HA_CONTAINER=homeassistant
```

Copy the yamaha component tree:

```sh
docker cp ./homeassistant/components/yamaha/. \
  "$HA_CONTAINER:/usr/src/homeassistant/homeassistant/components/yamaha/"
```

Copy the `rxv` package payload:

```sh
docker exec "$HA_CONTAINER" mkdir -p /opt/yamaha_override/rxv
docker cp ./python/rxv/. "$HA_CONTAINER:/opt/yamaha_override/rxv/"
```

Then ensure the container starts with:

```sh
PYTHONPATH=/opt/yamaha_override/rxv
```

How you set that depends on how the container is managed:

- `docker run`: add `-e PYTHONPATH=/opt/yamaha_override/rxv`
- `docker compose`: add `environment:`
- Kubernetes: add an env var to the pod spec

Restart the container after copying the files.

## Docker Compose example

```yaml
services:
  homeassistant:
    image: ghcr.io/home-assistant/home-assistant:stable
    ports:
      - "8123:8123"
    environment:
      PYTHONPATH: /opt/yamaha_override/rxv
    volumes:
      - ./config:/config
      - ./ha-yamaha/homeassistant/components/yamaha:/usr/src/homeassistant/homeassistant/components/yamaha:ro
      - ./ha-yamaha/python/rxv:/opt/yamaha_override/rxv:ro
```

## Verify

After startup, look for log lines showing:

- Yamaha zone discovery returning `Main_Zone` and `Zone_B`
- `Yamaha Receiver Zone B` being created

You can check with:

```sh
docker logs -f homeassistant
```

If you are using the test launcher from this repo:

```sh
docker logs -f homeassistant-yamaha-test
```
