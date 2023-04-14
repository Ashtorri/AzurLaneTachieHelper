from PIL import Image
from pprint import pprint
from typing import Dict
from UnityPy.classes import RectTransform
import numpy as np
import UnityPy


def parse_obj(mesh):  
    with open(mesh) as file:
        lines = [_.replace('\n', '').split(' ') for _ in file.readlines()]

        data = {
            'g': [],   # group name
            'v': [],   # geometric vertices
            'vt': [],  # texture vertices
            'f': []    # face, indexed as v/vt/vn
        }
        for line in lines:
            data[line[0]].append(line[1:])

        v = np.array(data['v'], dtype=np.float32)
        vt = np.array(data['vt'], dtype=np.float32)
        f = np.array(
            [[[___ for ___ in __.split('/')] for __ in _] for _ in data['f']],
            dtype=np.int32
        )

        v[:, 0] = -v[:, 0]
        s = np.stack(v, -1).max(-1) + 1

        print(f'[INFO] Mesh file: {mesh}')
        print(f'[INFO] Vertex count: {len(v)}')
        print(f'[INFO] Texcoord count: {len(vt)}')
        print(f'[INFO] Face count: {len(f)}')
        print(f'[INFO] Mesh size: {s[:2]}')

    return {'v': v, 'vt': vt, 'f': f, 'v_normalized': v / s}


def read_img(filename, resize=None):
    img = Image.open(filename)
    if resize is not None:
        img = img.resize(resize, resample=Image.Resampling.HAMMING)
    return np.array(img.transpose(Image.FLIP_TOP_BOTTOM))


def save_img(data, filename):
    Image.fromarray(data).transpose(Image.FLIP_TOP_BOTTOM).save(filename)


def resize_img(data, size):
    return np.array(Image.fromarray(data).resize(size, resample=Image.Resampling.HAMMING))


def get_rect_name(rect: RectTransform):
    return rect.m_GameObject.read().m_Name


def convert(raw: RectTransform) -> Dict[str, np.ndarray]:
    entry = [
        'm_LocalPosition',
        'm_LocalScale',
        'm_AnchorMin',
        'm_AnchorMax',
        'm_AnchoredPosition',
        'm_SizeDelta',
        'm_Pivot'
    ]
    return {_: np.array([*raw.to_dict()[_].values()][:2]) for _ in entry}


def get_img_area(data, size, pad=0):
    # pad with one extra pixel and clip
    lb = np.round(np.maximum(np.stack(data, -1).min(-1) - pad, 0)).astype(np.int32)
    ru = np.round(np.minimum(np.stack(data, -1).max(-1) + pad, size - 1)).astype(np.int32)

    return *lb, *(ru - lb + 1)


def decode_tex(enc_img, dec_size, v, vt, f, *args):
    enc_img = Image.fromarray(enc_img)
    dec_img = Image.new('RGBA', tuple(dec_size))
    enc_size = np.array(enc_img.size)

    for rect in zip(f[::2], f[1::2]):
        index_v, index_vt = np.stack([*rect[0][:2, :2], *rect[1][:2, :2]], -1)

        x1, y1, w1, h1 = get_img_area(v[index_v - 1, :2], dec_size, 0)
        x2, y2, w2, h2 = get_img_area(vt[index_vt - 1] * enc_size, enc_size, 0)
        # print(x1, y1, w1, h1)
        # print(x2, y2, w2, h2)

        sub = enc_img.crop((x2, y2, x2 + w2, y2 + h2)).resize((w1, h1))
        dec_img.paste(sub, (x1, y1))

    return np.array(dec_img)


def encode_tex(dec_img, enc_size, v, vt, f, *args):
    dec_img = Image.fromarray(dec_img)
    enc_img = Image.new('RGBA', tuple(enc_size), 1)
    dec_size = np.array(dec_img.size)

    for rect in zip(f[::2], f[1::2]):
        index_v, index_vt = np.stack([*rect[0][:2, :2], *rect[1][:2, :2]], -1)

        x1, y1, w1, h1 = get_img_area(v[index_v - 1, :2], dec_size, 1)
        x2, y2, w2, h2 = get_img_area(vt[index_vt - 1] * enc_size, enc_size, 1)
        # print(x1, y1, w1, h1)
        # print(x2, y2, w2, h2)

        sub = dec_img.crop((x1, y1, x1 + w1, y1 + h1)).resize((w2, h2))
        enc_img.paste(sub, (x2, y2))

    return np.array(enc_img)




def get_rect_transform(filename):
    assets = UnityPy.load(filename)
    game_objects = [_.read() for _ in assets.objects if _.type.name == 'GameObject']
    face_gameobj = [_ for _ in game_objects if _.m_Name == 'face'][0]
    face_rect = face_gameobj.read().m_Component[0].component.read()
    base_rect = face_rect.read().m_Father.read()

    print('[INFO] Face GameObject PathID:', face_gameobj.path_id)
    print('[INFO] Face RectTransform PathID:', face_rect.path_id)
    print('[INFO] Base RectTransform PathID:', base_rect.path_id)

    base = convert(base_rect)
    face = convert(face_rect)

    print('[INFO] Face RectTransform data:')
    pprint(base)
    print('[INFO] Base RectTransform data:')
    pprint(face)

    base_pivot = base['m_SizeDelta'] * base['m_Pivot']
    face_pivot = base_pivot + face['m_LocalPosition'][:2]
    face_offset = face_pivot - face['m_SizeDelta'] * face['m_Pivot']

    x, y = np.round(face_offset).astype(np.int32)
    w, h = face['m_SizeDelta'].astype(np.int32)

    print('[INFO] Paintingface area:', x, y, w, h)

    return base, face, x, y, w, h
