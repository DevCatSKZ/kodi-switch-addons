"""Build a static Kodi repository from catalogued Switch add-on archives.

No network access or publishing is performed. Preview output is not a release.
"""
import argparse
import hashlib
import io
import json
import re
import shutil
import stat
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ID = 'repository.kodi-switch'


def https_base(value):
    url = urlsplit(value)
    if (url.scheme != 'https' or not url.hostname or url.username or url.password
            or url.query or url.fragment or not url.path.endswith('/')
            or '\\' in value or any(c.isspace() for c in value)):
        raise ValueError('Use an HTTPS directory URL ending in /, without credentials or query')
    return value


def archive_contents(path, addon_id):
    """Validate the archive before any extraction, including ELF architecture."""
    files = {}
    with zipfile.ZipFile(path) as archive:
        seen = set()
        for member in archive.infolist():
            name = PurePosixPath(member.filename)
            if (not name.parts or name.is_absolute() or '..' in name.parts
                    or name.parts[0] != addon_id or '\\' in member.filename
                    or ':' in member.filename or member.filename in seen
                    or stat.S_ISLNK(member.external_attr >> 16)):
                raise ValueError('Unsafe or duplicate archive member: ' + member.filename)
            seen.add(member.filename)
            if member.is_dir():
                continue
            data = archive.read(member)
            if data.startswith(b'\x7fELF') and (
                    len(data) < 20 or data[4:6] != b'\x02\x01'
                    or int.from_bytes(data[18:20], 'little') != 183):
                raise ValueError('Non-AArch64 ELF: ' + member.filename)
            files[member.filename] = data
    manifest = ET.fromstring(files[addon_id + '/addon.xml'])
    if manifest.get('id') != addon_id:
        raise ValueError('Archive add-on ID differs from catalog')
    return manifest, files


def xml_bytes(root):
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)


