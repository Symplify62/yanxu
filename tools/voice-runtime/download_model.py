"""Download public official weights to the isolated runtime; verify before use."""
import hashlib
from pathlib import Path
import tempfile
import urllib.request

SHA = 'e7584940aeac8d5512d875e58ce6c09ba4ddad65d8128e1dac0d93aadd087ebb'
URL = 'https://huggingface.co/Wespeaker/wespeaker-cnceleb-resnet34-LM/resolve/main/cnceleb_resnet34_LM.onnx'
root = Path(__file__).resolve().parents[2] / '.local-data/voice-runtime/models'
root.mkdir(parents=True, exist_ok=True)
target = root / 'cnceleb_resnet34_LM.onnx'
if target.exists():
    if hashlib.sha256(target.read_bytes()).hexdigest() != SHA:
        raise RuntimeError('Existing weights have a different digest; will not overwrite')
else:
    with tempfile.NamedTemporaryFile(dir=root, prefix='.model-', delete=False) as temporary:
        temporary_path = Path(temporary.name)
        try:
            with urllib.request.urlopen(URL, timeout=60) as response:
                while block := response.read(1024 * 1024):
                    temporary.write(block)
            temporary.flush()
            if hashlib.sha256(temporary_path.read_bytes()).hexdigest() != SHA:
                raise RuntimeError('Downloaded model digest does not match reviewed weights')
            temporary_path.replace(target)
        finally:
            temporary_path.unlink(missing_ok=True)
print('Official voice model verified:', SHA)
