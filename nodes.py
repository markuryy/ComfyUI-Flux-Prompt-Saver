import os
import re
import torch
import numpy as np
from PIL import Image
from PIL.PngImagePlugin import PngInfo
import folder_paths
from datetime import datetime
import comfy.samplers
import random
import time
import logging
from comfy.utils import ProgressBar
from comfy_extras.nodes_custom_sampler import Noise_RandomNoise, BasicScheduler, BasicGuider, SamplerCustomAdvanced
from comfy_extras.nodes_latent import LatentBatch
from comfy_extras.nodes_model_advanced import ModelSamplingFlux, ModelSamplingAuraFlow

def parse_string_to_list(input_string):
    try:
        if not input_string:
            return []
        items = input_string.replace('\n', ',').split(',')
        result = []
        for item in items:
            item = item.strip()
            if not item:
                continue
            try:
                num = float(item)
                if num.is_integer():
                    num = int(num)
                result.append(num)
            except ValueError:
                continue
        return result
    except:
        return []

def conditioning_set_values(conditioning, values):
    c = []
    for t in conditioning:
        n = [t[0], t[1].copy()]
        for k, v in values.items():
            if k == "guidance":
                n[1]['guidance_scale'] = v
        c.append(tuple(n))
    return c

class FluxTextSampler:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
                    "model": ("MODEL", ),
                    "conditioning": ("CONDITIONING", ),
                    "latent_image": ("LATENT", ),
                    "seed": ("INT", { "default": 0, "min": 0, "max": 0xffffffffffffffff }),
                    "sampler": ("STRING", { "multiline": False, "dynamicPrompts": False, "default": "euler" }),
                    "scheduler": ("STRING", { "multiline": False, "dynamicPrompts": False, "default": "simple" }),
                    "steps": ("STRING", { "multiline": False, "dynamicPrompts": False, "default": "20" }),
                    "guidance": ("STRING", { "multiline": False, "dynamicPrompts": False, "default": "3.5" }),
                    "max_shift": ("STRING", { "multiline": False, "dynamicPrompts": False, "default": "" }),
                    "base_shift": ("STRING", { "multiline": False, "dynamicPrompts": False, "default": "" }),
                    "denoise": ("STRING", { "multiline": False, "dynamicPrompts": False, "default": "1.0" }),
                }}
    
    RETURN_TYPES = ("LATENT","SAMPLER_PARAMS")
    RETURN_NAMES = ("latent", "params")
    FUNCTION = "execute"
    CATEGORY = "sampling"

    def execute(self, model, conditioning, latent_image, seed, sampler, scheduler, steps, guidance, max_shift, base_shift, denoise):
        is_schnell = model.model.model_type == comfy.model_base.ModelType.FLOW

        # Handle seed
        noise = [seed]

        if sampler == '*':
            sampler = comfy.samplers.KSampler.SAMPLERS
        elif sampler.startswith("!"):
            sampler = sampler.replace("\n", ",").split(",")
            sampler = [s.strip("! ") for s in sampler]
            sampler = [s for s in comfy.samplers.KSampler.SAMPLERS if s not in sampler]
        else:
            sampler = sampler.replace("\n", ",").split(",")
            sampler = [s.strip() for s in sampler if s.strip() in comfy.samplers.KSampler.SAMPLERS]
        if not sampler:
            sampler = ['euler']

        if scheduler == '*':
            scheduler = comfy.samplers.KSampler.SCHEDULERS
        elif scheduler.startswith("!"):
            scheduler = scheduler.replace("\n", ",").split(",")
            scheduler = [s.strip("! ") for s in scheduler]
            scheduler = [s for s in comfy.samplers.KSampler.SCHEDULERS if s not in scheduler]
        else:
            scheduler = scheduler.replace("\n", ",").split(",")
            scheduler = [s.strip() for s in scheduler]
            scheduler = [s for s in scheduler if s in comfy.samplers.KSampler.SCHEDULERS]
        if not scheduler:
            scheduler = ['simple']

        if steps == "":
            if is_schnell:
                steps = "4"
            else:
                steps = "20"
        steps = parse_string_to_list(steps)
        
        denoise = "1.0" if denoise == "" else denoise
        denoise = parse_string_to_list(denoise)

        guidance = "3.5" if guidance == "" else guidance
        guidance = parse_string_to_list(guidance)
        
        if not is_schnell:
            max_shift = "1.15" if max_shift == "" else max_shift
            base_shift = "0.5" if base_shift == "" else base_shift
        else:
            max_shift = "0"
            base_shift = "1.0" if base_shift == "" else base_shift

        max_shift = parse_string_to_list(max_shift)
        base_shift = parse_string_to_list(base_shift)
               
        cond_text = None
        if isinstance(conditioning, dict) and "encoded" in conditioning:
            cond_text = conditioning["text"]
            cond_encoded = conditioning["encoded"]
        else:
            cond_encoded = [conditioning]

        out_latent = None
        out_params = []

        basicschedueler = BasicScheduler()
        basicguider = BasicGuider()
        samplercustomadvanced = SamplerCustomAdvanced()
        latentbatch = LatentBatch()
        modelsamplingflux = ModelSamplingFlux() if not is_schnell else ModelSamplingAuraFlow()
        width = latent_image["samples"].shape[3]*8
        height = latent_image["samples"].shape[2]*8

        total_samples = len(cond_encoded) * len(noise) * len(max_shift) * len(base_shift) * len(guidance) * len(sampler) * len(scheduler) * len(steps) * len(denoise)
        current_sample = 0
        if total_samples > 1:
            pbar = ProgressBar(total_samples)

        for i in range(len(cond_encoded)):
            conditioning = cond_encoded[i]
            ct = cond_text[i] if cond_text else None
            for n in noise:
                randnoise = Noise_RandomNoise(n)
                for ms in max_shift:
                    for bs in base_shift:
                        if is_schnell:
                            work_model = modelsamplingflux.patch_aura(model, bs)[0]
                        else:
                            work_model = modelsamplingflux.patch(model, ms, bs, width, height)[0]
                        for g in guidance:
                            cond = conditioning_set_values(conditioning, {"guidance": g})
                            guider = basicguider.get_guider(work_model, cond)[0]
                            for s in sampler:
                                samplerobj = comfy.samplers.sampler_object(s)
                                for sc in scheduler:
                                    for st in steps:
                                        for d in denoise:
                                            sigmas = basicschedueler.get_sigmas(work_model, sc, st, d)[0]
                                            current_sample += 1
                                            logging.info(f"Sampling {current_sample}/{total_samples} with seed {n}, sampler {s}, scheduler {sc}, steps {st}, guidance {g}, max_shift {ms}, base_shift {bs}, denoise {d}")
                                            start_time = time.time()
                                            latent = samplercustomadvanced.sample(randnoise, guider, samplerobj, sigmas, latent_image)[1]
                                            elapsed_time = time.time() - start_time
                                            out_params.append({
                                                "time": elapsed_time,
                                                "seed": n,
                                                "width": width,
                                                "height": height,
                                                "sampler": s,
                                                "scheduler": sc,
                                                "steps": st,
                                                "guidance": g,
                                                "max_shift": ms,
                                                "base_shift": bs,
                                                "denoise": d,
                                                "prompt": ct
                                            })

                                            if out_latent is None:
                                                out_latent = latent
                                            else:
                                                out_latent = latentbatch.batch(out_latent, latent)[0]
                                            if total_samples > 1:
                                                pbar.update(1)

        return (out_latent, out_params)

