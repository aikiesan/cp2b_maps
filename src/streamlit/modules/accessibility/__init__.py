"""
CP2B Maps - Accessibility Module
WCAG 2.1 Level A compliance utilities
"""

from .core import (
    initialize_accessibility,
    load_accessibility_css,
    add_skip_link,
    accessible_heading,
    accessible_image,
    accessible_link,
    error_message,
    success_message,
    set_page_language,
    accessible_form_label,
    keyboard_instructions,
    map_text_alternative,
    announce_to_screen_reader,
    add_landmark,
    add_aria_live_region
)

__all__ = [
    "initialize_accessibility",
    "load_accessibility_css",
    "add_skip_link",
    "accessible_heading",
    "accessible_image",
    "accessible_link",
    "error_message",
    "success_message",
    "set_page_language",
    "accessible_form_label",
    "keyboard_instructions",
    "map_text_alternative",
    "announce_to_screen_reader",
    "add_landmark",
    "add_aria_live_region"
]
