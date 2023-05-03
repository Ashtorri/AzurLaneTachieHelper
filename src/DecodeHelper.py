import os

import numpy as np
from PIL import Image
from pytoshop.enums import ColorMode
from pytoshop.user import nested_layers

from .TextureHelper import TextureHelper
from .utility import gen_ps_layer, raw_name


class DecodeHelper(TextureHelper):
    def exec(self, dir: str):
        painting = []
        for _ in self.deps:
            name = raw_name(_)
            self.metas[name]["dec"] = self.decode(
                self.metas[name]["mesh"],
                self.metas[name]["enc"],
                self.metas[name]["RawSpriteSize"],
            ).resize(self.metas[name]["SizeDelta"], Image.Resampling.LANCZOS)
            sub = Image.new("RGBA", self.size)
            sub.paste(self.metas[name]["dec"], self.metas[name]["Offset"])
            painting += [gen_ps_layer(sub, name)]

        face = []
        for _ in self.metas["face"]["diff"]:
            full = Image.new("RGBA", self.size)
            full.paste(_.image.transpose(Image.FLIP_TOP_BOTTOM), self.metas["face"]["Offset"])
            face += [gen_ps_layer(full, _.name, False)]

        layers = [
            nested_layers.Group(name="paintingface", layers=face, closed=False),
            nested_layers.Group(name="painting", layers=painting, closed=False),
        ]
        psd = nested_layers.nested_layers_to_psd(layers, color_mode=ColorMode.rgb)
        path = os.path.join(dir, self.name + ".psd")
        with open(path, "wb") as f:
            psd.write(f)

        return path

    def decode(self, mesh: dict, enc: Image.Image, rss: tuple) -> Image.Image:
        dec = Image.new("RGBA", rss)

        v, vt, f = mesh.values()
        for _ in f:
            lb1, ru1 = self._measure(v[_])
            lb2, ru2 = self._measure(vt[_] * enc.size)

            dec.paste(enc.crop((*lb2, *ru2)), (*lb1,))

        return dec

    def _measure(self, data):
        lb = np.round(np.stack(data, -1).min(-1)).astype(np.int32)
        ru = np.round(np.stack(data, -1).max(-1)).astype(np.int32)
        return lb, ru
