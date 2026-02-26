from PIL import Image, ImageDraw, ImageFont

def create_alert_image(data_dict, output_path):
    # Colors matching the template
    color_red = (220, 20, 60)
    color_yellow = (255, 255, 0)
    color_green = (144, 238, 144)
    color_black = (0, 0, 0)
    color_white = (255, 255, 255)
    
    # Fonts
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 16)
        font_bold = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 16)
    except IOError:
        font = ImageFont.load_default()
        font_bold = font

    # Table dimensions
    col1_width = 300
    col2_width = 450
    row_height = 30
    total_width = col1_width + col2_width
    num_rows = len(data_dict) + 1  # +1 for the top date row if needed, but let's just do len(data_dict) for pairs and add 1 for title
    
    # We will assume a specific header, or we take the first item as title
    total_height = num_rows * row_height

    img = Image.new('RGB', (total_width, total_height), color=color_white)
    draw = ImageDraw.Draw(img)
    
    y = 0
    # Draw title
    title_text = "26.02.2026"
    draw.rectangle([(0, y), (total_width, y + row_height)], outline=color_black, width=1)
    
    # We need text length to center it
    # Use textbbox instead of textsize
    bbox = draw.textbbox((0,0), title_text, font=font_bold)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    draw.text(((total_width - tw) / 2, y + (row_height - th) / 2 - 2), title_text, font=font_bold, fill=color_black)
    y += row_height

    # Draw rows
    for key, value in data_dict.items():
        # Determine background color
        bg_color = color_white
        if "ўчиш вақти" in key:
            bg_color = color_red
        elif "Носозлик сабаби" in key:
            bg_color = color_yellow
        elif "ёнган вақти" in key:
            bg_color = color_green

        # Draw left cell
        draw.rectangle([(0, y), (col1_width, y + row_height)], fill=bg_color, outline=color_black, width=1)
        draw.text((5, y + 5), key, font=font, fill=color_black)

        # Draw right cell
        draw.rectangle([(col1_width, y), (total_width, y + row_height)], fill=bg_color, outline=color_black, width=1)
        draw.text((col1_width + 5, y + 5), str(value), font=font, fill=color_black)

        y += row_height

    img.save(output_path)
    print("Saved to", output_path)

if __name__ == "__main__":
    data = {
        "Боғлама номи": "7-Боғлама",
        "ЭАТС": "ЭАТС-744",
        "Қурилма тури": "OLT",
        "Қурилма номи": "TOBS-744-OLT-MA5801-PSKOM",
        "Қурилма ўрнатилган жой": "OUTDOOR",
        "Қурилма уланиши ( UPLINK )": "TOBS-744.9-SA_Huawei-S5320_1_Ge0/0/17",
        "Қурилма ўтказувчанлик сигими": "10G",
        "Қурилма IP адреси": "10.47.132.19",
        "Монтированный ёмкость": "1044",
        "Умумий абонентлар сони": "0",
        "Қурилма ўчиш вақти": "26.02.2026-03:43",
        "Носозлик сабаби": "Номаълум",
        "Қурилма ёнган вақти": "26.02.2026-06:52"
    }
    create_alert_image(data, "poc_alert.png")
