"""
Audio utilities for loading, converting, and preprocessing audio files.
"""
import base64
import tempfile
import os
import logging
from typing import Tuple, Optional
import numpy as np
import soundfile as sf
import librosa

logger = logging.getLogger(__name__)

# Constants for validation
MAX_AUDIO_SIZE_MB = 25  # Maximum base64 decoded size in MB
MAX_DURATION_SECONDS = 300  # Maximum 5 minutes
MIN_DURATION_SECONDS = 1  # Minimum 1 second


def detect_audio_format(audio_bytes: bytes) -> str:
    """
    Detect audio format from file magic bytes.
    
    Args:
        audio_bytes: Raw audio bytes
        
    Returns:
        File extension (e.g., '.m4a', '.webm', '.wav', '.mp3', '.ogg')
    """
    # Check magic bytes for common audio formats
    if audio_bytes[:4] == b'ftyp' or audio_bytes[4:8] == b'ftyp':
        return '.m4a'  # M4A/MP4
    elif audio_bytes[:4] == b'RIFF':
        return '.wav'
    elif audio_bytes[:3] == b'ID3' or audio_bytes[:2] == b'\xff\xfb':
        return '.mp3'
    elif audio_bytes[:4] == b'OggS':
        return '.ogg'
    elif audio_bytes[:4] == b'\x1aE\xdf\xa3':
        return '.webm'
    elif audio_bytes[:4] == b'fLaC':
        return '.flac'
    else:
        # Default to m4a as it's most common from mobile
        return '.m4a'


def validate_audio_size(base64_str: str) -> None:
    """
    Validate that audio size is within acceptable limits.
    
    Args:
        base64_str: Base64 encoded audio data
        
    Raises:
        ValueError: If audio exceeds size limit
    """
    # Base64 is ~4/3 the size of raw bytes
    estimated_bytes = len(base64_str) * 3 / 4
    estimated_mb = estimated_bytes / (1024 * 1024)
    
    if estimated_mb > MAX_AUDIO_SIZE_MB:
        raise ValueError(
            f"Audio file too large: {estimated_mb:.1f}MB exceeds {MAX_AUDIO_SIZE_MB}MB limit"
        )


def validate_audio_duration(audio: np.ndarray, sr: int) -> None:
    """
    Validate that audio duration is within acceptable limits.
    
    Args:
        audio: Audio array
        sr: Sample rate
        
    Raises:
        ValueError: If audio is too short or too long
    """
    duration = len(audio) / sr
    
    if duration < MIN_DURATION_SECONDS:
        raise ValueError(
            f"Audio too short: {duration:.1f}s is less than {MIN_DURATION_SECONDS}s minimum"
        )
    
    if duration > MAX_DURATION_SECONDS:
        raise ValueError(
            f"Audio too long: {duration:.1f}s exceeds {MAX_DURATION_SECONDS}s limit"
        )


def load_audio_from_base64(base64_str: str, target_sr: int = 16000) -> Tuple[np.ndarray, int]:
    """
    Load audio from base64 string and convert to numpy array.
    
    Args:
        base64_str: Base64 encoded audio data
        target_sr: Target sample rate (default 16000 Hz)
        
    Returns:
        Tuple of (audio_array, sample_rate)
        
    Raises:
        ValueError: If audio is invalid, too large, or duration out of bounds
    """
    # Validate size before decoding
    validate_audio_size(base64_str)
    
    temp_path: Optional[str] = None
    
    try:
        # Decode base64 to bytes
        audio_bytes = base64.b64decode(base64_str)
        
        # Detect format from content
        file_extension = detect_audio_format(audio_bytes)
        logger.info(f"Detected audio format: {file_extension}")
        
        # Create temporary file with correct extension
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_extension)
        temp_path = temp_file.name
        temp_file.write(audio_bytes)
        temp_file.close()
        
        # Load audio using librosa
        audio, sr = librosa.load(temp_path, sr=target_sr, mono=True)
        
        # Validate duration
        validate_audio_duration(audio, sr)
        
        # Normalize audio to prevent clipping
        audio = normalize_audio(audio)
        
        return audio, sr
        
    except ValueError:
        # Re-raise validation errors as-is
        raise
    except Exception as e:
        logger.error(f"Failed to load audio from base64: {str(e)}")
        raise ValueError(f"Failed to load audio from base64: {str(e)}")
    finally:
        # Always clean up temp file
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except Exception as cleanup_error:
                logger.warning(f"Failed to clean up temp file {temp_path}: {cleanup_error}")


def normalize_audio(audio: np.ndarray, target_level: float = 0.3) -> np.ndarray:
    """
    Normalize audio levels to prevent clipping and ensure consistent volume.
    
    Args:
        audio: Audio array
        target_level: Target RMS level (0-1)
        
    Returns:
        Normalized audio array
    """
    # Calculate current RMS
    rms = np.sqrt(np.mean(audio**2))
    
    if rms > 0:
        # Scale to target level
        scaling_factor = target_level / rms
        audio = audio * scaling_factor
        
    # Clip to prevent values outside [-1, 1]
    audio = np.clip(audio, -1.0, 1.0)
    
    return audio


def save_temp_wav(audio: np.ndarray, sr: int) -> str:
    """
    Save audio array as temporary WAV file.
    
    Args:
        audio: Audio array
        sr: Sample rate
        
    Returns:
        Path to temporary WAV file
    """
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
    temp_path = temp_file.name
    temp_file.close()
    
    sf.write(temp_path, audio, sr)
    
    return temp_path


def get_audio_duration(audio: np.ndarray, sr: int) -> float:
    """
    Calculate audio duration in seconds.
    
    Args:
        audio: Audio array
        sr: Sample rate
        
    Returns:
        Duration in seconds
    """
    return len(audio) / sr


def resample_audio(audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    """
    Resample audio to target sample rate.
    
    Args:
        audio: Audio array
        orig_sr: Original sample rate
        target_sr: Target sample rate
        
    Returns:
        Resampled audio array
    """
    if orig_sr == target_sr:
        return audio
        
    return librosa.resample(audio, orig_sr=orig_sr, target_sr=target_sr)
