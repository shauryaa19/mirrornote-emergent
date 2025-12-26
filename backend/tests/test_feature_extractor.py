"""
Tests for feature_extractor module.

Run with: pytest tests/test_feature_extractor.py -v
"""
import pytest
import numpy as np
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import feature_extractor


class TestExtractProsody:
    """Tests for extract_prosody function"""
    
    def test_returns_expected_keys(self):
        """Should return all expected prosody metrics"""
        # Generate simple audio (sine wave for voiced content)
        sr = 16000
        t = np.linspace(0, 1, sr)
        audio = np.sin(2 * np.pi * 200 * t).astype(np.float32)  # 200 Hz tone
        
        result = feature_extractor.extract_prosody(audio, sr)
        
        expected_keys = ["pitch_mean", "pitch_std", "pitch_p5", "pitch_p50", 
                         "pitch_p95", "pitch_range_hz", "pitch_series"]
        for key in expected_keys:
            assert key in result
    
    def test_handles_silent_audio(self):
        """Should handle silent audio gracefully"""
        audio = np.zeros(16000)  # 1 second of silence
        result = feature_extractor.extract_prosody(audio, sr=16000)
        
        # Should return zeros, not crash
        assert result["pitch_mean"] == 0
        assert result["pitch_series"] == []
    
    def test_pitch_series_limited(self):
        """Should limit pitch series to 200 points"""
        sr = 16000
        t = np.linspace(0, 10, sr * 10)  # 10 seconds
        audio = np.sin(2 * np.pi * 200 * t).astype(np.float32)
        
        result = feature_extractor.extract_prosody(audio, sr)
        
        assert len(result["pitch_series"]) <= 200


class TestExtractLoudness:
    """Tests for extract_loudness function"""
    
    def test_returns_expected_keys(self):
        """Should return all expected loudness metrics"""
        audio = np.random.randn(16000).astype(np.float32)
        result = feature_extractor.extract_loudness(audio, sr=16000)
        
        expected_keys = ["rms_mean", "rms_std", "dynamic_range_db", "rms_series"]
        for key in expected_keys:
            assert key in result
    
    def test_handles_silent_audio(self):
        """Should handle silent audio gracefully"""
        audio = np.zeros(16000)
        result = feature_extractor.extract_loudness(audio, sr=16000)
        
        assert result["rms_mean"] == 0
    
    def test_dynamic_range_positive(self):
        """Dynamic range should be positive for varying audio"""
        # Create audio with varying amplitude
        audio = np.concatenate([
            np.random.randn(8000) * 0.1,  # Quiet section
            np.random.randn(8000) * 0.5,  # Loud section
        ]).astype(np.float32)
        
        result = feature_extractor.extract_loudness(audio, sr=16000)
        assert result["dynamic_range_db"] >= 0


class TestExtractVoiceQualityLibrosa:
    """Tests for extract_voice_quality_librosa function"""
    
    def test_returns_expected_keys(self):
        """Should return all expected quality metrics"""
        audio = np.random.randn(16000).astype(np.float32)
        result = feature_extractor.extract_voice_quality_librosa(audio, sr=16000)
        
        expected_keys = ["jitter_local", "shimmer_local", "hnr_mean", "method", "is_approximation"]
        for key in expected_keys:
            assert key in result
    
    def test_marks_as_approximation(self):
        """Should indicate these are approximations, not clinical measurements"""
        audio = np.random.randn(16000).astype(np.float32)
        result = feature_extractor.extract_voice_quality_librosa(audio, sr=16000)
        
        assert result["is_approximation"] == True
        assert result["method"] == "librosa_proxy"
    
    def test_values_in_expected_ranges(self):
        """Quality metrics should be in reasonable ranges"""
        audio = np.random.randn(16000).astype(np.float32)
        result = feature_extractor.extract_voice_quality_librosa(audio, sr=16000)
        
        assert 0 <= result["jitter_local"] <= 5
        assert 0 <= result["shimmer_local"] <= 8
        assert 5 <= result["hnr_mean"] <= 20


class TestExtractSpectral:
    """Tests for extract_spectral function"""
    
    def test_returns_expected_keys(self):
        """Should return all expected spectral metrics"""
        audio = np.random.randn(16000).astype(np.float32)
        result = feature_extractor.extract_spectral(audio, sr=16000)
        
        expected_keys = ["mfcc_means", "mfcc_stds", "spectral_centroid_mean", 
                         "rolloff_mean", "bandwidth_mean"]
        for key in expected_keys:
            assert key in result
    
    def test_mfcc_dimensions(self):
        """Should extract 13 MFCCs"""
        audio = np.random.randn(16000).astype(np.float32)
        result = feature_extractor.extract_spectral(audio, sr=16000)
        
        assert len(result["mfcc_means"]) == 13
        assert len(result["mfcc_stds"]) == 13


class TestExtractAllFeatures:
    """Tests for extract_all_features function"""
    
    def test_returns_all_feature_groups(self):
        """Should return prosody, loudness, quality, and spectral"""
        audio = np.random.randn(16000).astype(np.float32)
        result = feature_extractor.extract_all_features(audio, sr=16000)
        
        assert "prosody" in result
        assert "loudness" in result
        assert "quality" in result
        assert "spectral" in result
    
    def test_uses_segments_when_provided(self):
        """Should use VAD segments when provided"""
        audio = np.random.randn(32000).astype(np.float32)  # 2 seconds
        segments = [
            {"start_s": 0, "end_s": 0.5, "type": "silence"},
            {"start_s": 0.5, "end_s": 1.5, "type": "speech"},  # 1 second of speech
            {"start_s": 1.5, "end_s": 2.0, "type": "silence"},
        ]
        
        # This should work without error
        result = feature_extractor.extract_all_features(audio, sr=16000, segments=segments)
        assert "prosody" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
