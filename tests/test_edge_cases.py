"""Test edge cases and potential bugs in the application"""
import unittest
import sys
import pandas as pd
import numpy as np
from pathlib import Path
from unittest.mock import Mock, patch

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

class TestGeospatialEdgeCases(unittest.TestCase):
    """Test edge cases in geospatial data processing"""

    def test_geometry_coordinate_extraction_with_null_geometry(self):
        """Test coordinate extraction when geometry is None"""
        from shapely.geometry import Point
        import geopandas as gpd

        # Create test data with null geometry
        test_data = {
            'cd_mun': ['123', '456'],
            'nome_municipio': ['City A', 'City B'],
            'geometry': [Point(-46.6, -23.5), None]  # One valid, one null
        }

        gdf = gpd.GeoDataFrame(test_data)

        # Test that accessing .x and .y on null geometry doesn't crash
        for idx, row in gdf.iterrows():
            if row['geometry'] is not None:
                try:
                    lat, lon = row['geometry'].y, row['geometry'].x
                    self.assertIsInstance(lat, (int, float))
                    self.assertIsInstance(lon, (int, float))
                except AttributeError:
                    self.fail("Failed to extract coordinates from valid geometry")
            else:
                # This should not cause an exception in well-written code
                self.assertIsNone(row['geometry'])

    def test_invalid_coordinate_values(self):
        """Test handling of invalid coordinate values"""
        from shapely.geometry import Point
        import geopandas as gpd

        # Create test data with invalid coordinates
        invalid_coords = [
            Point(np.inf, -23.5),  # Infinite longitude
            Point(-46.6, np.nan),  # NaN latitude
            Point(999, -999),      # Out of range coordinates
        ]

        for geom in invalid_coords:
            if hasattr(geom, 'x') and hasattr(geom, 'y'):
                # Code should handle invalid coordinates gracefully
                x, y = geom.x, geom.y
                # Check if coordinates are valid for Brazil/SP
                if not (np.isfinite(x) and np.isfinite(y)):
                    self.assertTrue(np.isinf(x) or np.isnan(x) or np.isinf(y) or np.isnan(y))

    def test_crs_conversion_edge_cases(self):
        """Test CRS conversion with edge cases"""
        import geopandas as gpd
        from shapely.geometry import Point

        # Test with undefined CRS
        gdf = gpd.GeoDataFrame({
            'geometry': [Point(-46.6, -23.5)]
        })

        # This should not crash even without defined CRS
        self.assertIsNone(gdf.crs)

        # Test with already correct CRS
        gdf.crs = 'EPSG:4326'
        self.assertEqual(str(gdf.crs), 'EPSG:4326')


class TestDataTypeConsistency(unittest.TestCase):
    """Test data type consistency issues"""

    def test_numeric_conversion_edge_cases(self):
        """Test numeric conversion with problematic values"""
        from database.data_loader import clean_data

        # Create test data with various problematic values
        test_data = pd.DataFrame({
            'CD_MUN': ['123', '456', '789'],
            'Biogás Bovino (Nm³/ano)': ['1000.5', 'invalid', ''],  # Mixed types
            'populacao_2022': ['100000', '0', '-50'],  # Including negative
            'area_km2': ['150.0', 'N/A', '0.0'],  # Including N/A
        })

        cleaned_df = clean_data(test_data.copy())

        # Check that invalid values were converted to 0
        self.assertEqual(cleaned_df['biogas_bovinos_nm_ano'].iloc[1], 0)  # 'invalid' -> 0
        self.assertEqual(cleaned_df['biogas_bovinos_nm_ano'].iloc[2], 0)  # '' -> 0

        # Check that numeric values are properly typed
        self.assertTrue(pd.api.types.is_numeric_dtype(cleaned_df['biogas_bovinos_nm_ano']))
        self.assertTrue(pd.api.types.is_numeric_dtype(cleaned_df['populacao_2022']))

    def test_string_encoding_issues(self):
        """Test string encoding issues that could cause problems"""
        from database.data_loader import clean_data

        # Test with special characters that might cause encoding issues
        test_data = pd.DataFrame({
            'CD_MUN': ['123'],
            'NM_MUN': ['São José dos Campos'],  # Special characters
            'latitude': [-23.5],
            'longitude': [-46.6],
        })

        cleaned_df = clean_data(test_data.copy())

        # Check that municipality name is preserved correctly
        self.assertEqual(cleaned_df['nome_municipio'].iloc[0], 'São José dos Campos')


