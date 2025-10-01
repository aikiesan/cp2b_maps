"""
CP2B Maps - WCAG Level A Accessibility Core Module
Utilities and helpers for implementing minimum accessibility requirements
"""

import streamlit as st
from pathlib import Path
from typing import Optional


def load_accessibility_css():
    """
    Load accessibility CSS styles into Streamlit app
    WCAG Requirements: 2.4.7 Focus Visible, 2.4.1 Bypass Blocks
    """
    css_file = Path(__file__).parent / "styles.css"

    if css_file.exists():
        with open(css_file, 'r', encoding='utf-8') as f:
            css_content = f.read()
            st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
    else:
        st.warning("⚠️ Arquivo de acessibilidade não encontrado")


def add_skip_link(target_id: str = "main-content"):
    """
    Add skip navigation link - WCAG 2.4.1 Bypass Blocks (Level A)

    Args:
        target_id: ID of the main content area to skip to
    """
    skip_link_html = f"""
    <a href="#{target_id}" class="skip-to-content">
        Pular para o conteúdo principal
    </a>
    <div id="{target_id}" tabindex="-1"></div>
    """
    st.markdown(skip_link_html, unsafe_allow_html=True)


def add_aria_live_region(region_id: str = "announcements", politeness: str = "polite"):
    """
    Create ARIA live region for screen reader announcements
    WCAG Requirement: Dynamic content updates

    Args:
        region_id: Unique ID for the live region
        politeness: 'polite' or 'assertive'
    """
    live_region_html = f"""
    <div id="{region_id}"
         aria-live="{politeness}"
         aria-atomic="true"
         class="sr-only">
    </div>
    """
    st.markdown(live_region_html, unsafe_allow_html=True)


def announce_to_screen_reader(message: str, region_id: str = "announcements"):
    """
    Announce message to screen readers via ARIA live region

    Args:
        message: Message to announce
        region_id: ID of the live region to use
    """
    announcement_script = f"""
    <script>
        (function() {{
            const liveRegion = document.getElementById('{region_id}');
            if (liveRegion) {{
                liveRegion.textContent = '{message}';
                setTimeout(() => {{
                    liveRegion.textContent = '';
                }}, 3000);
            }}
        }})();
    </script>
    """
    st.markdown(announcement_script, unsafe_allow_html=True)


def add_landmark(role: str, label: Optional[str] = None, content: str = ""):
    """
    Add ARIA landmark region - WCAG 1.3.1 Info and Relationships (Level A)

    Args:
        role: ARIA role (navigation, main, complementary, contentinfo)
        label: Optional aria-label for the landmark
        content: HTML content within the landmark
    """
    aria_label = f'aria-label="{label}"' if label else ""
    landmark_html = f"""
    <div role="{role}" {aria_label}>
        {content}
    </div>
    """
    st.markdown(landmark_html, unsafe_allow_html=True)


def accessible_heading(text: str, level: int = 1, id: Optional[str] = None):
    """
    Create accessible heading with proper hierarchy
    WCAG Requirement: 1.3.1 Info and Relationships (Level A)

    Args:
        text: Heading text
        level: Heading level (1-6)
        id: Optional ID for linking
    """
    if level < 1 or level > 6:
        level = 1

    id_attr = f'id="{id}"' if id else ""
    heading_html = f"<h{level} {id_attr}>{text}</h{level}>"
    st.markdown(heading_html, unsafe_allow_html=True)


def accessible_image(
    src: str,
    alt: str,
    caption: Optional[str] = None,
    longdesc: Optional[str] = None
):
    """
    Create accessible image with text alternative
    WCAG Requirement: 1.1.1 Non-text Content (Level A)

    Args:
        src: Image source path or URL
        alt: Alternative text describing the image
        caption: Optional visible caption
        longdesc: Optional long description for complex images
    """
    longdesc_attr = f'longdesc="{longdesc}"' if longdesc else ""

    img_html = f"""
    <figure>
        <img src="{src}" alt="{alt}" {longdesc_attr} />
        {f'<figcaption>{caption}</figcaption>' if caption else ''}
    </figure>
    """
    st.markdown(img_html, unsafe_allow_html=True)


