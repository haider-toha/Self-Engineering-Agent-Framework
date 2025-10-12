"""
Setup Script - Initialize the Self-Engineering Agent Framework
"""

import os
import sys
import subprocess


def check_python_version():
    """Ensure Python 3.10+"""
    if sys.version_info < (3, 10):
        print("❌ Python 3.10 or higher is required")
        print(f"   Current version: {sys.version}")
        return False
    print(f"✓ Python version: {sys.version.split()[0]}")
    return True


def check_docker():
    """Check if Docker is installed and running"""
    try:
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print(f"✓ Docker installed: {result.stdout.strip()}")
            
            # Check if Docker daemon is running
            result = subprocess.run(
                ["docker", "ps"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print("✓ Docker daemon is running")
                return True
            else:
                print("❌ Docker daemon is not running. Please start Docker Desktop.")
                return False
        else:
            print("❌ Docker is not installed")
            return False
    except FileNotFoundError:
        print("❌ Docker is not installed")
        return False
    except Exception as e:
        print(f"❌ Error checking Docker: {e}")
        return False


def install_dependencies():
    """Install Python dependencies"""
    print("\n📦 Installing Python dependencies...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
            check=True
        )
        print("✓ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        return False


def check_env_file():
    """Check if .env file exists"""
    if os.path.exists(".env"):
        print("✓ .env file exists")
        return True
    else:
        print("⚠ .env file not found")
        print("  Please create a .env file with your configuration:")
        print("  Copy .env.example to .env and add your OPENAI_API_KEY")
        return False


def build_docker_image():
    """Build the sandbox Docker image"""
    print("\n🐳 Building Docker sandbox image...")
    try:
        from src.sandbox import SecureSandbox
        sandbox = SecureSandbox()
        if sandbox.build_image():
            print("✓ Docker image built successfully")
            return True
        else:
            print("❌ Failed to build Docker image")
            return False
    except Exception as e:
        print(f"❌ Error building Docker image: {e}")
        return False


def seed_initial_tools():
    """Seed the registry with initial tools"""
    print("\n🌱 Seeding initial tools...")
    try:
        import seed_tools
        seed_tools.seed_tools()
        return True
    except Exception as e:
        print(f"❌ Error seeding tools: {e}")
        return False


def main():
    """Main setup function"""
    print("=" * 60)
    print("Self-Engineering Agent Framework - Setup")
    print("=" * 60)
    print()
    
    # Track setup success
    all_checks_passed = True
    
    # Check Python version
    if not check_python_version():
        all_checks_passed = False
        return
    
    # Check Docker
    if not check_docker():
        all_checks_passed = False
        return
    
    # Check .env file
    env_exists = check_env_file()
    if not env_exists:
        all_checks_passed = False
    
    # Ask user if they want to continue
    print("\n" + "=" * 60)
    response = input("\nProceed with installation? (y/n): ").lower().strip()
    
    if response != 'y':
        print("Setup cancelled.")
        return
    
    # Install dependencies
    if not install_dependencies():
        all_checks_passed = False
        return
    
    # Build Docker image
    if not build_docker_image():
        all_checks_passed = False
        return
    
    # Seed tools
    if not seed_initial_tools():
        all_checks_passed = False
    
    # Final summary
    print("\n" + "=" * 60)
    if all_checks_passed and env_exists:
        print("✅ Setup completed successfully!")
        print("\nTo start the agent:")
        print("  python web/app.py")
        print("\nThen open http://localhost:5000 in your browser")
    else:
        print("⚠ Setup completed with warnings")
        print("\nPlease address any issues above before starting the agent")
    print("=" * 60)


if __name__ == "__main__":
    main()