def write_hashed(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    path.with_name(path.name + '.sha256').write_text(digest + '\n', encoding='ascii')
    return digest


def repository_files(base_url, version, package_base_url=None):
    https_base(base_url)
    package_base_url = https_base(package_base_url or base_url)
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ValueError('Repository version must be major.minor.patch')
    template = ROOT / 'sources/kodi/addons' / REPOSITORY_ID
    root = ET.parse(template / 'addon.xml').getroot()
    root.set('name', 'Kodi Switch Add-on repository')
    root.set('version', version)
    directory = root.find("extension[@point='xbmc.addon.repository']/dir")
    directory.find('info').text = base_url + 'addons.xml'
    directory.find('checksum').text = base_url + 'addons.xml.sha256'
    directory.find('datadir').text = package_base_url
    ET.SubElement(directory, 'artdir').text = base_url
    metadata = root.find("extension[@point='xbmc.addon.metadata']")
    for description in metadata.findall('description'):
        language = description.get('lang', '')
        description.text = (
            'Native Erweiterungen fuer Kodi auf Nintendo Switch. Installation und Updates erfolgen online.'
            if language == 'de_DE' else
            'Native add-ons for Kodi on Nintendo Switch. Install and update add-ons online.')
    return root, {'addon.xml': xml_bytes(root), 'icon.png': (template / 'icon.png').read_bytes(),
                  'LICENSE.md': (ROOT / 'LICENSE.md').read_bytes()}


def deterministic_zip(addon_id, files):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(addon_id + '/' + name, (2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    return buffer.getvalue()


def build(archive_dir, catalog_path, output, base_url=None, version='1.1.0',
          preview=False, selected=None, package_base_url=None):
    archive_dir, output = Path(archive_dir).resolve(), Path(output).resolve()
    if output.exists():
        raise ValueError('Output must be a new directory')
    if base_url:
        https_base(base_url)
    if package_base_url:
        https_base(package_base_url)
        if not base_url:
            raise ValueError('Package URL requires an index base URL')
    if not preview and not base_url:
        raise ValueError('Release output requires the final HTTPS base URL')
    rows = json.loads(Path(catalog_path).read_text(encoding='utf-8'))['addons']
    if selected:
        unknown = set(selected) - {row['id'] for row in rows}
        if unknown:
            raise ValueError('Unknown catalog IDs: ' + ', '.join(sorted(unknown)))
        rows = [row for row in rows if row['id'] in selected]
    if not rows:
        raise ValueError('No add-ons selected')
    # Check the entire selected set before producing output.
    for row in rows:
        if not re.fullmatch(r'[a-z0-9_.-]+', row['id']):
            raise ValueError('Invalid catalog ID')
        if not re.fullmatch(r'[0-9][a-zA-Z0-9_.+~-]*', row['version']):
            raise ValueError('Invalid catalog version')
        if not preview and (row.get('redistribution_review') != 'approved'
                            or not re.fullmatch(r'[0-9a-f]{40}', row.get('source_commit', ''))):
            raise ValueError('Release source/license review incomplete: ' + row['id'])
        path = archive_dir / (row['id'] + '-' + row['version'] + '.zip')
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != row['archive_sha256']:
            raise ValueError('Archive differs from catalog: ' + row['id'])
    output.mkdir(parents=True)
    index = ET.Element('addons')
    records = []
    for row in sorted(rows, key=lambda row: row['id']):
        addon_id = row['id']
        filename = addon_id + '-' + row['version'] + '.zip'
        source = archive_dir / filename
        metadata, files = archive_contents(source, addon_id)
        if metadata.get('version') != row['version']:
            raise ValueError('Archive version differs from catalog: ' + addon_id)
        platform = metadata.findtext("extension[@point='xbmc.addon.metadata']/platform", '')
        if not set(platform.split()).intersection({'switch', 'all'}):
            raise ValueError('Archive is not marked for Switch: ' + addon_id)
        target = output / 'site' / addon_id
        package_target = output / 'release-assets' / addon_id if package_base_url else target
        digest = write_hashed(package_target / filename, source.read_bytes())
        assets = metadata.find("extension[@point='xbmc.addon.metadata']/assets")
        for asset in list(assets) if assets is not None else []:
            if asset.tag not in ('icon', 'fanart', 'banner', 'clearlogo') or not asset.text:
                continue
            relative = PurePosixPath(asset.text.strip())
            if relative.is_absolute() or '..' in relative.parts or '\\' in asset.text or ':' in asset.text:
                raise ValueError('Unsafe asset path')
            content = files.get(addon_id + '/' + relative.as_posix())
            if content is not None:
                destination = target / relative.as_posix()
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(content)
        index.append(metadata)
        records.append({'id': addon_id, 'version': row['version'], 'sha256': digest,
                        'source': row.get('source'), 'source_commit': row.get('source_commit'),
                        'redistribution_review': row.get('redistribution_review')})
    if base_url:
        metadata, files = repository_files(base_url, version, package_base_url)
        name = REPOSITORY_ID + '-' + version + '.zip'
        content = deterministic_zip(REPOSITORY_ID, files)
        package_target = output / ('release-assets' if package_base_url else 'site') / REPOSITORY_ID
        write_hashed(package_target / name, content)
        icon_target = output / 'site' / REPOSITORY_ID / 'icon.png'
        icon_target.parent.mkdir(parents=True, exist_ok=True)
        icon_target.write_bytes(files['icon.png'])
        write_hashed(output / 'bootstrap' / name, content)
        index.append(metadata)
    write_hashed(output / 'site/addons.xml', xml_bytes(index))
    (output / 'site/.nojekyll').write_text('', encoding='ascii')
    report = {'preview': preview, 'release_approved': False,
              'base_url': base_url, 'package_base_url': package_base_url or base_url,
              'repository_version': version,
              'bootstrap_ready': bool(base_url), 'packages': records}
    (output / 'repository-manifest.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive-dir', type=Path, required=True)
    parser.add_argument('--catalog', type=Path, default=ROOT / 'manifests/addons.json')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--base-url')
    parser.add_argument('--package-base-url', help='Optional separate ZIP/checksum location')
    parser.add_argument('--version', default='1.1.0')
    parser.add_argument('--preview', action='store_true')
    parser.add_argument('--addon', action='append')
    args = parser.parse_args()
    result = build(args.archive_dir, args.catalog, args.output, args.base_url,
                   args.version, args.preview, args.addon, args.package_base_url)
    print(json.dumps({'packages': len(result['packages']), 'preview': result['preview'],
                      'bootstrap_ready': result['bootstrap_ready']}))


if __name__ == '__main__':
    main()
