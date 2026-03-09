# Skeleton

This directory is a minimal Home Assistant test harness for the patched global Yamaha integration in this repository.

It is meant for local container-based verification, not for installation into a normal Home Assistant config directory.

## Contents

- `run_ha_yamaha_override.sh`
  Launches a Home Assistant container and bind-mounts the patched `homeassistant/components/yamaha` directory from this repo over the global Yamaha integration inside the container.
- `configuration.yaml`
  Minimal test configuration with debug logging enabled and a Yamaha receiver definition for live verification.

## How to use it

Run the launcher and point it at any existing Home Assistant config directory:

```sh
./skeleton/run_ha_yamaha_override.sh /path/to/ha-config
```

What the script does:

1. Copies the supplied config directory into `/tmp/ha`
2. Replaces `/tmp/ha/configuration.yaml` with `skeleton/configuration.yaml`
3. Starts a Home Assistant container
4. Mounts this repo's patched Yamaha integration into:
   `/usr/src/homeassistant/homeassistant/components/yamaha`
5. Streams the container logs

Default ports:

- host: `8500`
- container: `8123`

You can override the image or ports with environment variables:

```sh
IMAGE=ghcr.io/home-assistant/home-assistant:stable HOST_PORT=8501 ./skeleton/run_ha_yamaha_override.sh /path/to/ha-config
```

## When to use this

Use `skeleton/` when you want to:

- verify the patched Yamaha integration against a live receiver
- inspect Home Assistant startup logs
- test the integration in a disposable container without modifying your normal Home Assistant container setup

Use the repo-level [installation.md](/data/scripts/yamaha/gitrepo/ha-yamaha/installation.md) when you want to run the patched Yamaha integration in your actual Home Assistant container.
