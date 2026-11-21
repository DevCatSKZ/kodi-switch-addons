# Publishing add-on updates

1. Build the add-on for the matching Kodi NX ABI. Increase its version.
2. Record the exact source commit, dependency sources and license notices.
3. Validate the archive structure, AArch64 ELF, loader compatibility and target hardware behavior.
4. Generate a reviewed catalog and static repository using `tools/build_repository.py`
   from the Kodi NX source archive. Use these URL bases:

   - Index/artwork: `https://devcatskz.github.io/kodi-switch-addons/piers/switch/`
   - Packages: `https://github.com/DevCatSKZ/kodi-switch-addons/releases/download/`

5. Upload each add-on to the release whose tag equals its add-on ID. Include
   `<id>-<version>.zip`, its `.sha256` sidecar, corresponding sources and notices.
   Keep older versioned files available. Never replace an existing version with different bytes.
6. Download the uploaded assets and compare SHA-256 hashes.
7. Copy the generated `site` tree to `docs/piers/switch`, review the diff and
   commit the updated index and its checksum together. GitHub Pages publishes `/docs`.
8. Check the public index checksum and an actual installation/update on the Switch.

The catalog must only reference assets that are already accessible without
authentication. Do not put GitHub tokens or other credentials in the repository
add-on or in the application package.

The repository bootstrap itself uses the tag `repository.kodi-switch` and is
listed in the catalog so it can update normally. Increase its version when
changing repository URLs or settings.

