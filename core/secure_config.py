# core/secure_config.py

"""
🔒 Secure Configuration Manager

Handles loading of sensitive configuration from environment variables
and provides secure access to credentials and settings.

Key Features:
- Environment variable loading with validation
- Secure credential storage
- Configuration validation
- Fallback to defaults for non-sensitive settings

Author: Security Team
"""

import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SecureConfigManager:
    """
    Secure configuration manager that loads sensitive data from environment
    variables and non-sensitive data from configuration files.
    """
    
    def __init__(self, env_file: Optional[str] = None):
        """
        Initialize the secure configuration manager
        
        Args:
            env_file: Path to .env file (defaults to .env in project root)
        """
        # Load environment variables
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()
        
        # Load base configuration
        self.config = self._load_base_config()
        
        # Override with environment variables
        self._apply_environment_overrides()
        
        # Validate configuration
        self._validate_configuration()
        
        logger.info("✅ Secure configuration loaded successfully")
    
    def _load_base_config(self) -> Dict[str, Any]:
        """Load base configuration from YAML file"""
        config_path = Path("configs/global.yaml")
        
        if not config_path.exists():
            logger.warning(f"Configuration file not found: {config_path}")
            return {}
        
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                return config
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            return {}
    
    def _apply_environment_overrides(self):
        """Apply environment variable overrides to configuration"""
        # IG API Credentials (sensitive - must come from environment)
        self.config['ig'] = {
            'api_key': os.getenv('IG_API_KEY', ''),
            'username': os.getenv('IG_USERNAME', ''),
            'password': os.getenv('IG_PASSWORD', ''),
            'base_url': os.getenv('IG_BASE_URL', self.config.get('ig', {}).get('base_url', 'https://demo-api.ig.com/gateway/deal')),
            'session_duration': int(os.getenv('IG_SESSION_DURATION', self.config.get('ig', {}).get('session_duration', 3600))),
            'cache_file': self.config.get('ig', {}).get('cache_file', 'session_cache.json'),
            'log_file': self.config.get('ig', {}).get('log_file', 'ig_streaming.log')
        }
        
        # MongoDB Configuration
        mongodb_uri = os.getenv('MONGODB_URI', self.config.get('mongodb', {}).get('uri', 'mongodb://127.0.0.1:27017'))
        self.config['mongodb'] = {
            'uri': mongodb_uri,
            'database': os.getenv('MONGODB_DATABASE', self.config.get('mongodb', {}).get('database', 'ftse100_scalping_bot')),
            'collection': os.getenv('MONGODB_COLLECTION', self.config.get('mongodb', {}).get('collection', 'ftse100'))
        }
        
        # Feature Flags from environment
        if os.getenv('MARGIN_MANAGEMENT_ENABLED') is not None:
            self.config.setdefault('margin_management', {})['enabled'] = os.getenv('MARGIN_MANAGEMENT_ENABLED', 'true').lower() == 'true'
        
        if os.getenv('DYNAMIC_LIMITS_ENABLED') is not None:
            self.config.setdefault('dynamic_limits', {})['enabled'] = os.getenv('DYNAMIC_LIMITS_ENABLED', 'true').lower() == 'true'
        
        if os.getenv('EMERGENCY_PROTECTION_ENABLED') is not None:
            self.config.setdefault('dynamic_limits', {}).setdefault('emergency_protection', {})['enabled'] = \
                os.getenv('EMERGENCY_PROTECTION_ENABLED', 'true').lower() == 'true'
        
        # API Limits from environment
        if os.getenv('API_DAILY_LIMIT'):
            self.config.setdefault('margin_management', {}).setdefault('api_optimization', {})['daily_request_limit'] = \
                int(os.getenv('API_DAILY_LIMIT', 800))
        
        # Cache settings from environment
        if os.getenv('CACHE_DURATION_MINUTES'):
            self.config.setdefault('margin_management', {}).setdefault('api_optimization', {})['cache_duration_minutes'] = \
                int(os.getenv('CACHE_DURATION_MINUTES', 15))
        
        # Log level
        log_level = os.getenv('LOG_LEVEL', 'INFO')
        logging.getLogger().setLevel(getattr(logging, log_level))
    
    def _validate_configuration(self):
        """Validate that all required configuration is present"""
        errors = []
        
        # Check for required IG credentials
        ig_config = self.config.get('ig', {})
        if not ig_config.get('api_key'):
            errors.append("IG_API_KEY environment variable is required")
        if not ig_config.get('username'):
            errors.append("IG_USERNAME environment variable is required")
        if not ig_config.get('password'):
            errors.append("IG_PASSWORD environment variable is required")
        
        # Check for MongoDB configuration
        mongodb_config = self.config.get('mongodb', {})
        if not mongodb_config.get('uri'):
            errors.append("MongoDB URI is required")
        
        # Raise error if any validation fails
        if errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Mask sensitive values for logging
        masked_config = self._mask_sensitive_values(self.config.copy())
        logger.info(f"Configuration validated successfully")
        logger.debug(f"Configuration: {masked_config}")
    
    def _mask_sensitive_values(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Mask sensitive values in configuration for safe logging"""
        if 'ig' in config:
            if 'api_key' in config['ig'] and config['ig']['api_key']:
                config['ig']['api_key'] = config['ig']['api_key'][:8] + '...' if len(config['ig']['api_key']) > 8 else '***'
            if 'password' in config['ig'] and config['ig']['password']:
                config['ig']['password'] = '***'
            if 'username' in config['ig'] and config['ig']['username']:
                config['ig']['username'] = config['ig']['username'][:3] + '***' if len(config['ig']['username']) > 3 else '***'
        
        return config
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key
        
        Args:
            key: Configuration key (supports dot notation, e.g., 'ig.api_key')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        
        return value
    
    def get_ig_credentials(self) -> Dict[str, str]:
        """
        Get IG API credentials
        
        Returns:
            Dictionary with api_key, username, and password
        """
        return {
            'api_key': self.config['ig']['api_key'],
            'username': self.config['ig']['username'],
            'password': self.config['ig']['password'],
            'base_url': self.config['ig']['base_url']
        }
    
    def get_mongodb_config(self) -> Dict[str, str]:
        """
        Get MongoDB configuration
        
        Returns:
            Dictionary with uri, database, and collection
        """
        return self.config['mongodb']
    
    def is_feature_enabled(self, feature: str) -> bool:
        """
        Check if a feature is enabled
        
        Args:
            feature: Feature name (e.g., 'margin_management', 'dynamic_limits')
            
        Returns:
            True if feature is enabled, False otherwise
        """
        if feature == 'margin_management':
            return self.config.get('margin_management', {}).get('enabled', False)
        elif feature == 'dynamic_limits':
            return self.config.get('dynamic_limits', {}).get('enabled', False)
        elif feature == 'emergency_protection':
            return self.config.get('dynamic_limits', {}).get('emergency_protection', {}).get('enabled', False)
        else:
            return False
    
    def get_api_limits(self) -> Dict[str, int]:
        """
        Get API limit configuration
        
        Returns:
            Dictionary with API limit settings
        """
        api_config = self.config.get('margin_management', {}).get('api_optimization', {})
        return {
            'daily_request_limit': api_config.get('daily_request_limit', 800),
            'cache_duration_minutes': api_config.get('cache_duration_minutes', 15),
            'emergency_api_reserve': api_config.get('emergency_api_reserve', 50)
        }
    
    def reload(self):
        """Reload configuration from environment and files"""
        logger.info("Reloading configuration...")
        self.__init__()

# Global instance
_secure_config = None

def get_secure_config() -> SecureConfigManager:
    """Get global secure configuration instance"""
    global _secure_config
    if _secure_config is None:
        _secure_config = SecureConfigManager()
    return _secure_config

# Convenience function for getting configuration values
def get_config(key: str, default: Any = None) -> Any:
    """
    Get configuration value by key
    
    Args:
        key: Configuration key (supports dot notation)
        default: Default value if key not found
        
    Returns:
        Configuration value or default
    """
    return get_secure_config().get(key, default)

if __name__ == "__main__":
    # Test the secure configuration manager
    print("🧪 Testing Secure Configuration Manager")
    print("=" * 50)
    
    try:
        # Initialize configuration
        config_manager = SecureConfigManager()
        
        # Test getting values
        print("\n📊 Configuration Status:")
        print(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
        print(f"Margin Management: {'✅ Enabled' if config_manager.is_feature_enabled('margin_management') else '❌ Disabled'}")
        print(f"Dynamic Limits: {'✅ Enabled' if config_manager.is_feature_enabled('dynamic_limits') else '❌ Disabled'}")
        print(f"Emergency Protection: {'✅ Enabled' if config_manager.is_feature_enabled('emergency_protection') else '❌ Disabled'}")
        
        # Test API limits
        api_limits = config_manager.get_api_limits()
        print(f"\n📡 API Limits:")
        print(f"Daily Request Limit: {api_limits['daily_request_limit']}")
        print(f"Cache Duration: {api_limits['cache_duration_minutes']} minutes")
        print(f"Emergency Reserve: {api_limits['emergency_api_reserve']} requests")
        
        # Test masked credentials (for logging)
        masked_config = config_manager._mask_sensitive_values(config_manager.config.copy())
        print(f"\n🔒 Masked IG Config: {masked_config.get('ig', {})}")
        
        print("\n✅ Secure configuration manager test completed successfully")
        
    except Exception as e:
        print(f"\n❌ Error testing secure configuration: {e}")
        print("\n💡 Make sure to:")
        print("1. Copy .env.example to .env")
        print("2. Fill in your actual credentials in .env")
        print("3. Never commit .env to version control")