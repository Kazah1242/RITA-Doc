from PIL import Image, ImageDraw, ImageFont
import os
import math

def create_modern_icon():
    size = (512, 512)
    image = Image.new('RGBA', size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    # Create modern gradient background with rounded corners
    center_x, center_y = size[0] // 2, size[1] // 2
    
    # Draw multiple circles for gradient effect
    colors = [
        (66, 135, 245),   # Blue
        (109, 66, 245),   # Purple  
        (245, 66, 200),   # Pink
        (66, 245, 235),   # Cyan
    ]
    
    # Draw gradient circles
    for i in range(20):
        radius = 256 - i * 12
        alpha = int(255 * (1 - i / 20))
        color_idx = i % len(colors)
        color = colors[color_idx] + (alpha,)
        
        draw.ellipse([center_x - radius, center_y - radius, 
                     center_x + radius, center_y + radius], 
                    fill=color)
    
    # Draw main rounded rectangle background
    draw.rounded_rectangle([30, 30, 482, 482], radius=80, fill=(25, 25, 35, 240))
    
    # Add inner glow effect
    for i in range(5):
        offset = i * 2
        alpha = 50 - i * 10
        draw.rounded_rectangle([30 + offset, 30 + offset, 482 - offset, 482 - offset], 
                              radius=80 - offset, outline=(100, 150, 255, alpha), width=2)
    
    # Try to load a modern font, fallback to default
    font = None
    font_paths = [
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
        '/System/Library/Fonts/Helvetica.ttc',  # macOS
        '/Windows/Fonts/arialbd.ttf',  # Windows
    ]
    for path in font_paths:
        if os.path.exists(path):
            font = ImageFont.truetype(path, 320)
            break
    if not font: 
        font = ImageFont.load_default()
    
    # Draw 'R' with gradient effect
    # Shadow
    draw.text((center_x + 4, center_y + 4), 'R', fill=(0, 0, 0, 100), font=font, anchor='mm')
    
    # Main text with gradient simulation
    for i in range(3):
        offset = i * 2
        alpha = 255 - i * 30
        color = (100 + i * 50, 150 + i * 30, 255 - i * 20)
        draw.text((center_x - offset, center_y - offset), 'R', fill=color, font=font, anchor='mm')
    
    # Final white text
    draw.text((center_x, center_y), 'R', fill='white', font=font, anchor='mm')
    
    # Add decorative elements
    # Small dots in corners
    dot_positions = [
        (80, 80), (432, 80), (80, 432), (432, 432)
    ]
    for x, y in dot_positions:
        draw.ellipse([x-8, y-8, x+8, y+8], fill=(100, 200, 255, 180))
        draw.ellipse([x-4, y-4, x+4, y+4], fill='white')
    
    # Save in multiple formats
    image.save('icon.png', 'PNG')
    image.save('icon.ico', 'ICO')
    
    print('✨ Modern gradient R icon created successfully!')

def create_animated_icon_frames():
    """Create multiple frames for animated icon"""
    frames = []
    size = (512, 512)
    
    for frame in range(8):
        image = Image.new('RGBA', size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        center_x, center_y = size[0] // 2, size[1] // 2
        
        # Animated gradient rotation
        rotation = (frame * 45) * math.pi / 180
        
        # Background
        draw.rounded_rectangle([30, 30, 482, 482], radius=80, fill=(25, 25, 35, 240))
        
        # Animated ring
        for i in range(3):
            angle = rotation + i * 2 * math.pi / 3
            x = center_x + 180 * math.cos(angle)
            y = center_y + 180 * math.sin(angle)
            draw.ellipse([x-15, y-15, x+15, y+15], fill=(100, 200, 255, 150 - i * 30))
        
        # Text
        font = None
        font_paths = [
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
            '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
        ]
        for path in font_paths:
            if os.path.exists(path):
                font = ImageFont.truetype(path, 320)
                break
        if not font: 
            font = ImageFont.load_default()
        
        draw.text((center_x, center_y), 'R', fill='white', font=font, anchor='mm')
        frames.append(image)
    
    # Save as animated GIF if PIL supports it
    if len(frames) > 1:
        frames[0].save('icon_animated.gif', save_all=True, append_images=frames[1:], 
                      duration=100, loop=0)
        print('🎬 Animated icon created as icon_animated.gif')

if __name__ == '__main__':
    create_modern_icon()
    create_animated_icon_frames()
