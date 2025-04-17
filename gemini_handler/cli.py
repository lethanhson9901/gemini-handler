# gemini_handler/cli.py

import argparse
import os
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from .data_models import KeyRotationStrategy, Strategy
from .server import GeminiServer


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Run Gemini API Server")
    parser.add_argument(
        "--host", 
        type=str, 
        default="0.0.0.0", 
        help="Host to bind server (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=8000, 
        help="Port to bind server (default: 8000)"
    )
    parser.add_argument(
        "--keys", 
        type=str, 
        default=None,
        help="Comma-separated list of Gemini API keys"
    )
    parser.add_argument(
        "--config", 
        type=str, 
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)"
    )
    
    return parser.parse_args()

def load_config(config_path: str) -> Dict:
    """Load configuration from YAML file."""
    try:
        config_path = Path(config_path)
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                print(f"✓ Loaded configuration from {config_path}")
                return config
        else:
            print(f"! Config file {config_path} not found, using default settings")
            return {}
    except Exception as e:
        print(f"! Error loading config file: {e}")
        return {}

def main():
    """Main entry point for the CLI."""
    args = parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    # Process API keys (priority: CLI args > config file > env vars)
    api_keys = None
    if args.keys:
        api_keys = [k.strip() for k in args.keys.split(',') if k.strip()]
    elif config and 'gemini' in config and 'api_keys' in config['gemini']:
        api_keys = config['gemini']['api_keys']
    
    # Extract server settings from config
    server_settings = {}
    if config and 'gemini' in config:
        gemini_config = config['gemini']
        
        # Extract generation settings
        if 'generation' in gemini_config:
            server_settings['generation_config'] = gemini_config['generation']
        
        # Extract strategy settings
        if 'strategies' in gemini_config:
            strategies = gemini_config['strategies']
            if 'content' in strategies:
                content_strategy_map = {
                    'round_robin': Strategy.ROUND_ROBIN,
                    'fallback': Strategy.FALLBACK,
                    'retry': Strategy.RETRY
                }
                server_settings['content_strategy'] = content_strategy_map.get(
                    strategies['content'], Strategy.ROUND_ROBIN
                )
                
            if 'key_rotation' in strategies:
                key_rotation_map = {
                    'sequential': KeyRotationStrategy.SEQUENTIAL,
                    'round_robin': KeyRotationStrategy.ROUND_ROBIN,
                    'least_used': KeyRotationStrategy.LEAST_USED,
                    'smart_cooldown': KeyRotationStrategy.SMART_COOLDOWN
                }
                server_settings['key_strategy'] = key_rotation_map.get(
                    strategies['key_rotation'], KeyRotationStrategy.ROUND_ROBIN
                )
        
        # Extract rate limiting settings
        if 'rate_limits' in gemini_config:
            rate_limits = gemini_config['rate_limits']
            if 'requests_per_minute' in rate_limits:
                server_settings['rate_limit'] = rate_limits['requests_per_minute']
            if 'reset_window' in rate_limits:
                server_settings['reset_window'] = rate_limits['reset_window']
        
        # Extract retry settings
        if 'retry' in gemini_config:
            retry = gemini_config['retry']
            if 'max_attempts' in retry:
                server_settings['max_retries'] = retry['max_attempts']
            if 'delay' in retry:
                server_settings['retry_delay'] = retry['delay']
        
        # Extract system instruction
        if 'system_instruction' in gemini_config:
            server_settings['system_instruction'] = gemini_config['system_instruction']
    
    # Extract proxy settings if available
    proxy_settings = None
    if config and 'proxy' in config:
        proxy_settings = config['proxy']
    
    # Create and run server
    server = GeminiServer(
        api_keys=api_keys,
        host=args.host,
        port=args.port,
        proxy_settings=proxy_settings,
        **server_settings
    )
    
    # Print server info
    print(f"✓ Gemini API Server running at http://{args.host}:{args.port}")
    print("✓ API is compatible with OpenAI format")
    print("✓ Endpoints:")
    print("  - GET  /v1/models")
    print("  - POST /v1/chat/completions")
    print("  - POST /v1/embeddings")
    print("  - GET  /health")
    
    # Run the server
    server.run()

if __name__ == "__main__":
    main()