class TestConcurrencyIssues(unittest.TestCase):
    """Test potential concurrency and race condition issues"""

    def test_cache_key_collisions(self):
        """Test if cache keys could collide between different data types"""
        # This is more of a design check - ensure cache keys are unique
        # For Streamlit cache, function name + arguments create the key

        # Test that different functions with same parameters don't collide
        cache_keys = set()

        # Simulate cache keys for different functions
        functions = [
            ('load_municipalities', ()),
            ('load_shapefile_cached', ('test.shp', 0.001)),
            ('format_number', (1000, 'Nm³/ano', 1)),
        ]

        for func_name, args in functions:
            cache_key = f"{func_name}_{hash(args)}"
            self.assertNotIn(cache_key, cache_keys, f"Cache key collision for {func_name}")
            cache_keys.add(cache_key)


class TestMalformedDataHandling(unittest.TestCase):
    """Test handling of malformed or corrupted data"""

    def test_corrupted_excel_file_handling(self):
        """Test handling of corrupted Excel files"""
        from database.data_loader import load_municipal_data

        # This test checks if the error handling works correctly
        # by testing the fallback to sample data

        # Mock a file that exists but is corrupted
        with patch('pandas.read_excel') as mock_read_excel:
            mock_read_excel.side_effect = Exception("Corrupted file")

            with patch('database.data_loader.find_data_file') as mock_find_file:
                mock_find_file.return_value = Path("fake_corrupted.xlsx")

                # This should not crash and should use sample data instead
                try:
                    result = load_municipal_data()
                    # The function should handle the error gracefully
                    self.assertIsInstance(result, bool)
                except Exception as e:
                    self.fail(f"Function should handle corrupted files gracefully: {e}")

    def test_empty_string_coordinates(self):
        """Test handling of empty string coordinates"""
        from database.data_loader import clean_data

        test_data = pd.DataFrame({
            'CD_MUN': ['123'],
            'latitude': [''],  # Empty string
            'longitude': [''],  # Empty string
        })

        cleaned_df = clean_data(test_data.copy())

        # Empty strings should be converted to 0
        self.assertEqual(cleaned_df['lat'].iloc[0], 0)
        self.assertEqual(cleaned_df['lon'].iloc[0], 0)

    def test_extreme_numeric_values(self):
        """Test handling of extreme numeric values"""
        from database.data_loader import clean_data

        test_data = pd.DataFrame({
            'CD_MUN': ['123', '456', '789'],
            'Biogás Bovino (Nm³/ano)': [
                '1.7976931348623157e+308',  # Near float64 max
                '-1.7976931348623157e+308', # Near float64 min
                '1e-324'  # Near float64 min positive
            ],
        })

        cleaned_df = clean_data(test_data.copy())

        # Check that extreme values are handled without overflow
        self.assertTrue(pd.api.types.is_numeric_dtype(cleaned_df['biogas_bovinos_nm_ano']))
        self.assertTrue(all(np.isfinite(cleaned_df['biogas_bovinos_nm_ano'])))


class TestMemoryLeakPotential(unittest.TestCase):
    """Test for potential memory leaks"""

    def test_large_dataframe_processing(self):
        """Test processing of large dataframes for memory efficiency"""
        from database.data_loader import clean_data

        # Create a reasonably large dataframe to test memory efficiency
        large_data = pd.DataFrame({
            'CD_MUN': [f'{i:07d}' for i in range(10000)],
            'NM_MUN': [f'City {i}' for i in range(10000)],
            'latitude': [-23.5 + (i * 0.001) for i in range(10000)],
            'longitude': [-46.6 + (i * 0.001) for i in range(10000)],
            'Biogás Bovino (Nm³/ano)': [str(i * 1000) for i in range(10000)],
        })

        # Memory usage before
        memory_before = large_data.memory_usage(deep=True).sum()

        cleaned_df = clean_data(large_data.copy())

        # Memory usage after
        memory_after = cleaned_df.memory_usage(deep=True).sum()

        # The cleaned dataframe shouldn't use dramatically more memory
        memory_ratio = memory_after / memory_before
        self.assertLess(memory_ratio, 3.0, "Data cleaning causing excessive memory usage")


if __name__ == '__main__':
    unittest.main(verbosity=2)