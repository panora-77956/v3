# -*- coding: utf-8 -*-
"""
Account Manager - Multi-account support for Google Labs API
Provides round-robin load balancing across multiple Google Labs accounts
"""

import json
import os
from typing import List, Dict, Optional, Tuple
from threading import Lock


class LabsAccount:
    """Represents a single Google Labs account with project ID and tokens"""
    
    def __init__(self, name: str, project_id: str, tokens: List[str], enabled: bool = True):
        """
        Initialize a Labs account
        
        Args:
            name: Account display name
            project_id: Google Labs Project ID
            tokens: List of OAuth tokens for this account
            enabled: Whether this account is active
        """
        self.name = name
        self.project_id = project_id
        self.tokens = [t.strip() for t in tokens if t.strip()]
        self.enabled = enabled
        self.usage_count = 0  # Track how many times this account has been used
    
    def to_dict(self) -> Dict:
        """Convert account to dictionary for serialization"""
        return {
            "name": self.name,
            "project_id": self.project_id,
            "tokens": self.tokens,
            "enabled": self.enabled
        }
    
    @staticmethod
    def from_dict(data: Dict) -> 'LabsAccount':
        """Create account from dictionary"""
        return LabsAccount(
            name=data.get("name", ""),
            project_id=data.get("project_id", ""),
            tokens=data.get("tokens", []),
            enabled=data.get("enabled", True)
        )
    
    def __repr__(self):
        return f"LabsAccount(name={self.name}, project_id={self.project_id[:8]}..., tokens={len(self.tokens)}, enabled={self.enabled})"


class AccountManager:
    """
    Manages multiple Google Labs accounts with round-robin load balancing
    Thread-safe for parallel scene generation
    """
    
    def __init__(self, accounts: Optional[List[LabsAccount]] = None):
        """
        Initialize account manager
        
        Args:
            accounts: List of LabsAccount objects (optional)
        """
        self.accounts = accounts or []
        self._current_index = 0
        self._lock = Lock()  # Thread safety for parallel processing
    
    def add_account(self, account: LabsAccount):
        """Add a new account to the manager"""
        with self._lock:
            self.accounts.append(account)
    
    def remove_account(self, index: int):
        """Remove account by index"""
        with self._lock:
            if 0 <= index < len(self.accounts):
                del self.accounts[index]
    
    def get_account(self, index: int) -> Optional[LabsAccount]:
        """Get account by index"""
        with self._lock:
            if 0 <= index < len(self.accounts):
                return self.accounts[index]
        return None
    
    def get_next_account(self) -> Optional[LabsAccount]:
        """
        Get next available account using round-robin algorithm
        Only returns enabled accounts
        
        Returns:
            LabsAccount object or None if no enabled accounts
        """
        with self._lock:
            if not self.accounts:
                return None
            
            # Filter enabled accounts
            enabled = [acc for acc in self.accounts if acc.enabled]
            if not enabled:
                return None
            
            # Round-robin selection
            account = enabled[self._current_index % len(enabled)]
            account.usage_count += 1
            self._current_index = (self._current_index + 1) % len(enabled)
            
            return account
    
    def get_account_for_scene(self, scene_index: int) -> Optional[LabsAccount]:
        """
        Get account for a specific scene using round-robin
        
        Args:
            scene_index: 0-based scene index
            
        Returns:
            LabsAccount object or None
        """
        with self._lock:
            if not self.accounts:
                return None
            
            enabled = [acc for acc in self.accounts if acc.enabled]
            if not enabled:
                return None
            
            # Deterministic selection based on scene index
            account = enabled[scene_index % len(enabled)]
            account.usage_count += 1
            
            return account
    
    def get_enabled_accounts(self) -> List[LabsAccount]:
        """Get list of enabled accounts"""
        with self._lock:
            return [acc for acc in self.accounts if acc.enabled]
    
    def get_all_accounts(self) -> List[LabsAccount]:
        """Get all accounts (enabled and disabled)"""
        with self._lock:
            return self.accounts.copy()
    
    def enable_account(self, index: int):
        """Enable account by index"""
        with self._lock:
            if 0 <= index < len(self.accounts):
                self.accounts[index].enabled = True
    
    def disable_account(self, index: int):
        """Disable account by index"""
        with self._lock:
            if 0 <= index < len(self.accounts):
                self.accounts[index].enabled = False
    
    def reset_usage_counts(self):
        """Reset usage counts for all accounts"""
        with self._lock:
            for account in self.accounts:
                account.usage_count = 0
    
    def get_usage_stats(self) -> List[Tuple[str, int]]:
        """
        Get usage statistics for all accounts
        
        Returns:
            List of tuples (account_name, usage_count)
        """
        with self._lock:
            return [(acc.name, acc.usage_count) for acc in self.accounts]
    
    def save_to_config(self, config_dict: Dict):
        """
        Save accounts to config dictionary
        
        Args:
            config_dict: Config dict to update (will modify in place)
        """
        with self._lock:
            config_dict['labs_accounts'] = [acc.to_dict() for acc in self.accounts]
    
    @staticmethod
    def load_from_config(config_dict: Dict) -> 'AccountManager':
        """
        Load accounts from config dictionary
        
        Args:
            config_dict: Config dict with 'labs_accounts' key
            
        Returns:
            AccountManager instance
        """
        accounts_data = config_dict.get('labs_accounts', [])
        accounts = [LabsAccount.from_dict(data) for data in accounts_data]
        return AccountManager(accounts)
    
    def is_multi_account_enabled(self) -> bool:
        """Check if multi-account mode is enabled (2+ enabled accounts)"""
        with self._lock:
            enabled = [acc for acc in self.accounts if acc.enabled]
            return len(enabled) >= 2
    
    def get_primary_account(self) -> Optional[LabsAccount]:
        """
        Get primary account (first enabled account)
        Used for backwards compatibility when multi-account is not enabled
        """
        with self._lock:
            enabled = [acc for acc in self.accounts if acc.enabled]
            return enabled[0] if enabled else None
    
    def __len__(self):
        """Return number of accounts"""
        with self._lock:
            return len(self.accounts)
    
    def __repr__(self):
        with self._lock:
            enabled = sum(1 for acc in self.accounts if acc.enabled)
            return f"AccountManager(total={len(self.accounts)}, enabled={enabled})"


# Global account manager instance
_global_manager: Optional[AccountManager] = None
_manager_lock = Lock()


def get_account_manager() -> AccountManager:
    """
    Get global account manager instance
    Lazy-loads from config on first access
    
    Returns:
        AccountManager instance
    """
    global _global_manager
    
    with _manager_lock:
        if _global_manager is None:
            # Load from config
            try:
                from utils import config as cfg
                config = cfg.load()
                _global_manager = AccountManager.load_from_config(config)
            except Exception as e:
                print(f"[WARN] Failed to load account manager from config: {e}")
                _global_manager = AccountManager()
        
        return _global_manager


def save_account_manager():
    """Save global account manager to config"""
    global _global_manager
    
    with _manager_lock:
        if _global_manager is not None:
            try:
                from utils import config as cfg
                config = cfg.load()
                _global_manager.save_to_config(config)
                cfg.save(config)
            except Exception as e:
                print(f"[ERR] Failed to save account manager to config: {e}")


def reset_account_manager():
    """Reset global account manager (for testing)"""
    global _global_manager
    
    with _manager_lock:
        _global_manager = None
