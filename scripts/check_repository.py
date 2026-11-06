"""Check publishable files without printing any matched secret values."""
from pathlib import Path
import re
import subprocess

PATTERNS = [r'hf_[A-Za-z0-9]{20,}', r'gh[pousr]_[A-Za-z0-9]{20,}', r'github_pat_[A-Za-z0-9_]{20,}', r'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----']

def main():
    output = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'])
    names = sorted(set(filter(None, output.decode('utf-8').split('\0'))))
    flagged, large = [], []
    for name in names:
        content = Path(name).read_bytes()
        if len(content) > 5_000_000:
            large.append(name)
        encoding = 'utf-16' if content.startswith(b'\xff\xfe') else 'utf-8'
        text = content.decode(encoding, errors='replace')
        if any(re.search(pattern, text) for pattern in PATTERNS):
            flagged.append(name)
    print(f'Checked {len(names)} publishable files.')
    print('Potential secret-bearing files (values hidden):', flagged)
    print('Files over 5 MB:', large)
    if '.env' in names:
        flagged.append('.env')
    raise SystemExit(bool(flagged or large))

if __name__ == '__main__': main()
