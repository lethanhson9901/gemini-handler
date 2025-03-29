import time
from itertools import cycle
from typing import List, Tuple

from .data_models import KeyRotationStrategy, KeyStats


class KeyRotationManager:
    """Enhanced key rotation manager with multiple strategies."""
    def __init__(
        self,
        api_keys: List[str],
        strategy: KeyRotationStrategy = KeyRotationStrategy.ROUND_ROBIN,
        rate_limit: int = 60,
        reset_window: int = 60
    ):
        if not api_keys:
            raise ValueError("At least one API key must be provided")
        
        self.api_keys = api_keys
        self.strategy = strategy
        self.rate_limit = rate_limit
        self.reset_window = reset_window
        
        # Initialize tracking
        self.key_stats = {i: KeyStats() for i in range(len(api_keys))}
        self._key_cycle = cycle(range(len(api_keys)))
        self.current_index = 0

    def _is_key_available(self, key_index: int) -> bool:
        """Check if a key is available based on rate limits and cooldown."""
        stats = self.key_stats[key_index]
        current_time = time.time()
        
        if current_time < stats.rate_limited_until:
            return False
            
        if current_time - stats.last_used > self.reset_window:
            stats.uses = 0
            
        return stats.uses < self.rate_limit

    def _get_sequential_key(self) -> Tuple[str, int]:
        """Get next key using sequential strategy."""
        start_index = self.current_index
        
        while True:
            if self._is_key_available(self.current_index):
                key_index = self.current_index
                self.current_index = (self.current_index + 1) % len(self.api_keys)
                return self.api_keys[key_index], key_index
                
            self.current_index = (self.current_index + 1) % len(self.api_keys)
            if self.current_index == start_index:
                self._handle_all_keys_busy()

    def _get_round_robin_key(self) -> Tuple[str, int]:
        """Get next key using round-robin strategy."""
        start_index = next(self._key_cycle)
        current_index = start_index
        
        while True:
            if self._is_key_available(current_index):
                return self.api_keys[current_index], current_index
                
            current_index = next(self._key_cycle)
            if current_index == start_index:
                self._handle_all_keys_busy()

    def _get_least_used_key(self) -> Tuple[str, int]:
        """Get key with lowest usage count."""
        while True:
            available_keys = [
                (idx, stats) for idx, stats in self.key_stats.items()
                if self._is_key_available(idx)
            ]
            
            if available_keys:
                key_index, _ = min(available_keys, key=lambda x: x[1].uses)
                return self.api_keys[key_index], key_index
                
            self._handle_all_keys_busy()

    def _get_smart_cooldown_key(self) -> Tuple[str, int]:
        """Get key using smart cooldown strategy."""
        while True:
            current_time = time.time()
            available_keys = [
                (idx, stats) for idx, stats in self.key_stats.items()
                if current_time >= stats.rate_limited_until and self._is_key_available(idx)
            ]
            
            if available_keys:
                key_index, _ = min(
                    available_keys,
                    key=lambda x: (x[1].failures, -(current_time - x[1].last_used))
                )
                return self.api_keys[key_index], key_index
                
            self._handle_all_keys_busy()

    def _handle_all_keys_busy(self) -> None:
        """Handle situation when all keys are busy."""
        current_time = time.time()
        any_reset = False
        
        for idx, stats in self.key_stats.items():
            if current_time - stats.last_used > self.reset_window:
                stats.uses = 0
                any_reset = True
                
        if not any_reset:
            time.sleep(1)

    def get_next_key(self) -> Tuple[str, int]:
        """Get next available API key based on selected strategy."""
        strategy_methods = {
            KeyRotationStrategy.SEQUENTIAL: self._get_sequential_key,
            KeyRotationStrategy.ROUND_ROBIN: self._get_round_robin_key,
            KeyRotationStrategy.LEAST_USED: self._get_least_used_key,
            KeyRotationStrategy.SMART_COOLDOWN: self._get_smart_cooldown_key
        }
        
        method = strategy_methods.get(self.strategy)
        if not method:
            raise ValueError(f"Unknown strategy: {self.strategy}")
            
        api_key, key_index = method()
        
        stats = self.key_stats[key_index]
        stats.uses += 1
        stats.last_used = time.time()
        
        return api_key, key_index

    def mark_success(self, key_index: int) -> None:
        """Mark successful API call."""
        if 0 <= key_index < len(self.api_keys):
            self.key_stats[key_index].failures = 0

    def mark_rate_limited(self, key_index: int) -> None:
        """Mark API key as rate limited."""
        if 0 <= key_index < len(self.api_keys):
            stats = self.key_stats[key_index]
            stats.failures += 1
            stats.rate_limited_until = time.time() + self.reset_window
            stats.uses = self.rate_limit
