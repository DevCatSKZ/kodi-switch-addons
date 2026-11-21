# Kodi Switch Add-on repository

Native Nintendo Switch add-ons and development updates for **Kodi NX**.
This is an independent community project, not an official Team Kodi or Nintendo release.

## Installation

Kodi NX includes the repository entry. Open **Add-ons â†’ Install from repository â†’
Kodi Switch Add-on repository** to download an available add-on.

For an existing compatible installation, install the
[repository ZIP](https://github.com/DevCatSKZ/kodi-switch-addons/releases/download/repository.kodi-switch/repository.kodi-switch-1.1.0.zip)
through **Install from zip file**.

The catalog and artwork are served by GitHub Pages. Versioned add-on archives
and SHA-256 checksums are served by GitHub Releases. Optional add-ons are
downloaded when requested; the repository ZIP does not contain the add-ons.

## Compatibility

- Target: Kodi NX based on Kodi 22 (Piers), Nintendo Switch Horizon, AArch64.
- These native packages are not Android, desktop Linux or Windows add-ons.
- This is a development channel. Availability does not imply every feature,
  game or playback configuration has been validated.
- The catalog contains 264 reviewed native add-ons: audio decoders and encoders, image decoders,
  VFS and PVR clients, screensavers, visualizations and libretro game cores. Each release lists the
  exact source archives the binary was built from. Further packages are added as their source,
  licensing and compatibility checks complete.
- Controller profiles (`game.controller.*`) and Python modules are installed from the official Kodi
  repository, which Kodi NX keeps enabled.
- Some cores (for example Snes9x, Genesis Plus GX, FinalBurn, MAME 2000-2016, PicoDrive) have
  upstream licenses that allow free redistribution but forbid sale or commercial use. They are
  distributed free of charge and marked in their release notes. Do not sell or bundle them.
- Updates follow Kodi's add-on update settings. Updating Kodi NX itself requires
  a new application build. Statically linked components also require an application update.
- No ROMs, BIOS files, proprietary CDM, user profiles or provider credentials are included.

## Sources and licenses

Each published add-on retains its upstream license. The release contains pinned
upstream sources, required source dependencies and checksums. Package-specific
source information is included in `SOURCES.json` when applicable.

[Build support and port sources](https://github.com/DevCatSKZ/kodi-switch-addons/releases/tag/port-support-20261121)
include the build recipes, platform support and dependency adaptations.

## Publishing updates

See [PUBLISHING.md](PUBLISHING.md). Always publish and verify the versioned
archives before updating the catalog. Existing versioned archives must not be
overwritten. A new binary requires a new add-on version.

