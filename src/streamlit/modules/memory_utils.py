"""
Memory management utilities
"""
import streamlit as st


def get_memory_usage():
    """Get current memory usage in MB"""
    try:
        import psutil
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
    except:
        return 0


def cleanup_memory():
    """Clean up memory-intensive session state variables"""
    memory_intensive_keys = [
        'raster_analysis_results',
        'vector_analysis_results', 
        'cached_maps',
        'large_datasets'
    ]
    
    # Monitor memory before cleanup
    memory_before = get_memory_usage()
    
    for key in memory_intensive_keys:
        if key in st.session_state:
            del st.session_state[key]
    
    # Clear matplotlib figures to free memory
    try:
        import matplotlib.pyplot as plt
        plt.close('all')
    except:
        pass
    
    # Force garbage collection
    import gc
    gc.collect()
    
    memory_after = get_memory_usage()
    if memory_before > 0 and memory_after > 0:
        memory_saved = memory_before - memory_after
        if memory_saved > 10:  # Only log if significant memory was freed
            st.caption(f"🧹 Freed {memory_saved:.1f}MB of memory")