class FluxPromptSaver:
    def __init__(self):
        self.output_dir = folder_paths.get_output_directory()
        self.type = "output"
        self.default_size = 1344  # Default image size

    @classmethod
    def INPUT_TYPES(s):
        return {
        "required": {
            "images": ("IMAGE",),
            "params": ("SAMPLER_PARAMS",),
            "positive": ("STRING", {"forceInput": True}),
            "model_name": ("STRING", {"forceInput": True}),
            "filename_prefix": ("STRING", {
                "default": "%date:yyyy-MM-dd%",
                "tooltip": "Subfolder to save the images in. Supports date formatting like %date:yyyy-MM-dd%"
            }),
            "filename": ("STRING", {
                "default": "FLUX_%date:HHmmss%",
                "tooltip": "Filename for the image. Supports date formatting like %date:HHmmss%"
            }),
        },
        "optional": {
            "negative": ("STRING", {"forceInput": True}),
        }
    }


    RETURN_TYPES = ()
    FUNCTION = "save_images"
    OUTPUT_NODE = True
    CATEGORY = "image"

    def save_images(self, images, params, positive, model_name, filename_prefix, filename, negative=""):
        # Replace date placeholders with actual date strings
        filename_prefix = self.replace_date_placeholders(filename_prefix)
        filename = self.replace_date_placeholders(filename)

        results = []
        p = params[0]

        # Construct the full output folder path
        full_output_folder = os.path.join(self.output_dir, filename_prefix)
        os.makedirs(full_output_folder, exist_ok=True)

        for image in images:
            i = 255. * image.cpu().numpy()
            img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))

            metadata = PngInfo()
            metadata.add_text("parameters", self.create_metadata_string(p, positive, negative, model_name))

            # Initial file path
            file_base = filename
            file_ext = ".png"
            file_name = f"{file_base}{file_ext}"
            file_path = os.path.join(full_output_folder, file_name)

            # Check if file exists and add iterator if necessary
            counter = 1
            while os.path.exists(file_path):
                file_name = f"{file_base}_{counter}{file_ext}"
                file_path = os.path.join(full_output_folder, file_name)
                counter += 1

            # Save the image
            img.save(file_path, pnginfo=metadata, optimize=True)
            results.append({
                "filename": file_name,
                "subfolder": filename_prefix,
                "type": self.type
            })

        return {"ui": {"images": results}}

    def replace_date_placeholders(self, s):
        # Regular expression to find all '%date:...%' placeholders
        date_placeholder_pattern = re.compile(r'%date:(.*?)%')

        def replace_match(match):
            # Extract the date format from the placeholder
            date_format = match.group(1)
            # Map custom date tokens to strftime tokens
            format_mappings = {
                'yyyy': '%Y',
                'MM': '%m',
                'dd': '%d',
                'HH': '%H',
                'mm': '%M',
                'ss': '%S',
                # Add more mappings if needed
            }
            # Replace custom tokens with strftime tokens
            for token, strftime_token in format_mappings.items():
                date_format = date_format.replace(token, strftime_token)
            try:
                # Return the formatted date
                return datetime.now().strftime(date_format)
            except Exception as e:
                # If formatting fails, return the original placeholder
                return match.group(0)

        # Replace all date placeholders in the string
        return date_placeholder_pattern.sub(replace_match, s)

    def create_metadata_string(self, params, positive, negative, model_name):
        sampler_scheduler = f"{params['sampler']}_{params['scheduler']}" if params['scheduler'] != 'normal' else params['sampler']

        negative_text = "(not used)" if not negative else negative

        guidance_val = params.get('guidance', 1.0)
        seed_val = params.get('seed', '?')

        return f"{positive}\nNegative prompt: {negative_text}\n" \
               f"Steps: {params['steps']}, Sampler: {sampler_scheduler}, CFG scale: {guidance_val}, Seed: {seed_val}, " \
               f"Size: {params['width']}x{params['height']}, Model hash: {params.get('model_hash', '')}, " \
               f"Model: {model_name}, Version: ComfyUI"


class ModelName:
    @classmethod
    def INPUT_TYPES(s):
        model_list = []
        for model_folder in ["checkpoints", "models", "unet", "diffusion_models"]:
            try:
                model_list.extend(folder_paths.get_filename_list(model_folder))
            except:
                pass
        model_list = list(set(model_list))
        
        return {"required": {"model_name": (model_list,)}}

    RETURN_TYPES = ("STRING",)
    FUNCTION = "get_name"
    CATEGORY = "utils"

    def get_name(self, model_name):
        return (model_name,)

NODE_CLASS_MAPPINGS = {
    "FluxPromptSaver": FluxPromptSaver,
    "FluxTextSampler": FluxTextSampler,
    "ModelName": ModelName
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "FluxPromptSaver": "🐈‍⬛ Flux Prompt Saver",
    "FluxTextSampler": "🐈‍⬛ Flux Text Sampler",
    "ModelName": "🐈‍⬛ Model Name"
}