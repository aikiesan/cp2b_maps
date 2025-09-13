#!/usr/bin/env python3
"""
Test script for municipality loader functionality
"""

import sys
from pathlib import Path

# Add the src directory to Python path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

try:
    from streamlit.modules.municipality_loader import get_municipality_geometries, get_municipality_info
    print("Successfully imported municipality loader")
    
    # Test with a few São Paulo municipalities
    test_municipalities = [
        "São Paulo",
        "Campinas", 
        "Santos",
        "Ribeirão Preto"
    ]
    
    print(f"\nTesting geometry loading for {len(test_municipalities)} municipalities...")
    
    geometries = get_municipality_geometries(test_municipalities)
    print(f"Loaded {len(geometries)} geometries")
    
    for i, (mun, geom) in enumerate(zip(test_municipalities, geometries)):
        if geom is not None:
            print(f"  {i+1}. {mun}: Geometry loaded (type: {type(geom).__name__})")
            
            # Test info loading
            info = get_municipality_info(mun)
            if info:
                print(f"     - Area: {info.get('area_km2', 'N/A')} km²")
                print(f"     - Region: {info.get('regiao_imediata', 'N/A')}")
                centroid = info.get('centroid')
                if centroid:
                    print(f"     - Centroid: [{centroid[0]:.4f}, {centroid[1]:.4f}]")
        else:
            print(f"  {i+1}. {mun}: No geometry found")
    
    print("\nTest completed successfully!")
    
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure the municipality loader module was created properly")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()