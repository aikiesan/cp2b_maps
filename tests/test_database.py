"""Unit tests for database functionality"""
import unittest
import tempfile
import sqlite3
import pandas as pd
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from database.migrations import create_database, get_database_path
from database.data_loader import (
    find_data_file, clean_data, create_sample_data,
    load_data_to_database, load_municipal_data
)


class TestDatabaseMigrations(unittest.TestCase):
    """Test database creation and migrations"""

    def setUp(self):
        """Set up test environment"""
        self.test_db_path = Path(tempfile.mktemp(suffix='.db'))

    def tearDown(self):
        """Clean up test environment"""
        if self.test_db_path.exists():
            self.test_db_path.unlink()

    def test_database_creation(self):
        """Test database and table creation"""
        # Mock get_database_path to use test database
        import database.migrations as migrations
        original_get_path = migrations.get_database_path
        migrations.get_database_path = lambda: self.test_db_path

        try:
            # Create database
            result = create_database()
            self.assertTrue(result)
            self.assertTrue(self.test_db_path.exists())

            # Verify table structure
            with sqlite3.connect(self.test_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(municipalities)")
                columns = [row[1] for row in cursor.fetchall()]

                expected_columns = [
                    'id', 'OBJECTID', 'cd_mun', 'nome_municipio', 'lat', 'lon',
                    'area_km2', 'populacao_2022', 'total_final_nm_ano',
                    'total_agricola_nm_ano', 'total_pecuaria_nm_ano'
                ]

                for col in expected_columns:
                    self.assertIn(col, columns, f"Column {col} not found in database")

        finally:
            # Restore original function
            migrations.get_database_path = original_get_path


class TestDataLoader(unittest.TestCase):
    """Test data loading functionality"""

    def test_find_data_file(self):
        """Test data file discovery"""
        # This test may return None if no files exist, which is acceptable
        result = find_data_file()
        if result is not None:
            self.assertTrue(isinstance(result, Path))

    def test_create_sample_data(self):
        """Test sample data creation"""
        df = create_sample_data()

        self.assertFalse(df.empty)
        self.assertGreater(len(df), 0)

        # Check required columns
        required_cols = ['cd_mun', 'nome_municipio', 'lat', 'lon']
        for col in required_cols:
            self.assertIn(col, df.columns)

        # Check data types
        self.assertTrue(pd.api.types.is_string_dtype(df['cd_mun']))
        self.assertTrue(pd.api.types.is_string_dtype(df['nome_municipio']))
        self.assertTrue(pd.api.types.is_numeric_dtype(df['lat']))
        self.assertTrue(pd.api.types.is_numeric_dtype(df['lon']))

    def test_clean_data(self):
        """Test data cleaning functionality"""
        # Create test data with various issues
        test_data = pd.DataFrame({
            'CD_MUN': ['123', '456', '789'],
            'NM_MUN': ['City A', 'City B', 'City C'],
            'latitude': [-23.5, -22.9, -24.1],
            'longitude': [-46.6, -47.1, -46.8],
            'area': [100, 200, 150],
            'Biogás Bovino (Nm³/ano)': ['1000', '2000', 'invalid']
        })

        cleaned_df = clean_data(test_data.copy())

        # Check column mapping worked
        self.assertIn('cd_mun', cleaned_df.columns)
        self.assertIn('nome_municipio', cleaned_df.columns)
        self.assertIn('lat', cleaned_df.columns)
        self.assertIn('lon', cleaned_df.columns)
        self.assertIn('area_km2', cleaned_df.columns)
        self.assertIn('biogas_bovinos_nm_ano', cleaned_df.columns)

        # Check data type conversions
        self.assertTrue(pd.api.types.is_string_dtype(cleaned_df['cd_mun']))
        self.assertTrue(pd.api.types.is_numeric_dtype(cleaned_df['lat']))
        self.assertTrue(pd.api.types.is_numeric_dtype(cleaned_df['lon']))

        # Check invalid numeric values were converted to 0
        self.assertEqual(cleaned_df['biogas_bovinos_nm_ano'].iloc[2], 0)

    def test_load_data_to_database_error_handling(self):
        """Test error handling in database loading"""
        # Test with None dataframe
        result = load_data_to_database(None)
        self.assertFalse(result)

        # Test with empty dataframe
        empty_df = pd.DataFrame()
        result = load_data_to_database(empty_df)
        self.assertFalse(result)


class TestDataIntegrity(unittest.TestCase):
    """Test data integrity and validation"""

    def test_sample_data_integrity(self):
        """Test sample data meets business requirements"""
        df = create_sample_data()

        # Check all required biogas columns are present
        biogas_columns = [col for col in df.columns if 'biogas_' in col]
        self.assertGreater(len(biogas_columns), 0)

        # Check all values are non-negative (except coordinates which can be negative)
        numeric_columns = df.select_dtypes(include=[int, float]).columns
        for col in numeric_columns:
            if col not in ['lat', 'lon']:  # Coordinates can be negative
                self.assertTrue(all(df[col] >= 0), f"Negative values found in {col}")

        # Check municipality codes are valid format
        for cd_mun in df['cd_mun']:
            self.assertEqual(len(cd_mun), 7, f"Invalid municipality code: {cd_mun}")
            self.assertTrue(cd_mun.isdigit(), f"Non-numeric municipality code: {cd_mun}")

        # Check coordinates are in valid range for São Paulo
        self.assertTrue(all(df['lat'] >= -26), "Latitude too far south")
        self.assertTrue(all(df['lat'] <= -19), "Latitude too far north")
        self.assertTrue(all(df['lon'] >= -54), "Longitude too far west")
        self.assertTrue(all(df['lon'] <= -44), "Longitude too far east")


if __name__ == '__main__':
    unittest.main()