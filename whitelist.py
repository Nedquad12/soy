#!/usr/bin/env python3
"""
Whitelist Management Utilities
Untuk memudahkan pengelolaan whitelist bot Telegram Stock Monitor
"""

import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Set
import argparse

class WhitelistManager:
    def __init__(self, whitelist_file: str = 'whitelist.json'):
        self.whitelist_file = whitelist_file
        self.data = self.load_whitelist()
    
    def load_whitelist(self) -> Dict:
        """Load whitelist from file"""
        if os.path.exists(self.whitelist_file):
            try:
                with open(self.whitelist_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading whitelist: {e}")
                return self.get_default_structure()
        return self.get_default_structure()
    
    def get_default_structure(self) -> Dict:
        """Get default whitelist structure"""
        return {
            'users': [],
            'groups': [],
            'enabled': True,
            'metadata': {
                'created': datetime.now().isoformat(),
                'last_modified': datetime.now().isoformat(),
                'version': '1.0'
            }
        }
    
    def save_whitelist(self):
        """Save whitelist to file"""
        self.data['metadata']['last_modified'] = datetime.now().isoformat()
        try:
            with open(self.whitelist_file, 'w') as f:
                json.dump(self.data, f, indent=2)
            print(f"✅ Whitelist saved to {self.whitelist_file}")
        except Exception as e:
            print(f"❌ Error saving whitelist: {e}")
    
    def add_user(self, user_id: int) -> bool:
        """Add user to whitelist"""
        if user_id not in self.data['users']:
            self.data['users'].append(user_id)
            self.save_whitelist()
            print(f"✅ User {user_id} added to whitelist")
            return True
        else:
            print(f"⚠️ User {user_id} already in whitelist")
            return False
    
    def remove_user(self, user_id: int) -> bool:
        """Remove user from whitelist"""
        if user_id in self.data['users']:
            self.data['users'].remove(user_id)
            self.save_whitelist()
            print(f"✅ User {user_id} removed from whitelist")
            return True
        else:
            print(f"⚠️ User {user_id} not found in whitelist")
            return False
    
    def add_group(self, group_id: int) -> bool:
        """Add group to whitelist"""
        if group_id not in self.data['groups']:
            self.data['groups'].append(group_id)
            self.save_whitelist()
            print(f"✅ Group {group_id} added to whitelist")
            return True
        else:
            print(f"⚠️ Group {group_id} already in whitelist")
            return False
    
    def remove_group(self, group_id: int) -> bool:
        """Remove group from whitelist"""
        if group_id in self.data['groups']:
            self.data['groups'].remove(group_id)
            self.save_whitelist()
            print(f"✅ Group {group_id} removed from whitelist")
            return True
        else:
            print(f"⚠️ Group {group_id} not found in whitelist")
            return False
    
    def enable_whitelist(self):
        """Enable whitelist system"""
        self.data['enabled'] = True
        self.save_whitelist()
        print("✅ Whitelist system enabled")
    
    def disable_whitelist(self):
        """Disable whitelist system"""
        self.data['enabled'] = False
        self.save_whitelist()
        print("❌ Whitelist system disabled")
    
    def show_status(self):
        """Show whitelist status"""
        status = "✅ Enabled" if self.data['enabled'] else "❌ Disabled"
        print(f"\n📊 Whitelist Status: {status}")
        print(f"👤 Users: {len(self.data['users'])}")
        print(f"💬 Groups: {len(self.data['groups'])}")
        print(f"📅 Last Modified: {self.data['metadata']['last_modified']}")
    
    def list_all(self):
        """List all whitelisted users and groups"""
        print("\n📋 Whitelist Contents:")
        print(f"Status: {'✅ Enabled' if self.data['enabled'] else '❌ Disabled'}")
        
        if self.data['users']:
            print(f"\n👤 Users ({len(self.data['users'])}):")
            for user_id in self.data['users']:
                print(f"  • {user_id}")
        else:
            print("\n👤 Users: None")
        
        if self.data['groups']:
            print(f"\n💬 Groups ({len(self.data['groups'])}):")
            for group_id in self.data['groups']:
                print(f"  • {group_id}")
        else:
            print("\n💬 Groups: None")
    
    def backup_whitelist(self, backup_file: str = None):
        """Create backup of whitelist"""
        if backup_file is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = f"whitelist_backup_{timestamp}.json"
        
        try:
            with open(backup_file, 'w') as f:
                json.dump(self.data, f, indent=2)
            print(f"✅ Backup created: {backup_file}")
        except Exception as e:
            print(f"❌ Error creating backup: {e}")
    
    def restore_whitelist(self, backup_file: str):
        """Restore whitelist from backup"""
        if not os.path.exists(backup_file):
            print(f"❌ Backup file not found: {backup_file}")
            return
        
        try:
            with open(backup_file, 'r') as f:
                self.data = json.load(f)
            self.save_whitelist()
            print(f"✅ Whitelist restored from: {backup_file}")
        except Exception as e:
            print(f"❌ Error restoring backup: {e}")
    
    def import_from_text(self, text_file: str, data_type: str = 'users'):
        """Import users/groups from text file (one per line)"""
        if not os.path.exists(text_file):
            print(f"❌ File not found: {text_file}")
            return
        
        try:
            with open(text_file, 'r') as f:
                lines = f.readlines()
            
            added_count = 0
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):  # Skip empty lines and comments
                    try:
                        id_value = int(line)
                        if data_type == 'users':
                            if self.add_user(id_value):
                                added_count += 1
                        elif data_type == 'groups':
                            if self.add_group(id_value):
                                added_count += 1
                    except ValueError:
                        print(f"⚠️ Invalid ID format: {line}")
            
            print(f"✅ Imported {added_count} {data_type}")
        except Exception as e:
            print(f"❌ Error importing from file: {e}")
    
    def export_to_text(self, output_file: str, data_type: str = 'users'):
        """Export users/groups to text file"""
        try:
            data_list = self.data[data_type]
            with open(output_file, 'w') as f:
                f.write(f"# Whitelist {data_type.capitalize()}\n")
                f.write(f"# Generated: {datetime.now().isoformat()}\n")
                f.write(f"# Total: {len(data_list)}\n\n")
                
                for item in data_list:
                    f.write(f"{item}\n")
            
            print(f"✅ {data_type.capitalize()} exported to: {output_file}")
        except Exception as e:
            print(f"❌ Error exporting to file: {e}")
    
    def validate_whitelist(self):
        """Validate whitelist structure and data"""
        issues = []
        
        # Check structure
        required_keys = ['users', 'groups', 'enabled', 'metadata']
        for key in required_keys:
            if key not in self.data:
                issues.append(f"Missing key: {key}")
        
        # Check data types
        if not isinstance(self.data.get('users', []), list):
            issues.append("Users should be a list")
        
        if not isinstance(self.data.get('groups', []), list):
            issues.append("Groups should be a list")
        
        if not isinstance(self.data.get('enabled', True), bool):
            issues.append("Enabled should be boolean")
        
        # Check for duplicates
        users = self.data.get('users', [])
        if len(users) != len(set(users)):
            issues.append("Duplicate users found")
        
        groups = self.data.get('groups', [])
        if len(groups) != len(set(groups)):
            issues.append("Duplicate groups found")
        
        # Check ID formats
        for user_id in users:
            if not isinstance(user_id, int) or user_id <= 0:
                issues.append(f"Invalid user ID: {user_id}")
        
        for group_id in groups:
            if not isinstance(group_id, int):
                issues.append(f"Invalid group ID: {group_id}")
        
        if issues:
            print("❌ Validation issues found:")
            for issue in issues:
                print(f"  • {issue}")
            return False
        else:
            print("✅ Whitelist validation passed")
            return True
    
    def clean_whitelist(self):
        """Clean whitelist by removing duplicates and invalid entries"""
        original_users = len(self.data['users'])
        original_groups = len(self.data['groups'])
        
        # Remove duplicates and invalid entries
        self.data['users'] = list(set([
            user_id for user_id in self.data['users'] 
            if isinstance(user_id, int) and user_id > 0
        ]))
        
        self.data['groups'] = list(set([
            group_id for group_id in self.data['groups'] 
            if isinstance(group_id, int)
        ]))
        
        self.save_whitelist()
        
        users_removed = original_users - len(self.data['users'])
        groups_removed = original_groups - len(self.data['groups'])
        
        print(f"✅ Cleaning completed:")
        print(f"  • Users removed: {users_removed}")
        print(f"  • Groups removed: {groups_removed}")

