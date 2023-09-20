import os
import re
import torch
import numpy as np

import folder_paths
from comfy.model_management import text_encoder_device, text_encoder_offload_device, soft_empty_cache

from ..model_downloader import load_models
from ..utils import is_junction, tensor2pil, resize_image

danbooru = None
blip_size = 384
gpu = text_encoder_device()
cpu = text_encoder_offload_device()
model_url = "https://github.com/AUTOMATIC1111/TorchDeepDanbooru/releases/download/v1/model-resnet_custom_v3.pt"
re_special = re.compile(r'([\\()])')


def load_danbooru(device_mode):
    global danbooru
    if danbooru is None:
        blip_dir = os.path.join(folder_paths.models_dir, "blip")
        if not os.path.exists(blip_dir) and not is_junction(blip_dir):
            os.makedirs(blip_dir, exist_ok=True)

        files = load_models(
            model_path=blip_dir,
            model_url='https://github.com/AUTOMATIC1111/TorchDeepDanbooru/releases/download/v1/model-resnet_custom_v3.pt',
            ext_filter=[".pt"],
            download_name='model-resnet_custom_v3.pt',
        )

        from .models.deepbooru_model import DeepDanbooruModel
        danbooru = DeepDanbooruModel()
        danbooru.load_state_dict(torch.load(files[0], map_location="cpu"))
        danbooru.eval()

    if device_mode != "CPU":
        danbooru = danbooru.to(gpu)

    danbooru.is_auto_mode = device_mode == "AUTO"

    return danbooru


def unload_danbooru():
    global danbooru
    if danbooru is not None and danbooru.is_auto_mode:
        danbooru = danbooru.to(cpu)

    soft_empty_cache()


class DeepDanbooruCaption:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "image": ("IMAGE",),
                "threshold": ("FLOAT", {"default": 0.5, "min": 0, "max": 1, "step": 0.01}),
                "sort_alpha": ([True, False], {"default": True}),
                "use_spaces": ([True, False], {"default": True}),
                "escape": ([True, False], {"default": True}),
                "filter_tags": ("STRING", {"default": "blacklist", "multiline": True}),
            },
            "optional": {
                "device_mode": (["AUTO", "Prefer GPU", "CPU"],),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("caption",)
    FUNCTION = "caption"
    CATEGORY = "Art Venture/Utils"

    def caption(self, image, threshold, sort_alpha, use_spaces, escape, filter_tags, device_mode="AUTO"):
        model = load_danbooru(device_mode)

        try:
            image = tensor2pil(image)
            image = resize_image(2, image.convert("RGB"), 512, 512)
            arr = np.expand_dims(np.array(image, dtype=np.float32), 0) / 255

            with torch.no_grad():
                x = torch.from_numpy(arr).to(gpu)
                y = model(x)[0].detach().cpu().numpy()

            probability_dict = {}

            for tag, probability in zip(model.tags, y):
                if probability < threshold:
                    continue

                if tag.startswith("rating:"):
                    continue

                probability_dict[tag] = probability

            if sort_alpha:
                tags = sorted(probability_dict)
            else:
                tags = [tag for tag, _ in sorted(probability_dict.items(), key=lambda x: -x[1])]

            res = []
            filtertags = {x.strip().replace(' ', '_') for x in filter_tags.split(",")}

            for tag in [x for x in tags if x not in filtertags]:
                probability = probability_dict[tag]
                tag_outformat = tag
                if use_spaces:
                    tag_outformat = tag_outformat.replace('_', ' ')
                if escape:
                    tag_outformat = re.sub(re_special, r'\\\1', tag_outformat)

                res.append(tag_outformat)

            return (", ".join(res),)
        except:
            raise
        finally:
            unload_danbooru()