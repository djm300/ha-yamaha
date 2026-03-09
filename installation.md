# Installation

This repository contains a patched Home Assistant Yamaha integration tree:

- `homeassistant/components/yamaha`

It is intended to replace the global Yamaha integration inside the Home Assistant container:

- `/usr/src/homeassistant/homeassistant/components/yamaha`

The patched `rxv` library and its supporting repo files are bundled inside that integration directory as:

- `homeassistant/components/yamaha/rxv`

No extra `PYTHONPATH` override is needed.

## Bind mount into a container

If you launch Home Assistant yourself with `docker run`, mount the Yamaha integration directory over the global Yamaha integration in the container:

```sh
docker run --rm -d \
  --name homeassistant-yamaha-test \
  -p 8123:8123 \
  -v /path/to/ha-config:/config \
  -v /path/to/ha-yamaha/homeassistant/components/yamaha:/usr/src/homeassistant/homeassistant/components/yamaha:ro \
  ghcr.io/home-assistant/home-assistant:stable
```

In this repository, you can use:

```sh
./skeleton/run_ha_yamaha_override.sh /path/to/ha-config
```

That script mounts the patched Yamaha integration automatically and replaces the config with `skeleton/configuration.yaml`.

## Docker Compose example

```yaml
services:
  homeassistant:
    image: ghcr.io/home-assistant/home-assistant:stable
    ports:
      - "8123:8123"
    volumes:
      - ./config:/config
      - ./ha-yamaha/homeassistant/components/yamaha:/usr/src/homeassistant/homeassistant/components/yamaha:ro
```

## Verify

After startup, look for log lines showing:

- Yamaha zone discovery returning `Main_Zone` and `Zone_B`
- `Yamaha Receiver Zone B` being created

You can check with:

```sh
docker logs -f homeassistant
```
