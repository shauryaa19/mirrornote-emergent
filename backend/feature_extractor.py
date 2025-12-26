"""
Acoustic feature extraction: prosody, loudness, quality, and spectral features.
"""
from typing import Dict, List
import logging
import numpy as np
import librosa

logger = logging.getLogger(__name__)

# Prosody thresholds (Hz)
PITCH_HIGH_THRESHOLD = 200  # Above this is considered high pitch
PITCH_LOW_THRESHOLD = 130   # Below this is considered low pitch
PITCH_STD_HIGH = 45         # High vocal variety
PITCH_STD_MEDIUM = 25       # Normal vocal variety

# Loudness thresholds (dB)
DYNAMIC_RANGE_HIGH = 15     # Very dynamic
DYNAMIC_RANGE_MEDIUM = 8    # Normal dynamic range

# Voice quality thresholds
HNR_EXCELLENT = 15          # Excellent voice quality
HNR_GOOD = 10               # Good voice quality


def extract_prosody(audio: np.ndarray, sr: int) -> Dict:
    """
    Extract prosodic features (pitch/F0).
    Uses librosa's pyin algorithm for robust pitch tracking.
    
    Args:
        audio: Audio array
        sr: Sample rate
        
    Returns:
        Dictionary of prosody metrics
    """
    try:
        # Extract F0 using PYIN
        f0, voiced_flag, voiced_probs = librosa.pyin(
            audio,
            fmin=librosa.note_to_hz('C2'),  # ~65 Hz
            fmax=librosa.note_to_hz('C7'),  # ~2093 Hz
            sr=sr
        )
        
        # Filter out unvoiced frames (NaN values)
        f0_voiced = f0[~np.isnan(f0)]
        
        if len(f0_voiced) == 0:
            logger.warning("No voiced frames detected in audio")
            return {
                "pitch_mean": 0,
                "pitch_std": 0,
                "pitch_p5": 0,
                "pitch_p50": 0,
                "pitch_p95": 0,
                "pitch_range_hz": 0,
                "pitch_series": []
            }
        
        # Calculate statistics
        pitch_mean = float(np.mean(f0_voiced))
        pitch_std = float(np.std(f0_voiced))
        pitch_p5 = float(np.percentile(f0_voiced, 5))
        pitch_p50 = float(np.percentile(f0_voiced, 50))
        pitch_p95 = float(np.percentile(f0_voiced, 95))
        pitch_range = pitch_p95 - pitch_p5
        
        # Create time series for visualization (downsample)
        hop_length = 512
        times = librosa.frames_to_time(range(len(f0)), sr=sr, hop_length=hop_length)
        pitch_series = [
            {"time": float(t), "f0": float(f) if not np.isnan(f) else None}
            for t, f in zip(times[::10], f0[::10])  # Downsample for efficiency
        ]
        
        return {
            "pitch_mean": round(pitch_mean, 2),
            "pitch_std": round(pitch_std, 2),
            "pitch_p5": round(pitch_p5, 2),
            "pitch_p50": round(pitch_p50, 2),
            "pitch_p95": round(pitch_p95, 2),
            "pitch_range_hz": round(pitch_range, 2),
            "pitch_series": pitch_series[:200]  # Limit to 200 points
        }
        
    except Exception as e:
        logger.error(f"Prosody extraction failed: {e}")
        return {
            "pitch_mean": 0,
            "pitch_std": 0,
            "pitch_p5": 0,
            "pitch_p50": 0,
            "pitch_p95": 0,
            "pitch_range_hz": 0,
            "pitch_series": []
        }


def extract_loudness(audio: np.ndarray, sr: int) -> Dict:
    """
    Extract loudness and energy features.
    
    Args:
        audio: Audio array
        sr: Sample rate
        
    Returns:
        Dictionary of loudness metrics
    """
    try:
        # Calculate RMS energy
        rms = librosa.feature.rms(y=audio, frame_length=2048, hop_length=512)[0]
        
        if len(rms) == 0:
            logger.warning("No RMS frames extracted from audio")
            return {
                "rms_mean": 0,
                "rms_std": 0,
                "dynamic_range_db": 0,
                "rms_series": []
            }
        
        # Convert to dB
        rms_db = librosa.amplitude_to_db(rms, ref=np.max)
        
        # Calculate statistics
        rms_mean = float(np.mean(rms))
        rms_std = float(np.std(rms))
        dynamic_range_db = float(np.max(rms_db) - np.min(rms_db))
        
        # Create time series
        times = librosa.frames_to_time(range(len(rms)), sr=sr, hop_length=512)
        rms_series = [
            {"time": float(t), "rms": float(r)}
            for t, r in zip(times[::10], rms[::10])
        ]
        
        return {
            "rms_mean": round(rms_mean, 4),
            "rms_std": round(rms_std, 4),
            "dynamic_range_db": round(dynamic_range_db, 2),
            "rms_series": rms_series[:200]
        }
        
    except Exception as e:
        logger.error(f"Loudness extraction failed: {e}")
        return {
            "rms_mean": 0,
            "rms_std": 0,
            "dynamic_range_db": 0,
            "rms_series": []
        }