def main():
    parser = argparse.ArgumentParser(description='Whitelist Management Utilities')
    parser.add_argument('--file', '-f', default='whitelist.json', help='Whitelist file path')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Add user command
    add_user_parser = subparsers.add_parser('add-user', help='Add user to whitelist')
    add_user_parser.add_argument('user_id', type=int, help='User ID to add')
    
    # Remove user command
    remove_user_parser = subparsers.add_parser('remove-user', help='Remove user from whitelist')
    remove_user_parser.add_argument('user_id', type=int, help='User ID to remove')
    
    # Add group command
    add_group_parser = subparsers.add_parser('add-group', help='Add group to whitelist')
    add_group_parser.add_argument('group_id', type=int, help='Group ID to add')
    
    # Remove group command
    remove_group_parser = subparsers.add_parser('remove-group', help='Remove group from whitelist')
    remove_group_parser.add_argument('group_id', type=int, help='Group ID to remove')
    
    # Enable/disable commands
    subparsers.add_parser('enable', help='Enable whitelist system')
    subparsers.add_parser('disable', help='Disable whitelist system')
    
    # Status and list commands
    subparsers.add_parser('status', help='Show whitelist status')
    subparsers.add_parser('list', help='List all whitelisted users and groups')
    
    # Backup and restore commands
    backup_parser = subparsers.add_parser('backup', help='Create backup of whitelist')
    backup_parser.add_argument('--output', '-o', help='Backup file name')
    
    restore_parser = subparsers.add_parser('restore', help='Restore whitelist from backup')
    restore_parser.add_argument('backup_file', help='Backup file to restore from')
    
    # Import and export commands
    import_parser = subparsers.add_parser('import', help='Import from text file')
    import_parser.add_argument('file', help='Text file to import from')
    import_parser.add_argument('--type', choices=['users', 'groups'], default='users', help='Type of data to import')
    
    export_parser = subparsers.add_parser('export', help='Export to text file')
    export_parser.add_argument('file', help='Text file to export to')
    export_parser.add_argument('--type', choices=['users', 'groups'], default='users', help='Type of data to export')
    
    # Validation and cleaning commands
    subparsers.add_parser('validate', help='Validate whitelist structure')
    subparsers.add_parser('clean', help='Clean whitelist (remove duplicates and invalid entries)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize manager
    manager = WhitelistManager(args.file)
    
    # Execute command
    if args.command == 'add-user':
        manager.add_user(args.user_id)
    elif args.command == 'remove-user':
        manager.remove_user(args.user_id)
    elif args.command == 'add-group':
        manager.add_group(args.group_id)
    elif args.command == 'remove-group':
        manager.remove_group(args.group_id)
    elif args.command == 'enable':
        manager.enable_whitelist()
    elif args.command == 'disable':
        manager.disable_whitelist()
    elif args.command == 'status':
        manager.show_status()
    elif args.command == 'list':
        manager.list_all()
    elif args.command == 'backup':
        manager.backup_whitelist(args.output)
    elif args.command == 'restore':
        manager.restore_whitelist(args.backup_file)
    elif args.command == 'import':
        manager.import_from_text(args.file, args.type)
    elif args.command == 'export':
        manager.export_to_text(args.file, args.type)
    elif args.command == 'validate':
        manager.validate_whitelist()
    elif args.command == 'clean':
        manager.clean_whitelist()

if __name__ == '__main__':
    main()
