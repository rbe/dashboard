# Paths and shipment

## Paths of config, data, state, and cache

A project that reads or writes such a path uses `XDG_CONFIG_HOME`, `XDG_DATA_HOME`, `XDG_STATE_HOME`, and `XDG_CACHE_HOME` on macOS and Linux. If a variable is unset, the paths are `~/.config`, `~/.local/share`, `~/.local/state`, and `~/.cache`.

## Shipment

A Make-only repository that ships a binary ships the binary. It ships example data only from `examples/`, and only when the path and the name say that it is an example.
