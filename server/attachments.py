"""Bounded attachments stored inside the owning item's versioned content."""
import base64
import binascii
import re
from urllib.parse import urlsplit

MAX_FILE_BYTES = 1_000_000
MAX_ATTACHMENTS = 20


def valid_attachments(entries):
    if not isinstance(entries, list) or len(entries) > MAX_ATTACHMENTS:
        return False
    ids = set()
    for entry in entries:
        if not isinstance(entry, dict):
            return False
        identifier, name = entry.get('id'), entry.get('name')
        if not isinstance(identifier, str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,100}', identifier) or identifier in ids:
            return False
        ids.add(identifier)
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 200 or re.search(r'[\x00-\x1f\x7f/\\]', name):
            return False
        if entry.get('kind') == 'file':
            size, data = entry.get('size'), entry.get('data')
            if type(size) is not int or not 0 <= size <= MAX_FILE_BYTES or not isinstance(data, str) or len(data) > 1_333_336:
                return False
            try:
                if len(base64.b64decode(data, validate=True)) != size:
                    return False
            except (ValueError, binascii.Error):
                return False
        elif entry.get('kind') == 'item':
            if not isinstance(entry.get('itemId'), str) or not re.fullmatch(r'[a-f0-9]{32}', entry['itemId']):
                return False
        elif entry.get('kind') == 'link':
            url = entry.get('url')
            if not isinstance(url, str) or len(url) > 2048 or re.search(r'[\s\x00-\x1f\x7f]', url):
                return False
            try:
                parsed = urlsplit(url)
                if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password:
                    return False
            except ValueError:
                return False
        else:
            return False
    return True