def accessible_link(url: str, text: str, title: Optional[str] = None, new_window: bool = False):
    """
    Create accessible link with proper attributes
    WCAG Requirements: 2.4.4 Link Purpose (Level A)

    Args:
        url: Link destination
        text: Link text (must be descriptive)
        title: Optional title attribute for additional context
        new_window: Whether to open in new window (adds warning)
    """
    title_attr = f'title="{title}"' if title else ""
    target_attr = 'target="_blank" rel="noopener noreferrer"' if new_window else ""
    new_window_indicator = " (abre em nova janela)" if new_window else ""

    link_html = f"""
    <a href="{url}" {title_attr} {target_attr}>
        {text}{new_window_indicator}
    </a>
    """
    st.markdown(link_html, unsafe_allow_html=True)


def error_message(message: str, role: str = "alert"):
    """
    Display accessible error message
    WCAG Requirement: 3.3.1 Error Identification (Level A)

    Args:
        message: Error message text
        role: ARIA role (alert or status)
    """
    error_html = f"""
    <div role="{role}" class="error-message">
        {message}
    </div>
    """
    st.markdown(error_html, unsafe_allow_html=True)


def success_message(message: str):
    """
    Display accessible success message

    Args:
        message: Success message text
    """
    success_html = f"""
    <div role="status" class="success-message">
        {message}
    </div>
    """
    st.markdown(success_html, unsafe_allow_html=True)


def set_page_language(lang: str = "pt-BR"):
    """
    Set page language - WCAG 3.1.1 Language of Page (Level A)

    Args:
        lang: Language code (default: Portuguese Brazilian)
    """
    lang_script = f"""
    <script>
        document.documentElement.lang = "{lang}";
    </script>
    """
    st.markdown(lang_script, unsafe_allow_html=True)


def accessible_form_label(label_text: str, input_id: str, required: bool = False):
    """
    Create accessible form label
    WCAG Requirement: 3.3.2 Labels or Instructions (Level A)

    Args:
        label_text: Label text
        input_id: ID of the associated input element
        required: Whether field is required
    """
    required_class = "required" if required else ""
    label_html = f"""
    <label for="{input_id}" class="{required_class}">
        {label_text}
    </label>
    """
    st.markdown(label_html, unsafe_allow_html=True)


def add_page_title(title: str):
    """
    Set page title for browser tab and screen readers
    WCAG Requirement: 2.4.2 Page Titled (Level A)

    Args:
        title: Page title
    """
    st.set_page_config(page_title=title)


def keyboard_instructions():
    """
    Display keyboard navigation instructions
    Helps users understand how to navigate with keyboard
    """
    instructions_html = """
    <div role="complementary" aria-label="Instruções de navegação por teclado" class="keyboard-instructions">
        <details>
            <summary><strong>⌨️ Instruções de Navegação por Teclado</strong></summary>
            <ul>
                <li><kbd>Tab</kbd> - Avançar para o próximo elemento interativo</li>
                <li><kbd>Shift + Tab</kbd> - Retornar ao elemento anterior</li>
                <li><kbd>Enter</kbd> ou <kbd>Espaço</kbd> - Ativar botões e links</li>
                <li><kbd>Setas</kbd> - Navegar em menus e opções</li>
                <li><kbd>Esc</kbd> - Fechar diálogos e menus</li>
            </ul>
        </details>
    </div>
    """
    st.markdown(instructions_html, unsafe_allow_html=True)


def map_text_alternative(
    map_description: str,
    data_summary: Optional[str] = None,
    show_as_expander: bool = True
):
    """
    Provide text alternative for interactive maps
    WCAG Requirement: 1.1.1 Non-text Content (Level A)

    Args:
        map_description: Description of what the map shows
        data_summary: Optional summary of key data points
        show_as_expander: Show as expandable section (default: True)
    """
    if show_as_expander:
        with st.expander("📊 Descrição do Mapa (Alternativa de Texto)"):
            st.markdown(f"**Descrição:** {map_description}")
            if data_summary:
                st.markdown(f"**Resumo dos Dados:** {data_summary}")
    else:
        st.markdown(f"""
        <div role="complementary" aria-label="Descrição do mapa">
            <p><strong>Descrição:</strong> {map_description}</p>
            {f'<p><strong>Resumo dos Dados:</strong> {data_summary}</p>' if data_summary else ''}
        </div>
        """, unsafe_allow_html=True)


def initialize_accessibility():
    """
    Initialize all core accessibility features
    Call this at the start of your Streamlit app
    """
    # Load CSS
    load_accessibility_css()

    # Set page language
    set_page_language("pt-BR")

    # Add skip link
    add_skip_link()

    # Add ARIA live region for announcements
    add_aria_live_region()

    # Note: keyboard_instructions() removed to prevent z-index issues with header
    # Focus indicators in CSS provide keyboard accessibility
