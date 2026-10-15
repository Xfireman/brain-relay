"""One local process, thread-safe, atomic JSON replacement. No silent recovery."""
import json
import os
from pathlib import Path
import tempfile
from threading import RLock
from .relay import validate_capsule, ValidationError


class Storage:
    def __init__(self, directory):
        self.directory = Path(directory).expanduser()
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.path = self.directory / 'capsules.json'
        self.lock = RLock()

    def _read(self):
        if not self.path.exists():
            return {}
        data = json.loads(self.path.read_text(encoding='utf-8'))
        if not isinstance(data, dict) or len(data) > 100:
            raise ValidationError('Stored capsule file is invalid; restore a backup before saving.')
        for key, value in data.items():
            if validate_capsule(value)['id'] != key:
                raise ValidationError('Stored capsule ID mismatch.')
        return data

    def all(self):
        with self.lock:
            return sorted(self._read().values(), key=lambda item: item['updated_at'], reverse=True)

    def get(self, capsule_id):
        with self.lock:
            return self._read().get(capsule_id)

    def save(self, capsule):
        capsule = validate_capsule(capsule)
        with self.lock:
            data = self._read()
            if capsule['id'] not in data and len(data) >= 100:
                raise ValidationError('This local store supports 100 capsules. Export a backup before starting a new data directory.')
            data[capsule['id']] = capsule
            temporary = None
            try:
                with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=self.directory, prefix='.capsules-', suffix='.tmp', delete=False) as stream:
                    temporary = stream.name
                    json.dump(data, stream, ensure_ascii=False, indent=2)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, self.path)
                temporary = None
            finally:
                if temporary:
                    os.unlink(temporary)
        return capsule
