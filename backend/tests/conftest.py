"""
Pytest configuration and fixtures for the test suite.
"""
import pytest
import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def sample_audio_16k():
    """Generate sample audio at 16kHz"""
    import numpy as np
    sr = 16000
    duration = 2  # seconds
    t = np.linspace(0, duration, sr * duration)
    # Mix of frequencies to simulate voice
    audio = (
        0.3 * np.sin(2 * np.pi * 150 * t) +
        0.2 * np.sin(2 * np.pi * 300 * t) +
        0.1 * np.sin(2 * np.pi * 450 * t)
    ).astype(np.float32)
    return audio, sr


@pytest.fixture
def silent_audio_16k():
    """Generate silent audio at 16kHz"""
    import numpy as np
    sr = 16000
    duration = 1  # second
    audio = np.zeros(sr * duration, dtype=np.float32)
    return audio, sr


@pytest.fixture
def sample_vad_segments():
    """Sample VAD segments for testing"""
    return [
        {"start_s": 0.0, "end_s": 1.0, "type": "speech"},
        {"start_s": 1.0, "end_s": 1.5, "type": "silence"},
        {"start_s": 1.5, "end_s": 3.0, "type": "speech"},
        {"start_s": 3.0, "end_s": 3.3, "type": "silence"},
        {"start_s": 3.3, "end_s": 5.0, "type": "speech"},
    ]
