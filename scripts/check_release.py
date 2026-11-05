#!/usr/bin/env python3
"""Offline documentation/privacy checks; refresh checksums, optionally create a ZIP."""
from __future__ import annotations

import argparse
import hashlib
import ipaddress
from pathlib import Path
import re
from urllib.parse import unquote
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TOP = {'README.md', 'README.en.md', 'agent.md', 'agent.en.md', 'AGENTS.md',
       'DISCLAIMER.md', 'DISCLAIMER.en.md', '.gitignore', '.gitattributes'}
DOCS = {'aerial', 'connection', 'device', 'app-install-policy', 'yecao',
        'app-inventory', 'recovery', 'troubleshooting', 'evidence', 'references',
        'maintenance-record-template', 'publishing', 'validation'}
CODE = {'scripts/tvctl.py', 'scripts/termux-ssh.sh', 'scripts/policy_lists.py',
        'scripts/check_release.py', 'tests/test_tvctl.py', 'tests/test_policy_lists.py'}
EXPECTED = TOP | CODE | {f'docs/{name}.md' for name in DOCS} | {f'docs/en/{name}.md' for name in DOCS}
IGNORED_DIRS = {'.git', '.local', 'local', 'work', '__pycache__'}
EXAMPLE_NETS = tuple(ipaddress.ip_network(net) for net in ('192.0.2.0/24', '198.51.100.0/24', '203.0.113.0/24'))


def source_files():
    found = {}
    for path in ROOT.rglob('*'):
        rel = path.relative_to(ROOT)
        if any(part in IGNORED_DIRS for part in rel.parts):
            continue
        if path.is_symlink():
            raise ValueError(f'Symlink is not permitted in release: {rel}')
        if not path.is_file() or rel.as_posix() == 'SHA256SUMS':
            continue
        if rel.as_posix() not in EXPECTED:
            raise ValueError(f'Unreviewed release file: {rel}')
        found[rel.as_posix()] = path
    if set(found) != EXPECTED:
        raise ValueError(f'Missing release files: {sorted(EXPECTED - set(found))}')
    return found


def check_text(rel, text):
    if text.startswith('\ufeff') or '\r' in text:
        raise ValueError(f'Release text must use UTF-8 without BOM and LF line endings: {rel}')
    patterns = (r'[A-Za-z]:[\\/](?:Users|Documents and Settings)[\\/]',
                r'-----BEGIN (?:OPENSSH |RSA |EC |DSA )?PRIVATE KEY-----',
                r'\bu0_a\d+\b', r'\bAAAAC3NzaC1lZDI1NTE5[A-Za-z0-9+/=]{20,}',
                r'\bAIza[A-Za-z0-9_-]{30,}', r'\bgh[pousr]_[A-Za-z0-9]{30,}')
    for pattern in patterns:
        if re.search(pattern, text):
            raise ValueError(f'Potential private context in {rel}')
    for raw in re.findall(r'(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])', text):
        try:
            addr = ipaddress.ip_address(raw)
        except ValueError:
            continue
        if any(addr in net for net in EXAMPLE_NETS):
            continue
        if addr.is_private and not addr.is_loopback:
            raise ValueError(f'Non-example private network address in {rel}')


def check_links(rel, text):
    for target in re.findall(r'\]\(([^)]+)\)', text):
        target = target.strip('<>')
        if '://' in target or target.startswith(('#', 'mailto:')):
            continue
        filename = unquote(target.split('#', 1)[0])
        destination = (ROOT / rel).parent / filename
        if not destination.resolve().is_relative_to(ROOT) or not destination.is_file():
            raise ValueError(f'Broken or external local link in {rel}: {target}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Verify existing checksums without writing them')
    parser.add_argument('--zip', action='store_true', help='Create a ZIP beside the repository directory')
    args = parser.parse_args()
    files = source_files()
    for rel, path in files.items():
        text = path.read_bytes().decode('utf8')
        check_text(rel, text)
        if path.suffix == '.md':
            check_links(rel, text)
    sums = ''.join(f'{hashlib.sha256(files[rel].read_bytes()).hexdigest()}  {rel}\n' for rel in sorted(files))
    manifest = ROOT / 'SHA256SUMS'
    if args.check:
        if not manifest.is_file() or manifest.read_text(encoding='utf8') != sums:
            raise ValueError('SHA256SUMS is missing or stale. Run without --check after reviewing changes.')
    else:
        manifest.write_text(sums, encoding='utf8', newline='\n')
    print(f'Checked {len(files)} public files, paired languages, local links and sensitive-data patterns.')
    print('Automated scans do not replace a manual privacy review.')
    if args.zip:
        archive = ROOT.parent / (ROOT.name + '.zip')
        with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as bundle:
            for rel in sorted(files):
                bundle.write(files[rel], ROOT.name + '/' + rel)
            bundle.write(manifest, ROOT.name + '/SHA256SUMS')
        with zipfile.ZipFile(archive) as bundle:
            if bundle.testzip() is not None or len(bundle.namelist()) != len(files) + 1:
                raise ValueError('ZIP verification failed')
        print(f'ZIP: {archive.name}; SHA256: {hashlib.sha256(archive.read_bytes()).hexdigest()}')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, OSError, UnicodeError) as exc:
        raise SystemExit(f'Release check failed: {exc}')
