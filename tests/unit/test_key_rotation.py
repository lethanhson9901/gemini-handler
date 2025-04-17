# tests/unit/test_key_rotation.py
import time
import pytest
from gemini_handler.key_rotation import KeyRotationManager
from gemini_handler.data_models import KeyRotationStrategy


class TestKeyRotationManager:
    """Tests for the KeyRotationManager class"""
    
    def test_init_with_valid_keys(self):
        """Test initialization with valid API keys"""
        keys = ["key1", "key2", "key3"]
        manager = KeyRotationManager(api_keys=keys)
        assert len(manager.api_keys) == 3
        assert manager.strategy == KeyRotationStrategy.ROUND_ROBIN  # Default
    
    def test_init_with_empty_keys(self):
        """Test initialization with empty API keys list raises ValueError"""
        with pytest.raises(ValueError):
            KeyRotationManager(api_keys=[])
    
    def test_get_sequential_key(self):
        """Test sequential key rotation strategy"""
        keys = ["key1", "key2", "key3"]
        manager = KeyRotationManager(
            api_keys=keys, 
            strategy=KeyRotationStrategy.SEQUENTIAL
        )
        
        # First call should return first key
        key, idx = manager.get_next_key()
        assert key == "key1"
        assert idx == 0
        
        # Second call should return second key
        key, idx = manager.get_next_key()
        assert key == "key2"
        assert idx == 1
        
        # Third call should return third key
        key, idx = manager.get_next_key()
        assert key == "key3"
        assert idx == 2
        
        # Fourth call should wrap around to first key
        key, idx = manager.get_next_key()
        assert key == "key1"
        assert idx == 0
    
    def test_get_round_robin_key(self):
        """Test round-robin key rotation strategy"""
        keys = ["key1", "key2", "key3"]
        manager = KeyRotationManager(
            api_keys=keys, 
            strategy=KeyRotationStrategy.ROUND_ROBIN
        )
        
        # Get all keys and verify we get each one
        used_keys = set()
        for _ in range(len(keys)):
            key, _ = manager.get_next_key()
            used_keys.add(key)
        
        assert used_keys == set(keys)
    
    def test_mark_rate_limited(self):
        """Test marking a key as rate limited"""
        keys = ["key1", "key2", "key3"]
        manager = KeyRotationManager(
            api_keys=keys, 
            strategy=KeyRotationStrategy.SEQUENTIAL,
            rate_limit=2,  # Low limit for testing
            reset_window=0.5  # Short window for testing
        )
        
        # Get a key and mark it rate limited
        _, idx = manager.get_next_key()
        manager.mark_rate_limited(idx)
        
        # Verify key stats
        stats = manager.key_stats[idx]
        assert stats.uses == 2  # Set to rate_limit
        assert stats.failures == 1
        assert stats.rate_limited_until > time.time()
        
        # Get next key - should be different
        _, new_idx = manager.get_next_key()
        assert new_idx != idx
    
    def test_key_reset_after_window(self):
        """Test key reset after reset window"""
        keys = ["key1", "key2", "key3"]
        reset_window = 0.1  # Very short for testing
        manager = KeyRotationManager(
            api_keys=keys, 
            strategy=KeyRotationStrategy.SEQUENTIAL,
            reset_window=reset_window
        )
        
        # Use a key multiple times
        key, idx = manager.get_next_key()
        manager.key_stats[idx].uses = 10
        manager.key_stats[idx].last_used = time.time() - (reset_window * 2)  # Past reset window
        
        # Use the key again - should be reset
        key, idx = manager.get_next_key()
        assert manager.key_stats[idx].uses == 1  # Reset to 0 then incremented by this use
