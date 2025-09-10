#!/usr/bin/env python3
"""
Setup script for CP2B Maps - Clean and Simple
Run this to initialize the database and load sample data
"""

import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def main():
    """Run complete setup"""
    logger.info("🌱 CP2B Maps Setup Starting...")
    logger.info("=" * 50)
    
    try:
        # Import after adding src to path
        from database.migrations import main as run_migrations
        from database.data_loader import main as load_data
        
        # Step 1: Create database
        logger.info("Step 1/2: Creating database and tables...")
        run_migrations()
        
        # Step 2: Load data
        logger.info("Step 2/2: Loading municipal data...")
        load_data()
        
        # Success
        logger.info("=" * 50)
        logger.info("✅ Setup completed successfully!")
        logger.info("")
        logger.info("🚀 Ready to run the application:")
        logger.info("   streamlit run src/streamlit/app.py")
        logger.info("")
        
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        logger.error("Make sure you're in the CP2B_Maps directory")
        sys.exit(1)
        
    except Exception as e:
        logger.error(f"❌ Setup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()