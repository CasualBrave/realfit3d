"""Inventory exact files consumed by the pinned GG renderer; never unpickle."""
import hashlib
from pathlib import Path


def inspect_asset(root, name, hash_files=False):
    if not name or name in ('.', '..') or '/' in name or '\\' in name:
        raise ValueError('Invalid garment ID')
    directory = Path(root) / name
    files = []
    for relative in ('stage1/template_uv.obj', 'stage1/cameras.json', 'stage3/ckpt/net.pt'):
        path = directory / relative
        entry = dict(path=str(path), exists=path.is_file())
        if hash_files and entry['exists']:
            digest = hashlib.sha256()
            with path.open('rb') as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b''):
                    digest.update(block)
            entry['sha256'] = digest.hexdigest()
        files.append(entry)
    return dict(asset_id=name, files=files, files_ready=all(f['exists'] for f in files),
                topology_verified=False, note='Existence/checksums do not establish UV/topology or checkpoint compatibility.')
