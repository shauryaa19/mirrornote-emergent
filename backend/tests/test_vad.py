"""
Tests for VAD (Voice Activity Detection) module.

Run with: pytest tests/test_vad.py -v
"""
import pytest
import numpy as np
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import vad


class TestSegmentSpeech:
    """Tests for segment_speech function"""
    
    def test_rejects_invalid_sample_rate(self):
        """Should raise error for unsupported sample rates"""
        audio = np.zeros(1000)
        with pytest.raises(ValueError, match="not supported"):
            vad.segment_speech(audio, sr=22050)  # Not a valid WebRTC VAD rate
    
    def test_accepts_valid_sample_rates(self):
        """Should accept 8000, 16000, 32000, 48000 Hz"""
        for sr in [8000, 16000, 32000, 48000]:
            audio = np.zeros(sr)  # 1 second of silence
            segments = vad.segment_speech(audio, sr)
            assert isinstance(segments, list)
    
    def test_returns_segments_with_correct_structure(self):
        """Should return segments with start_s, end_s, type"""
        audio = np.zeros(16000)  # 1 second
        segments = vad.segment_speech(audio, sr=16000)
        
        for segment in segments:
            assert "start_s" in segment
            assert "end_s" in segment
            assert "type" in segment
            assert segment["type"] in ["speech", "silence"]
    
    def test_silent_audio_returns_silence_segments(self):
        """Should detect silence in silent audio"""
        audio = np.zeros(16000 * 2)  # 2 seconds of silence
        segments = vad.segment_speech(audio, sr=16000)
        
        # Should have at least one segment
        assert len(segments) > 0
        # All segments should be silence
        for segment in segments:
            assert segment["type"] == "silence"
    
    def test_handles_short_audio(self):
        """Should handle audio shorter than frame size"""
        audio = np.zeros(100)  # Very short
        segments = vad.segment_speech(audio, sr=16000, frame_duration_ms=30)
        assert isinstance(segments, list)


class TestComputeTimingMetrics:
    """Tests for compute_timing_metrics function"""
    
    def test_empty_segments(self):
        """Should handle empty segments list"""
        metrics = vad.compute_timing_metrics([], total_duration=10.0)
        assert metrics["total_speech_ms"] == 0
        assert metrics["total_silence_ms"] == 0
        assert metrics["pause_count"] == 0
    
    def test_all_speech(self):
        """Should correctly calculate all-speech metrics"""
        segments = [
            {"start_s": 0, "end_s": 5, "type": "speech"}
        ]
        metrics = vad.compute_timing_metrics(segments, total_duration=5.0)
        
        assert metrics["total_speech_ms"] == 5000
        assert metrics["total_silence_ms"] == 0
        assert metrics["speech_ratio"] == 1.0
        assert metrics["pause_count"] == 0
    
    def test_mixed_segments(self):
        """Should correctly process mixed speech/silence"""
        segments = [
            {"start_s": 0, "end_s": 2, "type": "speech"},
            {"start_s": 2, "end_s": 3, "type": "silence"},  # 1s pause
            {"start_s": 3, "end_s": 5, "type": "speech"},
        ]
        metrics = vad.compute_timing_metrics(segments, total_duration=5.0)
        
        assert metrics["total_speech_ms"] == 4000
        assert metrics["total_silence_ms"] == 1000
        assert metrics["speech_ratio"] == 0.8
    
    def test_meaningful_pause_threshold(self):
        """Should only count pauses > 200ms as meaningful"""
        segments = [
            {"start_s": 0, "end_s": 1, "type": "speech"},
            {"start_s": 1, "end_s": 1.1, "type": "silence"},  # 100ms - not meaningful
            {"start_s": 1.1, "end_s": 2, "type": "speech"},
            {"start_s": 2, "end_s": 2.5, "type": "silence"},  # 500ms - meaningful
            {"start_s": 2.5, "end_s": 3, "type": "speech"},
        ]
        metrics = vad.compute_timing_metrics(segments, total_duration=3.0)
        
        assert metrics["pause_count"] == 1  # Only the 500ms pause
    
    def test_long_pause_detection(self):
        """Should detect long pauses (>700ms)"""
        segments = [
            {"start_s": 0, "end_s": 1, "type": "speech"},
            {"start_s": 1, "end_s": 2, "type": "silence"},  # 1000ms - long
            {"start_s": 2, "end_s": 3, "type": "speech"},
        ]
        metrics = vad.compute_timing_metrics(segments, total_duration=3.0)
        
        assert len(metrics["long_pauses"]) == 1
        assert metrics["long_pauses"][0]["duration_ms"] == 1000


class TestGetSpeechOnlyAudio:
    """Tests for get_speech_only_audio function"""
    
    def test_returns_full_audio_if_no_speech(self):
        """Should return full audio if no speech segments found"""
        audio = np.array([1, 2, 3, 4, 5])
        segments = [{"start_s": 0, "end_s": 1, "type": "silence"}]
        
        result = vad.get_speech_only_audio(audio, sr=5, segments=segments)
        assert np.array_equal(result, audio)
    
    def test_extracts_speech_portions(self):
        """Should extract only speech portions"""
        audio = np.arange(100)  # 0-99
        sr = 10  # 10 samples = 1 second
        segments = [
            {"start_s": 0, "end_s": 2, "type": "silence"},   # samples 0-19
            {"start_s": 2, "end_s": 5, "type": "speech"},    # samples 20-49
            {"start_s": 5, "end_s": 7, "type": "silence"},   # samples 50-69
            {"start_s": 7, "end_s": 10, "type": "speech"},   # samples 70-99
        ]
        
        result = vad.get_speech_only_audio(audio, sr=sr, segments=segments)
        
        # Should have samples 20-49 and 70-99
        assert len(result) == 60
    
    def test_handles_empty_segments(self):
        """Should return full audio for empty segments"""
        audio = np.array([1, 2, 3])
        result = vad.get_speech_only_audio(audio, sr=16000, segments=[])
        assert np.array_equal(result, audio)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
