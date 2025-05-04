# SQLite Database for Nutrition Data

This implementation replaces the JSON-based nutrition data storage with a SQLite database for better performance and query capabilities.

## Files Added

1. `database_schema.py` - Defines the SQLite database schema
2. `data_importer.py` - Imports data from the JSON file into the SQLite database
3. `services/db_nutrition_service.py` - Database-powered version of the nutrition service
4. `setup_db.py` - Script to set up the database and import data

## Database Schema

The database consists of three main tables:

- **foods** - Main table for food items with basic information
- **nutrients** - Nutrient values for each food
- **allergens** - Allergen information for each food

## Setup Instructions

1. Ensure your JSON data file exists at: `back/api/data/FoodData_Central_foundation_food_json_2025-04-24.json`
2. Run the setup script to create the database and import data:

```bash
cd back/api
python setup_db.py
```

3. The database will be created at: `back/api/data/nutrition.db`

## Switching Between Implementations

The router has been updated to use the database-powered service. If you need to switch back to the JSON-based service, update the import in `routers/nutrition.py`:

```python
# For database implementation:
from services.db_nutrition_service import get_nutrition_data_by_name, get_nutrition_data_by_barcode

# For JSON implementation:
from services.nutrition_service import get_nutrition_data_by_name, get_nutrition_data_by_barcode
```

## Benefits

- Faster queries, especially for large datasets
- Better memory usage (no need to load the entire dataset into memory)
- More robust error handling
- Support for complex queries
- Better scalability for future features

## Performance Considerations

- The database file can be quite large after importing a complete dataset
- For extremely large datasets, consider using an external database like PostgreSQL
- Initial data import may take some time, but subsequent queries will be much faster 