# ComfyUI Flux Prompt Saver

The Flux Prompt Saver is a custom node for ComfyUI that works in conjunction with the Flux Sampler Parameters node from the ComfyUI Essentials package. This node allows you to save images with metadata that includes information from the Flux Sampler Parameters pipeline.

## Features

- Saves images with metadata from the Flux Sampler Parameters pipeline
- Uses checkpoint selection for model names
- Combines sampler and scheduler information in the metadata
  
## Dependencies

This node requires the Flux Sampler Parameters node from the ComfyUI Essentials package by cubiq. You must install ComfyUI Essentials before using this node.

- [ComfyUI Essentials](https://github.com/cubiq/ComfyUI_essentials)

## Installation

To install the Flux Prompt Saver node:

1. Navigate to your ComfyUI custom nodes directory.
2. Clone this repository:
   ```
   git clone https://github.com/markuryy/ComfyUI-Flux-Prompt-Saver
   ```
3. Restart ComfyUI and refresh.

Note: This node is also available through ComfyUI Manager for easy installation.

## Usage

1. Add the Flux Sampler Parameters node from ComfyUI Essentials to your workflow.
2. Connect the output of VAE Decode to the "images" input of the Flux Prompt Saver.
3. Connect the "params" output from the Flux Sampler Parameters node to the "params" input of the Flux Prompt Saver.
4. Provide the positive prompt, model name, and optional negative prompt.
5. Run your workflow. The Flux Prompt Saver will save your images with the appropriate metadata.

## Notes

This node is designed for users who need to save images with specific metadata from the Flux Sampler Parameters pipeline. It may not be necessary for all ComfyUI workflows.

## Credits

- Flux Sampler Parameters node by [cubiq](https://github.com/cubiq)
- ComfyUI Essentials: https://github.com/cubiq/ComfyUI_essentials
