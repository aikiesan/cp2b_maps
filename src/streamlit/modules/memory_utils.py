"""
Enhanced Memory Management Utilities for CP2B Maps
Provides efficient memory monitoring, cleanup, and session state optimization
"""
import streamlit as st
import gc
import logging
from typing import List, Dict, Any, Optional
from functools import wraps

logger = logging.getLogger(__name__)


def get_memory_usage() -> float:
    """Get current memory usage in MB"""
    try:
        import psutil
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
    except ImportError:
        logger.warning("psutil not available, memory monitoring disabled")
        return 0
    except Exception as e:
        logger.error(f"Error getting memory usage: {e}")
        return 0


def get_detailed_memory_info() -> Dict[str, Any]:
    """Get detailed memory information"""
    try:
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()
        return {
            'rss_mb': memory_info.rss / 1024 / 1024,
            'vms_mb': memory_info.vms / 1024 / 1024,
            'percent': process.memory_percent(),
            'available_mb': psutil.virtual_memory().available / 1024 / 1024
        }
    except Exception as e:
        logger.error(f"Error getting detailed memory info: {e}")
        return {'rss_mb': 0, 'vms_mb': 0, 'percent': 0, 'available_mb': 0}


def cleanup_memory(aggressive: bool = False) -> float:
    """
    Clean up memory-intensive session state variables

    Args:
        aggressive: If True, performs more thorough cleanup

    Returns:
        float: Amount of memory freed in MB
    """
    memory_before = get_memory_usage()

    # Standard cleanup keys
    memory_intensive_keys = [
        'raster_analysis_results',
        'vector_analysis_results',
        'cached_maps',
        'large_datasets',
        'proximity_results',
        'map_data_cache',
        'folium_maps',
        'analysis_cache'
    ]

    # Additional aggressive cleanup keys
    if aggressive:
        memory_intensive_keys.extend([
            'municipality_data',
            'shapefile_cache',
            'plotly_figures',
            'temp_data'
        ])

    cleaned_keys = []
    for key in memory_intensive_keys:
        if key in st.session_state:
            del st.session_state[key]
            cleaned_keys.append(key)

    # Clear matplotlib figures
    try:
        import matplotlib.pyplot as plt
        plt.close('all')
    except ImportError:
        pass
    except Exception as e:
        logger.error(f"Error closing matplotlib figures: {e}")

    # Force garbage collection
    gc.collect()

    memory_after = get_memory_usage()
    memory_freed = max(0, memory_before - memory_after)

    if cleaned_keys:
        logger.info(f"Cleaned up session state keys: {cleaned_keys}")

    if memory_freed > 5:  # Only show if significant memory was freed
        st.caption(f"🧹 Freed {memory_freed:.1f}MB of memory")

    return memory_freed


def monitor_memory_usage(threshold_mb: float = 500) -> bool:
    """
    Monitor memory usage and trigger cleanup if needed

    Args:
        threshold_mb: Memory threshold in MB to trigger cleanup

    Returns:
        bool: True if cleanup was triggered
    """
    current_memory = get_memory_usage()

    if current_memory > threshold_mb:
        logger.warning(f"High memory usage detected: {current_memory:.1f}MB")
        freed = cleanup_memory(aggressive=True)
        logger.info(f"Emergency cleanup freed {freed:.1f}MB")
        return True

    return False


def optimize_session_state() -> None:
    """Optimize session state by removing old or unnecessary data"""
    keys_to_remove = []

    for key in st.session_state:
        try:
            # Remove empty containers
            if hasattr(st.session_state[key], '__len__') and len(st.session_state[key]) == 0:
                keys_to_remove.append(key)

            # Remove None values
            elif st.session_state[key] is None:
                keys_to_remove.append(key)

        except Exception:
            continue

    for key in keys_to_remove:
        del st.session_state[key]

    if keys_to_remove:
        logger.info(f"Optimized session state: removed {len(keys_to_remove)} empty/None keys")


def memory_efficient(func):
    """
    Decorator to monitor memory usage around function calls
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        memory_before = get_memory_usage()

        try:
            result = func(*args, **kwargs)
            return result
        finally:
            memory_after = get_memory_usage()
            memory_diff = memory_after - memory_before

            if memory_diff > 50:  # Log if function used more than 50MB
                logger.warning(f"Function {func.__name__} used {memory_diff:.1f}MB of memory")

                # Trigger cleanup if memory usage is very high
                if memory_after > 800:
                    cleanup_memory()

    return wrapper


def get_session_state_size() -> Dict[str, float]:
    """Get approximate size of session state variables in MB"""
    import sys

    sizes = {}
    for key, value in st.session_state.items():
        try:
            size_bytes = sys.getsizeof(value)
            if hasattr(value, '__dict__'):
                size_bytes += sum(sys.getsizeof(v) for v in value.__dict__.values())
            sizes[key] = size_bytes / 1024 / 1024  # Convert to MB
        except Exception:
            sizes[key] = 0

    return sizes


def display_memory_stats() -> None:
    """Display memory statistics in sidebar or expander"""
    memory_info = get_detailed_memory_info()

    with st.expander("🔍 Memory Statistics", expanded=False):
        col1, col2 = st.columns(2)

        with col1:
            st.metric("Memory Usage", f"{memory_info['rss_mb']:.1f}MB")
            st.metric("Memory %", f"{memory_info['percent']:.1f}%")

        with col2:
            st.metric("Available", f"{memory_info['available_mb']:.1f}MB")
            st.metric("Virtual", f"{memory_info['vms_mb']:.1f}MB")

        # Session state size breakdown
        session_sizes = get_session_state_size()
        if session_sizes:
            st.subheader("Session State Size")
            large_items = {k: v for k, v in session_sizes.items() if v > 1}  # > 1MB
            if large_items:
                for key, size in sorted(large_items.items(), key=lambda x: x[1], reverse=True):
                    st.text(f"{key}: {size:.1f}MB")

        # Cleanup button
        if st.button("🧹 Clean Memory", help="Force memory cleanup"):
            freed = cleanup_memory(aggressive=True)
            st.success(f"Freed {freed:.1f}MB of memory")
            st.experimental_rerun()