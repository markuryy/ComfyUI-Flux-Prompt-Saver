import os
import torch
import numpy as np
from PIL import Image
from PIL.PngImagePlugin import PngInfo
import folder_paths
from datetime import datetime

class FluxPromptSaver:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE",),
                "params": ("SAMPLER_PARAMS",),
                "positive": ("STRING",),
                "model_name": (folder_paths.get_filename_list("checkpoints"),),
            },
            "optional": {
                "negative": ("STRING", {"default": ""}),
            }
        }

    RETURN_TYPES = ()
    FUNCTION = "save_images"
    OUTPUT_NODE = True
    CATEGORY = "image"

    def save_images(self, images, params, positive, model_name, negative=""):
        results = []
        for image in images:
            i = 255. * image.cpu().numpy()
            img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))
            
            metadata = PngInfo()
            metadata.add_text("parameters", self.create_metadata_string(params, positive, negative, model_name))
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"FLUX_{timestamp}.png"
            path = folder_paths.get_output_directory()
            file_path = os.path.join(path, filename)
            
            img.save(file_path, pnginfo=metadata, optimize=True)
            results.append({
                "filename": filename,
                "subfolder": "",
                "type": "output"
            })

        return {"ui": {"images": results}}

    def create_metadata_string(self, params, positive, negative, model_name):
        p = params[0]
        sampler_scheduler = f"{p['sampler']}_{p['scheduler']}" if p['scheduler'] != 'normal' else p['sampler']
        return f"{positive}\nNegative prompt: {negative}\n" \
               f"Steps: {p['steps']}, Sampler: {sampler_scheduler}, CFG scale: 1.0, Seed: {p['seed']}, " \
               f"Size: {p['width']}x{p['height']}, Model hash: {p.get('model_hash', '')}, " \
               f"Model: {model_name}, Version: ComfyUI"

NODE_CLASS_MAPPINGS = {
    "FluxPromptSaver": FluxPromptSaver
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "FluxPromptSaver": "Flux Prompt Saver"
}