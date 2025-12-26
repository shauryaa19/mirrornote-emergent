"""
Tests for insights_generator module.

Run with: pytest tests/test_insights_generator.py -v
"""
import pytest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import insights_generator


class TestGeneratePitchInsight:
    """Tests for generate_pitch_insight function"""
    
    def test_zero_pitch_handling(self):
        """Should handle zero pitch mean gracefully"""
        result = insights_generator.generate_pitch_insight(0, 0, 0)
        assert "natural clarity" in result.lower()
    
    def test_high_pitch_classification(self):
        """Should classify high pitch (>200 Hz)"""
        result = insights_generator.generate_pitch_insight(250, 30, 50)
        assert "higher pitch" in result.lower()
    
    def test_low_pitch_classification(self):
        """Should classify low pitch (<130 Hz)"""
        result = insights_generator.generate_pitch_insight(100, 30, 50)
        assert "deeper voice" in result.lower()
    
    def test_high_variation(self):
        """Should describe high pitch variation (std > 45)"""
        result = insights_generator.generate_pitch_insight(150, 50, 100)
        assert "melody" in result.lower() or "engaged" in result.lower()


class TestGeneratePaceInsight:
    """Tests for generate_pace_insight function"""
    
    def test_fast_pace(self):
        """Should identify fast speaking (>160 WPM)"""
        result = insights_generator.generate_pace_insight(180, 10, 400)
        assert "quick" in result.lower() or "fast" in result.lower()
    
    def test_slow_pace(self):
        """Should identify slow speaking (<120 WPM)"""
        result = insights_generator.generate_pace_insight(100, 10, 400)
        assert "thoughtful" in result.lower()
    
    def test_includes_pause_count(self):
        """Should mention pause count"""
        result = insights_generator.generate_pace_insight(140, 15, 400)
        assert "15" in result or "pause" in result.lower()


class TestGenerateFillerInsight:
    """Tests for generate_filler_insight function"""
    
    def test_no_fillers(self):
        """Should praise absence of fillers"""
        result = insights_generator.generate_filler_insight({}, 100)
        assert "impressive" in result.lower() or "avoided" in result.lower()
    
    def test_high_filler_rate(self):
        """Should flag high filler rate (>5%)"""
        result = insights_generator.generate_filler_insight({"um": 8, "uh": 4}, 100)
        assert "um" in result.lower() or "filler" in result.lower()
    
    def test_mentions_top_fillers(self):
        """Should mention the most common fillers"""
        result = insights_generator.generate_filler_insight({"um": 10, "like": 3}, 200)
        assert "um" in result.lower()


class TestClassifyVoicePersonality:
    """Tests for classify_voice_personality function"""
    
    def test_dynamic_storyteller(self):
        """Should classify as Dynamic Storyteller for high pitch_std + dynamic_range"""
        metrics = {
            "prosody": {"pitch_std": 50},
            "loudness": {"dynamic_range_db": 15},
            "timing": {"silence_ratio": 0.2},
            "speaking_pace": 140
        }
        result = insights_generator.classify_voice_personality(metrics)
        assert "Dynamic" in result or "Storyteller" in result
    
    def test_steady_professional(self):
        """Should classify as Steady Professional for low variation"""
        metrics = {
            "prosody": {"pitch_std": 20},
            "loudness": {"dynamic_range_db": 6},
            "timing": {"silence_ratio": 0.2},
            "speaking_pace": 140
        }
        result = insights_generator.classify_voice_personality(metrics)
        assert "Steady" in result or "Professional" in result


class TestGeneratePersonalizedSummary:
    """Tests for generate_personalized_summary function"""
    
    def test_returns_all_required_keys(self):
        """Should return all expected insight keys"""
        metrics = {
            "prosody": {"pitch_mean": 150, "pitch_std": 30, "pitch_range_hz": 80},
            "loudness": {"rms_mean": 0.1, "dynamic_range_db": 10},
            "quality": {"jitter_local": 2, "shimmer_local": 4, "hnr_mean": 15},
            "timing": {"pause_count": 8, "mean_pause_ms": 400, "long_pauses": []},
            "filler_words": {"um": 2},
            "word_count": 150,
            "speaking_pace": 140,
            "duration": 60
        }
        
        result = insights_generator.generate_personalized_summary(metrics)
        
        assert "voice_personality" in result
        assert "headline" in result
        assert "key_insights" in result
        assert "what_went_well" in result
        assert "growth_opportunities" in result
        assert "tone_description" in result
    
    def test_limits_array_sizes(self):
        """Should limit arrays to reasonable sizes"""
        metrics = {
            "prosody": {"pitch_mean": 150, "pitch_std": 30, "pitch_range_hz": 80},
            "loudness": {"rms_mean": 0.1, "dynamic_range_db": 10},
            "quality": {"jitter_local": 2, "shimmer_local": 4, "hnr_mean": 15},
            "timing": {"pause_count": 8, "mean_pause_ms": 400, "long_pauses": []},
            "filler_words": {"um": 2, "uh": 3, "like": 5},
            "word_count": 150,
            "speaking_pace": 140,
            "duration": 60
        }
        
        result = insights_generator.generate_personalized_summary(metrics)
        
        assert len(result["key_insights"]) <= 7
        assert len(result["what_went_well"]) <= 4
        assert len(result["growth_opportunities"]) <= 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
