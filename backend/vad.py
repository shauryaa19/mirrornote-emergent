"""
Voice Activity Detection and timing analysis.
"""
from typing import List, Dict
import logging
import numpy as np
import webrtcvad
import struct

logger = logging.getLogger(__name__)

# VAD configuration constants
VAD_AGGRESSIVENESS = 2  # 0-3, higher = more aggressive (less false positives)
MEANINGFUL_PAUSE_MS = 200  # Minimum pause duration to count
LONG_PAUSE_MS = 700  # Threshold for "long" pauses


def segment_speech(audio: np.ndarray, sr: int, frame_duration_ms: int = 30) -> List[Dict]:
    """
    Segment audio into speech and silence regions using WebRTC VAD.
    
    Args:
        audio: Audio array (float32, -1 to 1)
        sr: Sample rate (must be 8000, 16000, 32000, or 48000)
        frame_duration_ms: Frame duration in ms (10, 20, or 30)
        
    Returns:
        List of segments with start_s, end_s, type
    """
    # WebRTC VAD only supports specific sample rates
    if sr not in [8000, 16000, 32000, 48000]:
        raise ValueError(f"Sample rate {sr} not supported. Use 8000, 16000, 32000, or 48000")
    
    # Convert float audio to int16
    audio_int16 = (audio * 32767).astype(np.int16)
    
    # Initialize VAD
    vad = webrtcvad.Vad(VAD_AGGRESSIVENESS)
    
    # Calculate frame size
    frame_size = int(sr * frame_duration_ms / 1000)
    
    # Process frames
    segments = []
    current_segment = None
    vad_error_count = 0
    
    for i in range(0, len(audio_int16), frame_size):
        frame = audio_int16[i:i + frame_size]
        
        # Skip incomplete frames
        if len(frame) < frame_size:
            break
            
        # Convert to bytes
        frame_bytes = struct.pack("%dh" % len(frame), *frame)
        
        # Detect speech
        try:
            is_speech = vad.is_speech(frame_bytes, sr)
        except Exception as e:
            vad_error_count += 1
            if vad_error_count <= 3:  # Log first few errors only
                logger.warning(f"VAD error at frame {i}: {e}")
            is_speech = False
        
        # Calculate time
        start_time = i / sr
        end_time = (i + frame_size) / sr
        
        # Build segments
        if is_speech:
            if current_segment is None or current_segment["type"] != "speech":
                # Start new speech segment
                if current_segment is not None:
                    segments.append(current_segment)
                current_segment = {
                    "start_s": start_time,
                    "end_s": end_time,
                    "type": "speech"
                }
            else:
                # Extend current speech segment
                current_segment["end_s"] = end_time
        else:
            if current_segment is None or current_segment["type"] != "silence":
                # Start new silence segment
                if current_segment is not None:
                    segments.append(current_segment)
                current_segment = {
                    "start_s": start_time,
                    "end_s": end_time,
                    "type": "silence"
                }
            else:
                # Extend current silence segment
                current_segment["end_s"] = end_time
    
    # Add last segment
    if current_segment is not None:
        segments.append(current_segment)
    
    # Log if there were many VAD errors
    if vad_error_count > 3:
        logger.warning(f"VAD encountered {vad_error_count} total errors during processing")
    
    return segments


def compute_timing_metrics(segments: List[Dict], total_duration: float) -> Dict:
    """
    Compute timing metrics from VAD segments.
    
    Args:
        segments: List of segments from segment_speech
        total_duration: Total audio duration in seconds
        
    Returns:
        Dictionary of timing metrics
    """
    speech_duration = 0
    silence_duration = 0
    pause_events = []
    
    for segment in segments:
        duration = segment["end_s"] - segment["start_s"]
        
        if segment["type"] == "speech":
            speech_duration += duration
        else:
            silence_duration += duration
            pause_events.append({
                "start_s": segment["start_s"],
                "end_s": segment["end_s"],
                "duration_ms": duration * 1000
            })
    
    # Filter meaningful pauses
    meaningful_pauses = [p for p in pause_events if p["duration_ms"] > MEANINGFUL_PAUSE_MS]
    long_pauses = [p for p in pause_events if p["duration_ms"] > LONG_PAUSE_MS]
    
    # Calculate metrics
    speech_ratio = speech_duration / total_duration if total_duration > 0 else 0
    silence_ratio = silence_duration / total_duration if total_duration > 0 else 0
    pause_count = len(meaningful_pauses)
    mean_pause_ms = np.mean([p["duration_ms"] for p in meaningful_pauses]) if meaningful_pauses else 0
    
    return {
        "total_speech_ms": speech_duration * 1000,
        "total_silence_ms": silence_duration * 1000,
        "speech_ratio": round(speech_ratio, 3),
        "silence_ratio": round(silence_ratio, 3),
        "pause_count": pause_count,
        "mean_pause_ms": round(mean_pause_ms, 1),
        "long_pauses": long_pauses,
        "pause_events": meaningful_pauses
    }


def get_speech_only_audio(audio: np.ndarray, sr: int, segments: List[Dict]) -> np.ndarray:
    """
    Extract only speech portions from audio.
    
    Args:
        audio: Full audio array
        sr: Sample rate
        segments: Segments from segment_speech
        
    Returns:
        Audio array containing only speech
    """
    speech_segments = [s for s in segments if s["type"] == "speech"]
    
    if not speech_segments:
        logger.warning("No speech segments found, returning full audio")
        return audio
    
    speech_audio = []
    for segment in speech_segments:
        start_idx = int(segment["start_s"] * sr)
        end_idx = int(segment["end_s"] * sr)
        speech_audio.append(audio[start_idx:end_idx])
    
    return np.concatenate(speech_audio) if speech_audio else audio
