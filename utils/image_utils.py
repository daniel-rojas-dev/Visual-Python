"""
image_utils.py — PIL image loading with smart resizing and LRU cache.
Keeps RAM usage low by capping image dimensions and caching results.
"""
from functools import lru_cache
from PIL import Image
import customtkinter as ctk
import os


# Max pixels per side for imported images (saves RAM on low-end PCs)
MAX_IMAGE_DIM = 512


@lru_cache(maxsize=32)
def _load_cached(path: str, max_w: int, max_h: int):
    """Load & resize image (cached by path+size). Returns PIL.Image."""
    img = Image.open(path)
    img.thumbnail((max_w, max_h), Image.LANCZOS)
    return img


def load_ctk_image(path: str, size: tuple = None) -> "ctk.CTkImage | None":
    """
    Load an image from `path`, resize to `size` (w, h) or auto-shrink.
    Returns a CTkImage ready for use in widgets, or None on failure.
    """
    if not path or not os.path.isfile(path):
        return None
    try:
        max_w = size[0] if size else MAX_IMAGE_DIM
        max_h = size[1] if size else MAX_IMAGE_DIM
        pil_img = _load_cached(path, max_w, max_h)
        return ctk.CTkImage(light_image=pil_img, dark_image=pil_img,
                            size=pil_img.size)
    except Exception:
        return None


def clear_image_cache():
    """Call when loading a new project to free RAM."""
    _load_cached.cache_clear()
