#!/usr/bin/env python3
"""
visualize_kit.py: Generate manifest.html with spectrograms for a TR-8S kit.
"""

import os
import argparse
import numpy as np
import matplotlib.pyplot as plt
import librosa
import librosa.display

def generate_spectrogram(audio_path, image_path):
    try:
        y, sr = librosa.load(audio_path, sr=None)
        D = librosa.amplitude_to_db(np.abs(librosa.stft(y)), ref=np.max)
        
        plt.figure(figsize=(4, 2))
        librosa.display.specshow(D, sr=sr, x_axis='time', y_axis='hz', cmap='magma')
        plt.axis('off')
        plt.tight_layout(pad=0)
        plt.savefig(image_path, bbox_inches='tight', pad_inches=0)
        plt.close()
        return True
    except Exception as e:
        print(f"Failed to plot {audio_path}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--kit_dir', required=True)
    args = parser.parse_args()
    
    html_content = """
    <html>
    <head>
        <style>
            body { background: #111; color: #eee; font-family: sans-serif; }
            .sample { display: inline-block; width: 300px; margin: 10px; background: #222; padding: 10px; border-radius: 5px; }
            img { width: 100%; height: 100px; object-fit: cover; background: #000; }
            h3 { font-size: 14px; margin: 5px 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
            audio { width: 100%; margin-top: 5px; }
            .category { clear: both; padding-top: 20px; border-top: 1px solid #444; }
        </style>
    </head>
    <body>
    <h1>TR-8S Kit Manifest</h1>
    """
    
    # Walk kit dir
    # Expecting: KIT_NAME/DRUMS etc.
    
    # We want to iterate known categories order
    categories = ["DRUMS", "PADS", "FX"]
    
    total_images = 0
    
    for cat in categories:
        cat_dir = os.path.join(args.kit_dir, cat)
        if not os.path.exists(cat_dir): continue
        
        html_content += f"<div class='category'><h2>{cat}</h2>"
        
        files = sorted([f for f in os.listdir(cat_dir) if f.lower().endswith('.wav')])
        
        # Create 'img' folder inside kit
        img_dir = os.path.join(args.kit_dir, "img")
        os.makedirs(img_dir, exist_ok=True)
        
        for f in files:
            wav_path = os.path.join(cat_dir, f)
            img_name = f + ".png"
            img_path = os.path.join(img_dir, img_name)
            
            # Generate if not exists
            if not os.path.exists(img_path):
                generate_spectrogram(wav_path, img_path)
                total_images += 1
                
            # Rel paths for HTML
            # wav is in CAT/file.wav, img is in img/file.wav.png
            # HTML is in ROOT
            
            rel_wav = f"{cat}/{f}"
            rel_img = f"img/{img_name}"
            
            html_content += f"""
            <div class='sample'>
                <img src='{rel_img}' loading='lazy'>
                <h3>{f}</h3>
                <audio controls src='{rel_wav}'></audio>
            </div>
            """
            
        html_content += "</div>"
        
    html_content += "</body></html>"
    
    with open(os.path.join(args.kit_dir, "manifest.html"), "w") as f:
        f.write(html_content)
        
    print(f"[VISUALIZER] Generated manifest with {total_images} spectrograms.")

if __name__ == "__main__":
    main()
