from pathlib import Path

from PIL import Image


class ImageProcessor:

    def convert(self, input_path: str, output_format: str, output_path: str | None = None) -> str:
        p = Path(input_path)
        if not p.exists():
            return f"Image introuvable: {input_path}"

        out_format = output_format.upper()
        if out_format == "JPG":
            out_format = "JPEG"

        if not output_path:
            output_path = str(p.with_suffix(f".{output_format.lower()}"))

        img = Image.open(p)
        if img.mode in ("RGBA", "P") and out_format == "JPEG":
            img = img.convert("RGB")

        img.save(output_path, format=out_format)
        return f"Image convertie: {output_path} ({Path(output_path).stat().st_size} octets)"

    def resize(
        self,
        input_path: str,
        width: int,
        height: int | None = None,
        maintain_ratio: bool = True,
    ) -> str:
        p = Path(input_path)
        if not p.exists():
            return f"Image introuvable: {input_path}"

        img = Image.open(p)
        original_w, original_h = img.size

        if maintain_ratio and height is None:
            ratio = width / original_w
            height = int(original_h * ratio)
        elif height is None:
            height = original_h

        img_resized = img.resize((width, height), Image.LANCZOS)
        output_path = str(p.with_stem(f"{p.stem}_resized"))
        img_resized.save(output_path)

        return f"Image redimensionnée: {output_path} ({width}×{height})"

    def compress(self, input_path: str, quality: int = 85) -> str:
        p = Path(input_path)
        if not p.exists():
            return f"Image introuvable: {input_path}"

        img = Image.open(p)
        output_path = str(p.with_stem(f"{p.stem}_compressed"))

        if p.suffix.lower() in (".jpg", ".jpeg"):
            img.save(output_path, format="JPEG", quality=quality, optimize=True)
        elif p.suffix.lower() == ".webp":
            img.save(output_path, format="WEBP", quality=quality)
        else:
            img.save(output_path, optimize=True)

        original_size = p.stat().st_size
        new_size = Path(output_path).stat().st_size
        reduction = ((original_size - new_size) / original_size) * 100

        return f"Image compressée: {output_path} ({new_size} octets, -{reduction:.1f}%)"

    def get_info(self, image_path: str) -> str:
        p = Path(image_path)
        if not p.exists():
            return f"Image introuvable: {image_path}"

        img = Image.open(p)
        info = {
            "format": img.format,
            "mode": img.mode,
            "dimensions": f"{img.size[0]}×{img.size[1]}",
            "width": img.size[0],
            "height": img.size[1],
            "dpi": img.info.get("dpi"),
            "file_size": f"{p.stat().st_size:,} octets",
        }

        lines = [f"**Image: {p.name}**"]
        for key, value in info.items():
            if value is not None:
                lines.append(f"  • {key}: {value}")
        return "\n".join(lines)

    def batch_convert(self, directory: str, from_format: str, to_format: str) -> str:
        dir_path = Path(directory)
        if not dir_path.is_dir():
            return f"Dossier introuvable: {directory}"

        converted = []
        pattern = f"*.{from_format.lower()}"

        for file in dir_path.glob(pattern):
            try:
                result = self.convert(str(file), to_format)
                converted.append(result)
            except Exception as e:
                converted.append(f"Erreur pour {file.name}: {e}")

        if not converted:
            return f"Aucune image .{from_format} trouvée dans {directory}"

        return f"**{len(converted)} images converties:**\n" + "\n".join(converted)

    def create_thumbnail(self, input_path: str, max_size: tuple = (300, 300)) -> str:
        p = Path(input_path)
        if not p.exists():
            return f"Image introuvable: {input_path}"

        img = Image.open(p)
        img.thumbnail(max_size, Image.LANCZOS)
        output_path = str(p.with_stem(f"{p.stem}_thumb"))
        img.save(output_path)

        return f"Miniature créée: {output_path} ({img.size[0]}×{img.size[1]})"
