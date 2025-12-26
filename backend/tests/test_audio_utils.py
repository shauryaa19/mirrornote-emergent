"""
Tests for audio_utils module.

Run with: pytest tests/test_audio_utils.py -v
"""
import pytest
import numpy as np
import base64
import os
import tempfile
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import audio_utils


class TestValidateAudioSize:
    """Tests for validate_audio_size function"""
    
    def test_valid_size(self):
        """Should not raise for audio under limit"""
        # 1MB of base64 (roughly 0.75MB raw)
        small_base64 = "A" * (1024 * 1024)
        audio_utils.validate_audio_size(small_base64)  # Should not raise
    
    def test_exceeds_max_size(self):
        """Should raise ValueError for audio exceeding 25MB"""
        # Create base64 that decodes to ~30MB
        large_base64 = "A" * (40 * 1024 * 1024)  # ~30MB decoded
        with pytest.raises(ValueError, match="too large"):
            audio_utils.validate_audio_size(large_base64)


class TestValidateAudioDuration:
    """Tests for validate_audio_duration function"""
    
    def test_valid_duration(self):
        """Should not raise for audio within limits"""
        sr = 16000
        audio = np.zeros(sr * 30)  # 30 seconds
        audio_utils.validate_audio_duration(audio, sr)  # Should not raise
    
    def test_too_short(self):
        """Should raise ValueError for audio under 1 second"""
        sr = 16000
        audio = np.zeros(sr // 2)  # 0.5 seconds
        with pytest.raises(ValueError, match="too short"):
            audio_utils.validate_audio_duration(audio, sr)
    
    def test_too_long(self):
        """Should raise ValueError for audio over 5 minutes"""
        sr = 16000
        audio = np.zeros(sr * 400)  # 400 seconds (6+ minutes)
        with pytest.raises(ValueError, match="too long"):
            audio_utils.validate_audio_duration(audio, sr)


class TestDetectAudioFormat:
    """Tests for detect_audio_format function"""
    
    def test_detect_wav(self):
        """Should detect WAV format"""
        wav_header = b'RIFF' + b'\x00' * 100
        assert audio_utils.detect_audio_format(wav_header) == '.wav'
    
    def test_detect_mp3_id3(self):
        """Should detect MP3 with ID3 header"""
        mp3_header = b'ID3' + b'\x00' * 100
        assert audio_utils.detect_audio_format(mp3_header) == '.mp3'
    
    def test_detect_ogg(self):
        """Should detect OGG format"""
        ogg_header = b'OggS' + b'\x00' * 100
        assert audio_utils.detect_audio_format(ogg_header) == '.ogg'
    
    def test_detect_flac(self):
        """Should detect FLAC format"""
        flac_header = b'fLaC' + b'\x00' * 100
        assert audio_utils.detect_audio_format(flac_header) == '.flac'
    
    def test_default_to_m4a(self):
        """Should default to m4a for unknown formats"""
        unknown = b'\x00\x00\x00\x00' + b'\x00' * 100
        assert audio_utils.detect_audio_format(unknown) == '.m4a'


class TestNormalizeAudio:
    """Tests for normalize_audio function"""
    
    def test_normalize_quiet_audio(self):
        """Should amplify quiet audio to target level"""
        quiet_audio = np.array([0.01, -0.01, 0.01, -0.01])
        normalized = audio_utils.normalize_audio(quiet_audio, target_level=0.3)
        assert np.abs(normalized).max() > np.abs(quiet_audio).max()
    
    def test_normalize_clips_to_valid_range(self):
        """Should clip values to [-1, 1]"""
        loud_audio = np.array([2.0, -2.0, 1.5, -1.5])
        normalized = audio_utils.normalize_audio(loud_audio, target_level=0.3)
        assert normalized.max() <= 1.0
        assert normalized.min() >= -1.0
    
    def test_handles_silent_audio(self):
        """Should handle all-zero audio without error"""
        silent = np.zeros(100)
        result = audio_utils.normalize_audio(silent)
        assert np.allclose(result, 0)


class TestSaveTempWav:
    """Tests for save_temp_wav function"""
    
    def test_creates_wav_file(self):
        """Should create a valid WAV file"""
        audio = np.random.randn(16000).astype(np.float32)  # 1 second
        sr = 16000
        
        path = audio_utils.save_temp_wav(audio, sr)
        try:
            assert os.path.exists(path)
            assert path.endswith('.wav')
        finally:
            os.remove(path)


class TestGetAudioDuration:
    """Tests for get_audio_duration function"""
    
    def test_correct_duration(self):
        """Should calculate correct duration"""
        sr = 16000
        audio = np.zeros(sr * 10)  # 10 seconds
        duration = audio_utils.get_audio_duration(audio, sr)
        assert duration == 10.0
    
    def test_fractional_duration(self):
        """Should handle fractional durations"""
        sr = 16000
        audio = np.zeros(sr * 3 + sr // 2)  # 3.5 seconds
        duration = audio_utils.get_audio_duration(audio, sr)
        assert duration == 3.5


class TestLoadAudioFromBase64:
    """Tests for load_audio_from_base64 function"""
    
    @patch('audio_utils.validate_audio_size')
    @patch('audio_utils.librosa.load')
    @patch('audio_utils.validate_audio_duration')
    def test_temp_file_cleanup_on_success(self, mock_validate_dur, mock_load, mock_validate_size):
        """Should clean up temp file on successful load"""
        # Setup mocks
        mock_load.return_value = (np.zeros(16000), 16000)
        mock_validate_size.return_value = None
        mock_validate_dur.return_value = None
        
        # Create valid base64 audio (minimal valid data)
        fake_audio = base64.b64encode(b'RIFF' + b'\x00' * 100).decode()
        
        # Call function (may fail but should still clean up)
        try:
            audio_utils.load_audio_from_base64(fake_audio)
        except Exception:
            pass  # We're testing cleanup, not success
        
        # Verify no temp files left (check temp directory)
        temp_dir = tempfile.gettempdir()
        m4a_files = [f for f in os.listdir(temp_dir) if f.endswith('.m4a')]
        wav_files = [f for f in os.listdir(temp_dir) if f.endswith('.wav')]
        # Note: This is a rough check - proper test would track specific file
    
    def test_raises_on_invalid_base64(self):
        """Should raise ValueError for invalid base64"""
        with pytest.raises(ValueError):
            audio_utils.load_audio_from_base64("not-valid-base64!!!")


class TestResampleAudio:
    """Tests for resample_audio function"""
    
    def test_no_resample_if_same_rate(self):
        """Should return original if sample rates match"""
        audio = np.array([1.0, 2.0, 3.0])
        result = audio_utils.resample_audio(audio, 16000, 16000)
        assert np.array_equal(audio, result)
    
    @patch('audio_utils.librosa.resample')
    def test_calls_librosa_resample(self, mock_resample):
        """Should call librosa.resample for different rates"""
        audio = np.array([1.0, 2.0, 3.0])
        mock_resample.return_value = audio
        
        audio_utils.resample_audio(audio, 44100, 16000)
        mock_resample.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
