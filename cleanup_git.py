#!/usr/bin/env python3
"""
Remove tracked files from git cache that should be ignored.
This keeps your local files but removes them from git tracking.
"""

import subprocess
import sys
import os


def run_command(cmd, description):
    """Run a git command and show results."""
    print(f"\n{description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        if result.returncode != 0 and result.stderr:
            if "did not match any files" not in result.stderr:
                print(f"  Note: {result.stderr.strip()}")
        return result.returncode == 0
    except Exception as e:
        print(f"  Error: {e}")
        return False


def main():
    print("=" * 70)
    print("REMOVE TRACKED FILES FROM GIT CACHE")
    print("=" * 70)
    print()
    print("This will remove files from git tracking but keep them locally.")
    print()
    
    if not os.path.exists(".git"):
        print("✗ Not a git repository!")
        sys.exit(1)
    
    # Check if .gitignore exists
    if not os.path.exists(".gitignore"):
        print("⚠ .gitignore not found. Creating one...")
        with open(".gitignore", "w") as f:
            f.write("# Python cache\n__pycache__/\n*.pyc\n*.pyo\n\n")
            f.write("# Virtual environment\nvenv/\nenv/\n.venv\n\n")
            f.write("# Environment variables\n.env\n.env.local\n\n")
            f.write("# IDE\n.vscode/\n.idea/\n\n")
            f.write("# OS\n.DS_Store\n")
        print("✓ Created .gitignore")
    
    # Remove venv if tracked
    if os.path.exists("venv"):
        run_command("git rm -r --cached venv/ 2>/dev/null", "Removing venv/ from git")
    
    # Remove .env if tracked
    if os.path.exists(".env"):
        run_command("git rm --cached .env 2>/dev/null", "Removing .env from git")
    
    # Remove all __pycache__ directories
    run_command(
        'find . -type d -name __pycache__ -exec git rm -r --cached {} + 2>/dev/null',
        "Removing __pycache__/ directories from git"
    )
    
    # Remove .pyc files
    run_command(
        'find . -name "*.pyc" -exec git rm --cached {} + 2>/dev/null',
        "Removing .pyc files from git"
    )
    
    # Remove .pyo files
    run_command(
        'find . -name "*.pyo" -exec git rm --cached {} + 2>/dev/null',
        "Removing .pyo files from git"
    )
    
    # Remove egg-info if tracked
    run_command(
        'find . -type d -name "*.egg-info" -exec git rm -r --cached {} + 2>/dev/null',
        "Removing *.egg-info/ directories from git"
    )
    
    print()
    print("=" * 70)
    print("NEXT STEPS")
    print("=" * 70)
    print()
    print("1. Review changes:")
    print("   git status")
    print()
    print("2. Add .gitignore:")
    print("   git add .gitignore")
    print()
    print("3. Commit changes:")
    print("   git commit -m 'Add .gitignore and remove tracked files'")
    print()
    print("✓ Done! Files are now ignored by git.")


if __name__ == "__main__":
    main()

