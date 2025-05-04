import os
import logging
import sys
import traceback
import argparse

# Configure logging to output to console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Set up the nutrition database')
    parser.add_argument('--test', action='store_true', help='Import a limited number of foods for testing')
    parser.add_argument('--max-foods', type=int, default=100, help='Maximum number of foods to import when testing')
    parser.add_argument('--batch-size', type=int, default=1000, help='Batch size for database transactions')
    parser.add_argument('--clear', action='store_true', help='Clear existing database data')
    return parser.parse_args()

def main():
    """Set up the SQLite database and import data"""
    args = parse_args()
    
    try:
        logger.info("Starting database setup...")
        
        # Attempt to import our modules
        try:
            from database_schema import create_database
            from data_importer import import_data
            logger.info("Successfully imported database modules")
        except ImportError as e:
            logger.error(f"Failed to import required modules: {e}")
            logger.error(traceback.format_exc())
            return
        
        # Create the database schema
        logger.info("Creating database schema...")
        try:
            create_database()
            logger.info("Database schema created successfully")
        except Exception as e:
            logger.error(f"Error creating database schema: {e}")
            logger.error(traceback.format_exc())
            return
        
        # Import data
        logger.info("Importing data from JSON file...")
        try:
            if args.test:
                logger.info(f"Running in test mode with max {args.max_foods} foods")
                success = import_data(
                    clear_existing=args.clear, 
                    batch_size=args.batch_size, 
                    max_foods=args.max_foods
                )
            else:
                success = import_data(
                    clear_existing=args.clear, 
                    batch_size=args.batch_size
                )
                
            if success:
                logger.info("Data imported successfully!")
            else:
                logger.error("Failed to import data")
        except Exception as e:
            logger.error(f"Error during data import: {e}")
            logger.error(traceback.format_exc())
            return
        
        logger.info("Database setup completed!")
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main() 