def extract_voice_quality_librosa(audio: np.ndarray, sr: int) -> Dict:
    """
    Extract voice quality features using librosa (proxy when Parselmouth unavailable).
    
    NOTE: These are approximations based on spectral features, not clinical measurements.
    For accurate jitter/shimmer/HNR, use Parselmouth/Praat.
    
    Args:
        audio: Audio array
        sr: Sample rate
        
    Returns:
        Dictionary of quality metrics (approximations)
    """
    try:
        # Spectral flatness (proxy for breathiness)
        flatness = librosa.feature.spectral_flatness(y=audio)
        flatness_mean = float(np.mean(flatness))
        
        # Zero crossing rate (proxy for jitter/roughness)
        zcr = librosa.feature.zero_crossing_rate(audio)
        zcr_mean = float(np.mean(zcr))
        
        # Spectral rolloff (proxy for harmonic content)
        rolloff = librosa.feature.spectral_rolloff(y=audio, sr=sr)
        rolloff_mean = float(np.mean(rolloff))
        
        # Estimate quality scores (normalized to typical ranges)
        # These are APPROXIMATIONS - not clinical measurements
        jitter_proxy = min(zcr_mean * 10, 5.0)  # Normalized to ~0-5% range
        shimmer_proxy = min(flatness_mean * 20, 8.0)  # Normalized to ~0-8% range
        hnr_proxy = max(15 - (flatness_mean * 30), 5.0)  # Inverse relationship, 5-20 dB
        
        return {
            "jitter_local": round(jitter_proxy, 2),
            "shimmer_local": round(shimmer_proxy, 2),
            "hnr_mean": round(hnr_proxy, 2),
            "method": "librosa_proxy",  # Indicates these are approximations
            "is_approximation": True
        }
        
    except Exception as e:
        logger.error(f"Quality extraction failed: {e}")
        return {
            "jitter_local": 0,
            "shimmer_local": 0,
            "hnr_mean": 15.0,
            "method": "fallback",
            "is_approximation": True
        }


def extract_spectral(audio: np.ndarray, sr: int) -> Dict:
    """
    Extract spectral features (MFCCs, centroid, rolloff, bandwidth).
    
    Args:
        audio: Audio array
        sr: Sample rate
        
    Returns:
        Dictionary of spectral metrics
    """
    try:
        # MFCCs
        mfccs = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=13)
        mfcc_means = [float(np.mean(mfcc)) for mfcc in mfccs]
        mfcc_stds = [float(np.std(mfcc)) for mfcc in mfccs]
        
        # Spectral centroid
        centroid = librosa.feature.spectral_centroid(y=audio, sr=sr)
        centroid_mean = float(np.mean(centroid))
        
        # Spectral rolloff
        rolloff = librosa.feature.spectral_rolloff(y=audio, sr=sr)
        rolloff_mean = float(np.mean(rolloff))
        
        # Spectral bandwidth
        bandwidth = librosa.feature.spectral_bandwidth(y=audio, sr=sr)
        bandwidth_mean = float(np.mean(bandwidth))
        
        return {
            "mfcc_means": [round(m, 3) for m in mfcc_means],
            "mfcc_stds": [round(s, 3) for s in mfcc_stds],
            "spectral_centroid_mean": round(centroid_mean, 2),
            "rolloff_mean": round(rolloff_mean, 2),
            "bandwidth_mean": round(bandwidth_mean, 2)
        }
        
    except Exception as e:
        logger.error(f"Spectral extraction failed: {e}")
        return {
            "mfcc_means": [0] * 13,
            "mfcc_stds": [0] * 13,
            "spectral_centroid_mean": 0,
            "rolloff_mean": 0,
            "bandwidth_mean": 0
        }


def extract_all_features(audio: np.ndarray, sr: int, segments: List[Dict] = None) -> Dict:
    """
    Extract all acoustic features from audio.
    
    Args:
        audio: Audio array
        sr: Sample rate
        segments: Optional VAD segments (for speech-only analysis)
        
    Returns:
        Dictionary containing all features
    """
    # Use speech-only audio if segments provided
    analysis_audio = audio
    if segments:
        from vad import get_speech_only_audio
        speech_audio = get_speech_only_audio(audio, sr, segments)
        if len(speech_audio) > sr:  # At least 1 second of speech
            analysis_audio = speech_audio
            logger.info(f"Using speech-only audio: {len(speech_audio)/sr:.1f}s of {len(audio)/sr:.1f}s total")
        else:
            logger.warning("Speech-only audio too short, using full audio")
    
    prosody = extract_prosody(analysis_audio, sr)
    loudness = extract_loudness(analysis_audio, sr)
    quality = extract_voice_quality_librosa(analysis_audio, sr)
    spectral = extract_spectral(analysis_audio, sr)
    
    return {
        "prosody": prosody,
        "loudness": loudness,
        "quality": quality,
        "spectral": spectral
    }
