#!/usr/bin/env python3
"""
Custom pre-commit hook to check for sensitive patterns in code.
Scans for API keys, passwords, tokens, and other secrets.
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple

# Patterns to detect sensitive information
SENSITIVE_PATTERNS = {
    "API_KEY": re.compile(
        r'(?i)(api[_-]?key|apikey)\s*[=:]\s*["\']?[a-zA-Z0-9_\-]{16,}["\']?'
    ),
    "SECRET_KEY": re.compile(
        r'(?i)(secret[_-]?key|secret)\s*[=:]\s*["\']?[a-zA-Z0-9_\-]{16,}["\']?'
    ),
    "PASSWORD": re.compile(
        r'(?i)(password|passwd|pwd)\s*[=:]\s*["\'][^"\']{4,}["\']'
    ),
    "PRIVATE_KEY": re.compile(
        r'(?i)(private[_-]?key|privatekey)\s*[=:]\s*["\']?[a-zA-Z0-9+/=]{20,}["\']?'
    ),
    "AWS_KEY": re.compile(
        r'AKIA[0-9A-Z]{16}'
    ),
    "GITHUB_TOKEN": re.compile(
        r'gh[pousr]_[A-Za-z0-9_]{36,}'
    ),
    "OPENAI_KEY": re.compile(
        r'sk-[a-zA-Z0-9]{20,}'
    ),
    "JWT_TOKEN": re.compile(
        r'eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*'
    ),
    "DATABASE_URL": re.compile(
        r'(?i)(postgresql|mysql|mongodb)://[^:]+:[^@]+@'
    ),
}

# Files to exclude from scanning
EXCLUDED_FILES = {
    '.secrets.baseline',
    'uv.lock',
    'poetry.lock',
    'package-lock.json',
    'yarn.lock',
    'Cargo.lock',
    '.gitignore',
    '.pre-commit-config.yaml',
}

# File extensions to scan
SCAN_EXTENSIONS = {'.py', '.env', '.yaml', '.yml', '.json', '.toml', '.txt', '.md'}


def should_scan_file(filepath: str) -> bool:
    """Check if file should be scanned."""
    path = Path(filepath)
    
    # Skip excluded files
    if path.name in EXCLUDED_FILES:
        return False
    
    # Check extension
    if path.suffix not in SCAN_EXTENSIONS:
        return False
    
    return True


def scan_file(filepath: str) -> List[Tuple[str, int, str]]:
    """
    Scan a file for sensitive patterns.
    
    Returns:
        List of (pattern_name, line_number, matched_text) tuples
    """
    findings = []
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except Exception as e:
        print(f"Warning: Could not read {filepath}: {e}", file=sys.stderr)
        return findings
    
    lines = content.split('\n')
    
    for line_num, line in enumerate(lines, start=1):
        # Skip comments explaining the pattern (meta-comments)
        if line.strip().startswith('#') and 'password' in line.lower():
            continue
        
        for pattern_name, pattern in SENSITIVE_PATTERNS.items():
            matches = pattern.findall(line)
            for match in matches:
                # Skip placeholder/example values
                if any(placeholder in str(match).lower() for placeholder in [
                    'example', 'placeholder', 'your_', 'xxx', '***', 
                    'changeme', 'password123', 'admin', 'test'
                ]):
                    continue
                
                # Truncate match for display
                match_str = str(match)
                if len(match_str) > 50:
                    match_str = match_str[:50] + '...'
                
                findings.append((pattern_name, line_num, match_str))
    
    return findings


def main():
    """Main entry point."""
    files = sys.argv[1:] if len(sys.argv) > 1 else []
    
    if not files:
        print("No files to check", file=sys.stderr)
        sys.exit(0)
    
    all_findings = []
    
    for filepath in files:
        if not should_scan_file(filepath):
            continue
        
        findings = scan_file(filepath)
        for pattern_name, line_num, match in findings:
            all_findings.append((filepath, pattern_name, line_num, match))
    
    if all_findings:
        print("\n🔴 Potential sensitive information detected:\n", file=sys.stderr)
        
        for filepath, pattern_name, line_num, match in all_findings:
            print(
                f"  ❌ {filepath}:{line_num}",
                file=sys.stderr
            )
            print(
                f"     Pattern: {pattern_name}",
                file=sys.stderr
            )
            print(
                f"     Match: {match[:80]}",
                file=sys.stderr
            )
            print(file=sys.stderr)
        
        print(
            "To fix:\n"
            "  1. Move secrets to .env file (and ensure .env is in .gitignore)\n"
            "  2. Use environment variables: os.environ.get('SECRET_KEY')\n"
            "  3. If this is a false positive, update the check script\n",
            file=sys.stderr
        )
        
        sys.exit(1)
    
    print("✅ No sensitive information detected")
    sys.exit(0)


if __name__ == '__main__':
    main()
