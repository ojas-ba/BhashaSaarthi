"""Explicit runtime configuration, with no credentials in serialized settings."""
import os
from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    param_model: str = os.getenv('PARAM_MODEL', 'bharatgenai/Param-1-2.9B-Instruct')
    param_revision: str = os.getenv('PARAM_REVISION', 'f9b32a727458727ff515fea5d82df00ae9b7ad56')
    trans_model: str = os.getenv('TRANS_MODEL', 'ai4bharat/indictrans2-indic-en-dist-200M')
    trans_revision: str = os.getenv('TRANS_REVISION', 'd66a2122ad6d28184f3dc3797b652bd80ae3f65f')
    device: str = os.getenv('DEVICE', 'cpu')
    precision: str = os.getenv('PRECISION', 'float32')
    xlit_url: str = os.getenv('XLIT_URL', 'http://127.0.0.1:8765')
    trans_url: str = os.getenv('TRANS_URL', '')
    remote_code: bool = os.getenv('ALLOW_REVIEWED_REMOTE_CODE', '0') == '1'
    max_chars: int = int(os.getenv('MAX_INPUT_CHARS', '1800'))
    max_new_tokens: int = int(os.getenv('MAX_NEW_TOKENS', '384'))
    max_generation_seconds: float = float(os.getenv('MAX_GENERATION_SECONDS', '120'))
