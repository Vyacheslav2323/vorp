"""
Toxic Green Theme Configuration

This file contains the color definitions and theme settings for the Toxic Green theme.
Import this file in your Django views to pass theme variables to templates if needed.
"""

# Main color scheme
THEME_COLORS = {
    'toxic_green': '#39FF14',
    'toxic_green_dark': '#32CD32',
    'toxic_green_light': '#7FFF00',
    'toxic_green_accent': '#00FF00',
    'light_bg': '#FFFFFF',
    'light_card_bg': '#F8F8F8',
    'text_color': '#333333',
}

# Theme settings
THEME_SETTINGS = {
    'name': 'Toxic Green Light',
    'description': 'A bright cyberpunk-inspired theme with toxic green accents on a white background.',
    'author': 'Django Team',
    'version': '1.1',
}

# Animation settings
ANIMATIONS = {
    'glow_duration': '2s',
    'pulse_duration': '6s',
}

def get_theme_context():
    """
    Return a dictionary with all theme variables to be used in templates.
    
    Usage in views:
    from theme_config import get_theme_context
    
    def my_view(request):
        context = get_theme_context()
        # Add more context variables as needed
        return render(request, 'my_template.html', context)
    """
    return {
        'theme_colors': THEME_COLORS,
        'theme_settings': THEME_SETTINGS,
        'animations': ANIMATIONS,
    } 