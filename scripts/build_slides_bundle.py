import os
import glob
import json

slides_dir = os.path.join("docs", "presentation", "slides")
output_bundle = os.path.join("docs", "presentation", "js", "slides-bundle.js")

# Find all slide html files sorted by filename
slide_files = sorted(glob.glob(os.path.join(slides_dir, "slide-*.html")))

slides_data = []
for file_path in slide_files:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read().strip()
        slides_data.append(content)

js_content = "// Auto-generated modular slides bundle for 100% offline file:// & CORS-free compatibility\n"
js_content += "window.MODULAR_SLIDES = " + json.dumps(slides_data, indent=2, ensure_ascii=False) + ";\n"

with open(output_bundle, "w", encoding="utf-8") as f:
    f.write(js_content)

print(f"Successfully generated {output_bundle} with {len(slides_data)} modular slides.")
