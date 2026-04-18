from __future__ import annotations
import requests
import copy
import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# 火山方舟（Ark）配置：
# 1) 推荐把真实 API Key 配到系统环境变量 ARK_API_KEY 中
# 2) 如需切换模型，可修改 ARK_MODEL（也可填 Endpoint ID）
# 3) 保留旧的 DEEPSEEK_* 环境变量兼容，方便从上一个版本平滑迁移
ARK_API_KEY = os.getenv("ARK_API_KEY") or os.getenv("DEEPSEEK_API_KEY") or ""
ARK_MODEL = os.getenv("ARK_MODEL") or os.getenv("ARK_ENDPOINT_ID") or os.getenv("DEEPSEEK_MODEL") or "deepseek-v3-2-251201"
ARK_MODEL_LABEL = ""
ARK_API_URL = os.getenv("ARK_API_URL") or os.getenv("DEEPSEEK_API_URL") or "https://ark.cn-beijing.volces.com/api/v3/chat/completions"


def is_placeholder_api_key(value: str) -> bool:
    value = (value or "").strip()
    if not value:
        return True
    return value in {
        "你的火山方舟API Key",
        "请替换为你的火山方舟API Key",
        "your_ark_api_key",
        "YOUR_ARK_API_KEY",
    }

COLOR_MAP = {
    "红色": "#d64545", "蓝色": "#4a7dff", "绿色": "#4caf50", "黄色": "#f1c40f",
    "白色": "#f5f5f5", "黑色": "#222222", "灰色": "#8e8e8e", "棕色": "#8b5a2b",
    "米色": "#d8c3a5", "橙色": "#f39c12", "紫色": "#8e44ad", "木色": "#c49a6c",
    "粉色": "#f0bfd6", "青色": "#4db6ac",
}

MATERIAL_OPTIONS = [
    "木纹", "布艺", "皮质", "绒面", "金属", "石材", "白色瓷砖", "大理石",
    "原木风", "玻璃", "烤漆", "混凝土", "陶瓷"
]
WALLS = ["top", "right", "bottom", "left"]
WALL_LABELS = {"top": "上墙", "right": "右墙", "bottom": "下墙", "left": "左墙"}
OPENING_TYPE_LABELS = {"door": "门", "window": "窗"}
ROOM_TYPE_OPTIONS = ["卧室", "浴室", "客厅", "饭厅", "厨房", "阳台"]

FURNITURE_DEFAULTS: Dict[str, Dict] = {
    "sofa": {
        "label": "沙发", "width": 1.8, "depth": 0.85, "height": 0.82,
        "color": "#6f7d8c", "material": "布艺", "category": "客厅", "group": "休闲家具",
        "icon": "🛋️", "tags": ["客厅", "主件", "舒适"], "score": "高人气"
    },
    "armchair": {
        "label": "单人椅", "width": 0.85, "depth": 0.78, "height": 0.82,
        "color": "#8d7b68", "material": "布艺", "category": "客厅", "group": "坐具家具",
        "icon": "🪑", "tags": ["客厅", "阅读", "单座"], "score": "高搭配"
    },
    "tv": {
        "label": "电视柜", "width": 1.4, "depth": 0.36, "height": 0.68,
        "color": "#2b3038", "material": "木纹", "category": "客厅", "group": "电器摆件",
        "icon": "📺", "tags": ["客厅", "电视", "低柜"], "score": "常用"
    },
    "coffee_table": {
        "label": "茶几", "width": 1.05, "depth": 0.6, "height": 0.45,
        "color": "#b58b62", "material": "木纹", "category": "客厅", "group": "桌几家具",
        "icon": "☕", "tags": ["客厅", "中心位", "小桌"], "score": "热销"
    },
    "sideboard": {
        "label": "边柜", "width": 1.2, "depth": 0.45, "height": 0.82,
        "color": "#c49a6c", "material": "木纹", "category": "客厅", "group": "收纳家具",
        "icon": "🗄️", "tags": ["客厅", "收纳", "靠墙"], "score": "推荐"
    },
    "bed": {
        "label": "床", "width": 2.0, "depth": 1.8, "height": 0.62,
        "color": "#d9d0c7", "material": "布艺", "category": "卧室", "group": "睡眠家具",
        "icon": "🛏️", "tags": ["卧室", "主件", "双人"], "score": "高人气"
    },
    "wardrobe": {
        "label": "衣柜", "width": 1.6, "depth": 0.62, "height": 2.1,
        "color": "#c49a6c", "material": "木纹", "category": "卧室", "group": "收纳家具",
        "icon": "🚪", "tags": ["卧室", "高柜", "收纳"], "score": "常用"
    },
    "nightstand": {
        "label": "床头柜", "width": 0.48, "depth": 0.42, "height": 0.56,
        "color": "#c19b73", "material": "木纹", "category": "卧室", "group": "收纳家具",
        "icon": "🧺", "tags": ["卧室", "边几", "小件"], "score": "搭配"
    },
    "bookshelf": {
        "label": "书架", "width": 1.0, "depth": 0.32, "height": 1.9,
        "color": "#9f7f56", "material": "木纹", "category": "卧室", "group": "收纳家具",
        "icon": "📚", "tags": ["卧室", "书房", "靠墙"], "score": "推荐"
    },
    "desk": {
        "label": "书桌", "width": 1.2, "depth": 0.6, "height": 0.75,
        "color": "#b8956a", "material": "木纹", "category": "卧室", "group": "桌几家具",
        "icon": "🧑‍💻", "tags": ["学习", "办公", "桌面"], "score": "常用"
    },
    "dining_table": {
        "label": "餐桌", "width": 1.4, "depth": 0.82, "height": 0.75,
        "color": "#d5b48c", "material": "木纹", "category": "餐厅", "group": "桌几家具",
        "icon": "🍽️", "tags": ["餐厅", "主件", "四人"], "score": "高人气"
    },
    "dining_chair": {
        "label": "餐椅", "width": 0.5, "depth": 0.5, "height": 0.9,
        "color": "#777777", "material": "布艺", "category": "餐厅", "group": "坐具家具",
        "icon": "🪑", "tags": ["餐厅", "坐具", "搭配"], "score": "常用"
    },
    "kitchen_counter": {
        "label": "橱柜台面", "width": 1.6, "depth": 0.6, "height": 0.92,
        "color": "#d7d7d7", "material": "大理石", "category": "厨房", "group": "厨卫家具",
        "icon": "🍳", "tags": ["厨房", "靠墙", "台面"], "score": "推荐"
    },
    "sink": {
        "label": "洗手台", "width": 0.9, "depth": 0.55, "height": 0.86,
        "color": "#eef2f6", "material": "陶瓷", "category": "卫浴", "group": "厨卫家具",
        "icon": "🚰", "tags": ["卫浴", "洗漱", "靠墙"], "score": "高频"
    },
    "toilet": {
        "label": "马桶", "width": 0.72, "depth": 0.72, "height": 0.82,
        "color": "#f7f7f7", "material": "陶瓷", "category": "卫浴", "group": "厨卫家具",
        "icon": "🚽", "tags": ["卫浴", "固定", "洁具"], "score": "高频"
    },
    "bathtub": {
        "label": "浴缸", "width": 1.6, "depth": 0.78, "height": 0.58,
        "color": "#ffffff", "material": "陶瓷", "category": "卫浴", "group": "厨卫家具",
        "icon": "🛁", "tags": ["卫浴", "大件", "靠墙"], "score": "展示"
    },
    "potted_plant": {
        "label": "绿植", "width": 0.7, "depth": 0.7, "height": 1.0,
        "color": "#4caf50", "material": "原木风", "category": "装饰", "group": "绿植装饰",
        "icon": "🪴", "tags": ["装饰", "绿植", "点缀"], "score": "推荐"
    },
    "flower_pot": {
        "label": "花盆", "width": 0.5, "depth": 0.5, "height": 0.62,
        "color": "#f06292", "material": "陶瓷", "category": "装饰", "group": "绿植装饰",
        "icon": "🌸", "tags": ["装饰", "花艺", "小件"], "score": "精致"
    },
    "indoor_tree": {
        "label": "室内树", "width": 1.0, "depth": 1.0, "height": 1.8,
        "color": "#2e7d32", "material": "原木风", "category": "装饰", "group": "绿植装饰",
        "icon": "🌳", "tags": ["装饰", "大株", "景观"], "score": "展示"
    },
}

FURNITURE_GROUPS = {k: v["group"] for k, v in FURNITURE_DEFAULTS.items()}
FURNITURE_ALIASES = {
    "沙发": "sofa", "单人椅": "armchair", "电视": "tv", "电视柜": "tv", "茶几": "coffee_table",
    "边柜": "sideboard", "衣柜": "wardrobe", "餐桌": "dining_table", "餐椅": "dining_chair",
    "床": "bed", "书桌": "desk", "床头柜": "nightstand", "书架": "bookshelf", "橱柜": "kitchen_counter",
    "台面": "kitchen_counter", "洗手台": "sink", "洗漱台": "sink", "马桶": "toilet", "浴缸": "bathtub",
    "绿植": "potted_plant", "盆栽": "potted_plant", "花草": "flower_pot", "花": "flower_pot", "树": "indoor_tree", "树木": "indoor_tree",
}


@dataclass
class Room:
    id: str
    name: str
    x: float
    y: float
    width: float
    depth: float
    height: float = 3.0
    wall_color: str = "#f0efe9"
    wall_material: str = "白色瓷砖"


@dataclass
class Furniture:
    id: str
    type: str
    label: str
    room_id: str
    x: float
    y: float
    z: float
    width: float
    depth: float
    height: float
    rotation: float
    color: str
    material: str


@dataclass
class Opening:
    id: str
    type: str
    name: str
    room_id: str
    wall: str
    offset: float
    width: float
    height: float
    sill: float
    color: str
    material: str


class GameState:
    def __init__(self) -> None:
        self.grid_size_m = 0.5
        self.show_grid = True
        self.message = "欢迎来到装修小游戏工作台 "
        self.rooms: List[Room] = [
            Room("room_1", "客厅", 0.0, 0.0, 4.8, 4.0, wall_material="原木风", wall_color="#ede6d8"),
            Room("room_2", "饭厅", 4.8, 0.0, 3.0, 3.0, wall_material="白色瓷砖", wall_color="#f7f4ee"),
            Room("room_3", "卧室", 0.0, 4.0, 3.8, 3.4, wall_material="木纹", wall_color="#efe7da"),
            Room("room_4", "阳台", 3.8, 4.0, 2.6, 1.8, wall_material="白色瓷砖", wall_color="#eef3ea"),
        ]
        self.furnitures: List[Furniture] = []
        self.openings: List[Opening] = [
            Opening("opening_1", "door", "客厅门", "room_1", "left", 1.2, 1.0, 2.1, 0.0, "#8b6a4d", "木纹"),
            Opening("opening_2", "window", "客厅窗", "room_1", "top", 1.4, 1.6, 1.5, 0.9, "#79bdf8", "玻璃"),
            Opening("opening_3", "door", "饭厅门", "room_2", "right", 1.2, 0.9, 2.1, 0.0, "#8b6a4d", "木纹"),
        ]
        self.history: List[Dict] = []
        self.future: List[Dict] = []

    def snapshot(self) -> Dict:
        return {
            "rooms": [asdict(r) for r in self.rooms],
            "furnitures": [asdict(f) for f in self.furnitures],
            "openings": [asdict(o) for o in self.openings],
            "grid_size_m": self.grid_size_m,
            "show_grid": self.show_grid,
            "message": self.message,
        }

    def restore(self, snapshot: Dict) -> None:
        self.rooms = [Room(**r) for r in snapshot["rooms"]]
        self.furnitures = [Furniture(**f) for f in snapshot["furnitures"]]
        self.openings = [Opening(**o) for o in snapshot["openings"]]
        self.grid_size_m = snapshot["grid_size_m"]
        self.show_grid = snapshot["show_grid"]
        self.message = snapshot["message"]

    def push_history(self) -> None:
        self.history.append(copy.deepcopy(self.snapshot()))
        self.future.clear()
        if len(self.history) > 80:
            self.history = self.history[-80:]

    def undo(self) -> str:
        if not self.history:
            self.message = "没有可撤销的操作 "
            return self.message
        self.future.append(copy.deepcopy(self.snapshot()))
        self.restore(self.history.pop())
        self.message = "已撤销上一步 "
        return self.message

    def redo(self) -> str:
        if not self.future:
            self.message = "没有可重做的操作 "
            return self.message
        self.history.append(copy.deepcopy(self.snapshot()))
        self.restore(self.future.pop())
        self.message = "已恢复刚才撤销的操作 "
        return self.message

    def to_dict(self) -> Dict:
        return {
            **self.snapshot(),
            "options": {
                "walls": [{"value": key, "label": WALL_LABELS[key]} for key in WALLS],
                "opening_types": [{"value": k, "label": v} for k, v in OPENING_TYPE_LABELS.items()],
                "room_materials": MATERIAL_OPTIONS,
                "furniture_catalog": [
                    {
                        "value": ftype,
                        "label": meta["label"],
                        "category": meta["category"],
                        "group": meta["group"],
                        "width": meta["width"],
                        "depth": meta["depth"],
                        "height": meta["height"],
                        "color": meta["color"],
                        "material": meta["material"],
                        "icon": meta.get("icon", "🧩"),
                        "tags": meta.get("tags", []),
                        "score": meta.get("score", "基础"),
                    }
                    for ftype, meta in FURNITURE_DEFAULTS.items()
                ],
                "room_types": ROOM_TYPE_OPTIONS,
                "rooms": [{"id": r.id, "name": r.name} for r in self.rooms],
                "history": {"can_undo": bool(self.history), "can_redo": bool(self.future)},
            }
        }


STATE = GameState()


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def normalize_rotation(value: float) -> float:
    return value % 360


def next_id(prefix: str, items: List) -> str:
    used = {obj.id for obj in items}
    i = 1
    while f"{prefix}_{i}" in used:
        i += 1
    return f"{prefix}_{i}"


def room_by_id(room_id: str) -> Optional[Room]:
    return next((r for r in STATE.rooms if r.id == room_id), None)


def furniture_by_id(item_id: str) -> Optional[Furniture]:
    return next((f for f in STATE.furnitures if f.id == item_id), None)


def opening_by_id(item_id: str) -> Optional[Opening]:
    return next((o for o in STATE.openings if o.id == item_id), None)


def find_room_for_point(x: float, y: float) -> Optional[Room]:
    for room in reversed(STATE.rooms):
        if room.x <= x <= room.x + room.width and room.y <= y <= room.y + room.depth:
            return room
    return None


def get_furniture_footprint(item: Furniture) -> tuple[float, float]:
    rot = int(item.rotation) % 180
    return (item.depth, item.width) if rot == 90 else (item.width, item.depth)


def clamp_furniture_inside_room(item: Furniture) -> None:
    room = room_by_id(item.room_id)
    if not room:
        return
    fw, fd = get_furniture_footprint(item)
    item.x = clamp(item.x, room.x + 0.05, room.x + room.width - fw - 0.05)
    item.y = clamp(item.y, room.y + 0.05, room.y + room.depth - fd - 0.05)


def collides(item: Furniture) -> bool:
    fw, fd = get_furniture_footprint(item)
    for other in STATE.furnitures:
        if other.id == item.id or other.room_id != item.room_id:
            continue
        ow, od = get_furniture_footprint(other)
        if not (item.x + fw <= other.x or other.x + ow <= item.x or item.y + fd <= other.y or other.y + od <= item.y):
            return True
    return False


def snap_furniture(item: Furniture) -> None:
    room = room_by_id(item.room_id)
    if not room:
        return

    fw, fd = get_furniture_footprint(item)
    threshold = 0.22

    left = room.x + 0.05
    right = room.x + room.width - fw - 0.05
    top = room.y + 0.05
    bottom = room.y + room.depth - fd - 0.05
    center_x = room.x + (room.width - fw) / 2
    center_y = room.y + (room.depth - fd) / 2

    if abs(item.x - left) <= threshold:
        item.x = left
    if abs(item.x - right) <= threshold:
        item.x = right
    if abs(item.y - top) <= threshold:
        item.y = top
    if abs(item.y - bottom) <= threshold:
        item.y = bottom
    if abs(item.x - center_x) <= threshold:
        item.x = center_x
    if abs(item.y - center_y) <= threshold:
        item.y = center_y

    for other in STATE.furnitures:
        if other.id == item.id or other.room_id != item.room_id:
            continue
        ow, od = get_furniture_footprint(other)
        candidates_x = [other.x, other.x + ow, other.x + (ow - fw) / 2]
        candidates_y = [other.y, other.y + od, other.y + (od - fd) / 2]
        for candidate in candidates_x:
            if abs(item.x - candidate) <= threshold:
                item.x = candidate
        for candidate in candidates_y:
            if abs(item.y - candidate) <= threshold:
                item.y = candidate

    clamp_furniture_inside_room(item)


def opening_default_name(opening_type: str, room: Room, idx: int | None = None) -> str:
    suffix = f"{idx}" if idx is not None else ""
    base = "门" if opening_type == "door" else "窗"
    return f"{room.name}{base}{suffix}"


def clamp_opening(opening: Opening) -> None:
    room = room_by_id(opening.room_id)
    if not room:
        return
    wall_len = room.width if opening.wall in {"top", "bottom"} else room.depth
    opening.width = clamp(opening.width, 0.5, max(0.5, wall_len - 0.1))
    opening.offset = clamp(opening.offset, 0.0, max(0.0, wall_len - opening.width))


def add_furniture(
    room: Room,
    ftype: str,
    x: Optional[float] = None,
    y: Optional[float] = None,
    color: Optional[str] = None,
    material: Optional[str] = None,
    width: Optional[float] = None,
    depth: Optional[float] = None,
    rotation: float = 0.0,
    label: Optional[str] = None,
) -> tuple[bool, str, Optional[Furniture]]:
    if ftype not in FURNITURE_DEFAULTS:
        return False, "家具类型不存在 ", None

    meta = FURNITURE_DEFAULTS[ftype]
    item = Furniture(
        id=next_id("furniture", STATE.furnitures),
        type=ftype,
        label=label or meta["label"],
        room_id=room.id,
        x=x if x is not None else room.x + 0.3,
        y=y if y is not None else room.y + 0.3,
        z=0.0,
        width=clamp(float(width or meta["width"]), 0.25, 5.0),
        depth=clamp(float(depth or meta["depth"]), 0.25, 5.0),
        height=meta["height"],
        rotation=normalize_rotation(rotation),
        color=color or meta["color"],
        material=material or meta["material"],
    )

    clamp_furniture_inside_room(item)
    snap_furniture(item)
    if collides(item):
        return False, f"{item.label}放置失败：与其他家具重叠 ", None

    STATE.furnitures.append(item)
    return True, f"已添加{item.label} ", item


def update_furniture(item: Furniture, payload: Dict) -> tuple[bool, str]:
    old = asdict(item)

    if "room_id" in payload and room_by_id(payload["room_id"]):
        item.room_id = payload["room_id"]

    if "type" in payload and payload["type"] in FURNITURE_DEFAULTS:
        item.type = payload["type"]
        meta = FURNITURE_DEFAULTS[item.type]
        item.height = meta["height"]
        if not payload.get("label"):
            item.label = meta["label"]
        if "material" not in payload:
            item.material = meta["material"]

    for key in ["label", "x", "y", "width", "depth", "rotation", "color", "material"]:
        if key not in payload:
            continue
        value = payload[key]
        if key in {"x", "y", "width", "depth", "rotation"}:
            value = float(value)
        setattr(item, key, value)

    item.width = clamp(item.width, 0.25, 5.0)
    item.depth = clamp(item.depth, 0.25, 5.0)
    item.rotation = normalize_rotation(item.rotation)

    fw, fd = get_furniture_footprint(item)
    center_room = find_room_for_point(item.x + fw / 2, item.y + fd / 2)
    if center_room:
        item.room_id = center_room.id

    clamp_furniture_inside_room(item)
    snap_furniture(item)

    if collides(item):
        for k, v in old.items():
            setattr(item, k, v)
        return False, f"{item.label}调整失败：与其他家具重叠 "

    return True, f"{item.label}已更新 "


def delete_furniture(item: Furniture) -> str:
    STATE.furnitures = [f for f in STATE.furnitures if f.id != item.id]
    return f"已删除{item.label} "


def update_room(room: Room, payload: Dict) -> tuple[bool, str]:
    old = asdict(room)

    for key in ["name", "x", "y", "width", "depth", "wall_color", "wall_material"]:
        if key not in payload:
            continue
        value = payload[key]
        if key in {"x", "y", "width", "depth"}:
            value = float(value)
        setattr(room, key, value)

    room.width = clamp(room.width, 1.6, 12.0)
    room.depth = clamp(room.depth, 1.6, 12.0)

    for item in STATE.furnitures:
        if item.room_id == room.id:
            clamp_furniture_inside_room(item)
            snap_furniture(item)
    for op in STATE.openings:
        if op.room_id == room.id:
            clamp_opening(op)

    for other in STATE.rooms:
        if other.id == room.id:
            continue
        if not (room.x + room.width <= other.x or other.x + other.width <= room.x or room.y + room.depth <= other.y or other.y + other.depth <= room.y):
            for k, v in old.items():
                setattr(room, k, v)
            return False, f"{room.name}调整失败：与{other.name}重叠 "

    return True, f"{room.name}已更新 "


def delete_room(room: Room) -> str:
    STATE.rooms = [r for r in STATE.rooms if r.id != room.id]
    STATE.furnitures = [f for f in STATE.furnitures if f.room_id != room.id]
    STATE.openings = [o for o in STATE.openings if o.room_id != room.id]
    return f"已删除{room.name}及其相关家具、门窗 "


def room_overlaps(room: Room) -> Optional[Room]:
    for other in STATE.rooms:
        if other.id == room.id:
            continue
        if not (room.x + room.width <= other.x or other.x + other.width <= room.x or room.y + room.depth <= other.y or other.y + other.depth <= room.y):
            return other
    return None


def find_available_room_position(width: float, depth: float, preferred_x: float, preferred_y: float) -> tuple[float, float]:
    candidates: list[tuple[float, float]] = [(preferred_x, preferred_y)]
    if STATE.rooms:
        min_x = min(r.x for r in STATE.rooms)
        min_y = min(r.y for r in STATE.rooms)
        max_x = max(r.x + r.width for r in STATE.rooms)
        max_y = max(r.y + r.depth for r in STATE.rooms)
        step = 0.6
        margin = 0.8

        scan_min_x = min(min_x - width - 2.0, preferred_x - 4.0)
        scan_max_x = max(max_x + 2.0, preferred_x + 4.0)
        scan_min_y = min(min_y - depth - 2.0, preferred_y - 4.0)
        scan_max_y = max(max_y + 2.0, preferred_y + 4.0)

        x = scan_min_x
        while x <= scan_max_x:
            y = scan_min_y
            while y <= scan_max_y:
                candidates.append((round(x, 1), round(y, 1)))
                y += step
            x += step

        for room in STATE.rooms:
            candidates.extend([
                (round(room.x + room.width + margin, 1), round(room.y, 1)),
                (round(room.x, 1), round(room.y + room.depth + margin, 1)),
                (round(room.x + room.width + margin, 1), round(room.y + room.depth + margin, 1)),
            ])

    for cx, cy in candidates:
        trial = Room("trial", "trial", cx, cy, width, depth)
        if not room_overlaps(trial):
            return cx, cy

    return preferred_x, preferred_y


def add_room(
    name: str,
    x: float,
    y: float,
    width: float,
    depth: float,
    wall_color: str = "#f0efe9",
    wall_material: str = "白色瓷砖",
) -> tuple[bool, str, Optional[Room]]:
    width = clamp(width, 1.6, 12.0)
    depth = clamp(depth, 1.6, 12.0)
    room_x, room_y = find_available_room_position(width, depth, x, y)
    room_name = name or ROOM_TYPE_OPTIONS[min(len(STATE.rooms), len(ROOM_TYPE_OPTIONS) - 1)]
    room = Room(next_id("room", STATE.rooms), room_name, room_x, room_y, width, depth, wall_color=wall_color, wall_material=wall_material)

    overlap = room_overlaps(room)
    if overlap:
        return False, f"新增房间失败：与{overlap.name}重叠 ", None

    STATE.rooms.append(room)
    if room_x != x or room_y != y:
        return True, f"已添加{room.name}，并自动避让到空位置 ", room
    return True, f"已添加{room.name} ", room


def add_opening(room: Room, opening_type: str, wall: str, offset: float, width: float, name: Optional[str] = None) -> tuple[bool, str, Optional[Opening]]:
    if opening_type not in OPENING_TYPE_LABELS or wall not in WALLS:
        return False, "门窗参数不正确 ", None

    same_type_count = len([o for o in STATE.openings if o.type == opening_type and o.room_id == room.id]) + 1
    opening = Opening(
        id=next_id("opening", STATE.openings),
        type=opening_type,
        name=name or opening_default_name(opening_type, room, same_type_count),
        room_id=room.id,
        wall=wall,
        offset=float(offset),
        width=float(width),
        height=1.5 if opening_type == "window" else 2.1,
        sill=0.9 if opening_type == "window" else 0.0,
        color="#79bdf8" if opening_type == "window" else "#8b6a4d",
        material="玻璃" if opening_type == "window" else "木纹",
    )

    clamp_opening(opening)
    STATE.openings.append(opening)
    return True, f"已为{room.name}添加{OPENING_TYPE_LABELS[opening_type]} ", opening


def update_opening(opening: Opening, payload: Dict) -> tuple[bool, str]:
    if "room_id" in payload and room_by_id(payload["room_id"]):
        opening.room_id = payload["room_id"]

    if "wall" in payload and payload["wall"] in WALLS:
        opening.wall = payload["wall"]

    if "type" in payload and payload["type"] in OPENING_TYPE_LABELS:
        opening.type = payload["type"]
        opening.height = 1.5 if opening.type == "window" else 2.1
        opening.sill = 0.9 if opening.type == "window" else 0.0
        opening.color = "#79bdf8" if opening.type == "window" else "#8b6a4d"
        opening.material = "玻璃" if opening.type == "window" else "木纹"

    for key in ["name", "offset", "width"]:
        if key in payload:
            value = payload[key]
            if key in {"offset", "width"}:
                value = float(value)
            setattr(opening, key, value)

    clamp_opening(opening)
    return True, f"已更新{opening.name or OPENING_TYPE_LABELS[opening.type]} "


def delete_opening(opening: Opening) -> str:
    STATE.openings = [o for o in STATE.openings if o.id != opening.id]
    return f"已删除{opening.name or OPENING_TYPE_LABELS[opening.type]} "


def parse_distance(text: str, default: float = 0.9) -> float:
    m = re.search(r"(\d+(?:\.\d+)?)\s*米", text)
    return float(m.group(1)) if m else default


def detect_color(text: str) -> Optional[str]:
    for cn, hex_color in COLOR_MAP.items():
        if cn in text:
            return hex_color
    return None


def detect_room(text: str) -> Optional[Room]:
    for room in STATE.rooms:
        if room.name in text or room.id in text:
            return room
    return None


def detect_furniture_type(text: str) -> Optional[str]:
    for cn, ftype in FURNITURE_ALIASES.items():
        if cn in text:
            return ftype
    return None


def call_ark_chat_json(system_prompt: str, user_prompt: str, max_tokens: int = 260) -> Dict:
    if is_placeholder_api_key(ARK_API_KEY):
        raise RuntimeError(
            "未配置火山方舟 API Key 请先在火山方舟控制台的“API Key 管理”创建 Key，"
            "再把它写入环境变量 ARK_API_KEY，或直接修改 app.py 顶部的 ARK_API_KEY 配置 "
        )

    payload = {
        "model": ARK_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.1,
        "max_tokens": max_tokens,
        "stream": False,
        "response_format": {"type": "json_object"},
    }

    req = urllib.request.Request(
        ARK_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {ARK_API_KEY}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        if exc.code == 401:
            raise RuntimeError(
                "HTTP 401：火山方舟鉴权失败 请检查 ARK_API_KEY 是否为“API Key 管理”页面新建的有效 Key "
                + (f" 服务端返回：{detail}" if detail else "")
            ) from exc
        if exc.code == 404:
            raise RuntimeError(
                "HTTP 404：火山方舟接口地址或模型标识不正确 请检查 ARK_API_URL 与 ARK_MODEL（或 ARK_ENDPOINT_ID） "
                + (f" 服务端返回：{detail}" if detail else "")
            ) from exc
        raise RuntimeError(f"HTTP {exc.code}：{detail or '火山方舟接口调用失败 '}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"网络连接失败：{exc.reason}") from exc

    try:
        result = json.loads(raw)
        content = result["choices"][0]["message"]["content"]
        return json.loads(content)
    except Exception as exc:
        raise RuntimeError(f"模型返回结果解析失败：{raw[:400]}") from exc


def normalize_voice_command_with_llm(transcript: str) -> Dict:
    room_names = "、".join(room.name for room in STATE.rooms) or "无"
    furniture_names = "、".join(sorted(set(meta["label"] for meta in FURNITURE_DEFAULTS.values())))
    color_names = "、".join(COLOR_MAP.keys())

    system_prompt = f"""
你是装修模拟小游戏的语音指令归一化助手 
你的任务是把“语音转文字结果”纠错、补全并改写成这个小游戏可执行的一句中文指令 

当前房间：{room_names}
可识别家具：{furniture_names}
可识别颜色：{color_names}

你只能输出 JSON 对象，格式固定为：
{{
  "command": "可执行的单句中文指令；如果无法确定则输出空字符串",
  "reason": "一句简短说明",
  "confidence": "high 或 medium 或 low"
}}

优先输出下列形式之一：
1. 给{{房间名}}添加{{家具名}}
2. 给{{房间名}}{{左墙/右墙/上墙/下墙}}添加门
3. 给{{房间名}}添加窗
4. 添加房间
5. 撤销
6. 重做
7. 显示网格
8. 隐藏网格
9. 删除{{家具名}}
10. 删除{{房间名}}的{{家具名}}
11. 把{{家具名}}改成{{颜色名}}
12. 把{{房间名}}宽度改为{{数字}}米
13. 把{{房间名}}深度改为{{数字}}米

规则：
- 允许纠正明显口误、同音字、ASR 误识别 
- 只保留一条最核心、最可执行的命令 
- 如果内容不明确、超出能力范围或不是装修操作，command 置空 
- 不要输出 markdown，不要输出多余解释 
""".strip()

    user_prompt = f"语音转文字结果：{transcript}"
    return call_ark_chat_json(system_prompt, user_prompt)


def apply_command(text: str) -> str:
    text = text.strip()
    if not text:
        return "请输入指令 "

    if "撤销" in text:
        return STATE.undo()
    if "重做" in text or "恢复" in text:
        return STATE.redo()

    if "网格" in text and any(w in text for w in ["显示", "开启"]):
        STATE.show_grid = True
        return "已显示网格 "

    if "网格" in text and any(w in text for w in ["隐藏", "关闭"]):
        STATE.show_grid = False
        return "已隐藏网格 "

    room = detect_room(text)
    ftype = detect_furniture_type(text)
    color = detect_color(text)

    if "添加房间" in text or ("新增" in text and "房间" in text):
        width = parse_distance(text, 3.0)
        all_nums = re.findall(r"(\d+(?:\.\d+)?)\s*米", text)
        depth = float(all_nums[1]) if len(all_nums) > 1 else width
        ok, msg, _ = add_room(f"房间{len(STATE.rooms)+1}", 0.5 + len(STATE.rooms) * 0.6, 0.5 + len(STATE.rooms) * 0.6, width, depth)
        return msg if ok else msg

    if room and ("添加门" in text or "添加窗" in text):
        wall = "top"
        if "左墙" in text:
            wall = "left"
        elif "右墙" in text:
            wall = "right"
        elif "下墙" in text:
            wall = "bottom"
        opening_type = "window" if "窗" in text else "door"
        ok, msg, _ = add_opening(room, opening_type, wall, 0.4, parse_distance(text, 1.2 if opening_type == "window" else 0.9))
        return msg if ok else msg

    if room and ftype and any(w in text for w in ["添加", "放置", "放一个"]):
        ok, msg, _ = add_furniture(room, ftype, color=color)
        return msg if ok else msg

    if room and any(w in text for w in ["宽度", "进深", "深度"]):
        width_m = re.search(r"宽度(?:改为|到|至)?\s*(\d+(?:\.\d+)?)\s*米", text)
        depth_m = re.search(r"(?:进深|深度)(?:改为|到|至)?\s*(\d+(?:\.\d+)?)\s*米", text)
        payload = {}
        if width_m:
            payload["width"] = float(width_m.group(1))
        if depth_m:
            payload["depth"] = float(depth_m.group(1))
        if color:
            payload["wall_color"] = color
        if payload:
            ok, msg = update_room(room, payload)
            return msg if ok else msg

    if ftype and any(w in text for w in ["删除", "移除"]):
        if room:
            # 删除指定房间的家具
            item = next((f for f in STATE.furnitures if f.type == ftype and f.room_id == room.id), None)
            if item:
                return delete_furniture(item)
            else:
                return f"{room.name}的{ftype}不存在 "
        else:
            # 没有指定房间，保持原有逻辑
            item = next((f for f in STATE.furnitures if f.type == ftype), None)
            if item:
                return delete_furniture(item)
            else:
                return f"{ftype}不存在 "

    if ftype and color:
        if room:
            # 修改指定房间的家具颜色
            item = next((f for f in STATE.furnitures if f.type == ftype and f.room_id == room.id), None)
            if item:
                ok, msg = update_furniture(item, {"color": color})
                return msg if ok else msg
            else:
                return f"{room.name}的{ftype}不存在 "
        else:
            # 没有指定房间，保持原有逻辑
            item = next((f for f in STATE.furnitures if f.type == ftype), None)
            if item:
                ok, msg = update_furniture(item, {"color": color})
                return msg if ok else msg
            else:
                return f"{ftype}不存在 "

    return "暂未识别该指令 可尝试：给客厅添加沙发、给客厅左墙添加门、给卧室添加窗、添加房间、删除客厅的沙发 "


@app.route("/")
def index():
    return render_template("index.html")



@app.route("/api/state")
def api_state():
    return jsonify(STATE.to_dict())


@app.route("/api/voice-command", methods=["POST"])
def api_voice_command():
    payload = request.get_json(silent=True) or {}
    transcript = str(payload.get("transcript", "")).strip()
    if not transcript:
        return jsonify({"ok": False, "message": "未接收到语音转文字内容 ", "state": STATE.to_dict()}), 400

    try:
        llm_result = normalize_voice_command_with_llm(transcript)
    except Exception as exc:
        msg = f"{ARK_MODEL_LABEL} 指令解析失败：{exc}"
        STATE.message = msg
        return jsonify({
            "ok": False,
            "message": msg,
            "transcript": transcript,
            "state": STATE.to_dict(),
        }), 500

    normalized_command = str(llm_result.get("command", "")).strip()
    llm_reason = str(llm_result.get("reason", "")).strip()
    llm_confidence = str(llm_result.get("confidence", "")).strip() or "unknown"

    if not normalized_command:
        msg = f"语音已识别，但 {ARK_MODEL_LABEL} 暂未判断出可执行指令 {(' 原因：' + llm_reason) if llm_reason else ''}"
        STATE.message = msg
        return jsonify({
            "ok": False,
            "message": msg,
            "transcript": transcript,
            "llm_reason": llm_reason,
            "llm_confidence": llm_confidence,
            "state": STATE.to_dict(),
        })

    if "撤销" not in normalized_command and "重做" not in normalized_command and "恢复" not in normalized_command:
        STATE.push_history()

    STATE.message = apply_command(normalized_command)
    return jsonify({
        "ok": True,
        "message": STATE.message,
        "transcript": transcript,
        "llm_command": normalized_command,
        "llm_reason": llm_reason,
        "llm_confidence": llm_confidence,
        "state": STATE.to_dict(),
    })



@app.route("/api/command", methods=["POST"])
def api_command():
    payload = request.get_json(silent=True) or {}
    text = str(payload.get("command", "")).strip()
    if text and ("撤销" not in text and "重做" not in text and "恢复" not in text):
        STATE.push_history()
    STATE.message = apply_command(text)
    return jsonify(STATE.to_dict())


@app.route("/api/undo", methods=["POST"])
def api_undo():
    STATE.undo()
    return jsonify({"ok": True, "message": "已撤销上一步操作", "state": STATE.to_dict()})


@app.route("/api/redo", methods=["POST"])
def api_redo():
    STATE.redo()
    return jsonify({"ok": True, "message": "已重做上一步操作", "state": STATE.to_dict()})


@app.route("/api/import", methods=["POST"])
def api_import():
    try:
        payload = request.get_json(silent=True)
        if not payload:
            return jsonify({"ok": False, "message": "无效的配置文件"}), 400
        
        # 保存历史记录
        STATE.push_history()
        
        # 清空当前状态
        STATE.rooms = []
        STATE.furnitures = []
        STATE.openings = []
        
        # 导入房间
        if "rooms" in payload:
            for room_data in payload["rooms"]:
                room = Room(
                    id=room_data.get("id"),
                    name=room_data.get("name", "房间"),
                    x=room_data.get("x", 0),
                    y=room_data.get("y", 0),
                    width=room_data.get("width", 3),
                    depth=room_data.get("depth", 3),
                    wall_color=room_data.get("wall_color", "#f0efe9"),
                    wall_material=room_data.get("wall_material", "白色瓷砖")
                )
                STATE.rooms.append(room)
        
        # 导入家具
        if "furnitures" in payload:
            for furniture_data in payload["furnitures"]:
                furniture = Furniture(
                    id=furniture_data.get("id"),
                    type=furniture_data.get("type", "sofa"),
                    label=furniture_data.get("label", "家具"),
                    room_id=furniture_data.get("room_id"),
                    x=furniture_data.get("x", 0),
                    y=furniture_data.get("y", 0),
                    z=furniture_data.get("z", 0),
                    width=furniture_data.get("width", 1),
                    depth=furniture_data.get("depth", 1),
                    height=furniture_data.get("height", 0.8),
                    rotation=furniture_data.get("rotation", 0),
                    color=furniture_data.get("color", "#6f7d8c"),
                    material=furniture_data.get("material", "布艺")
                )
                STATE.furnitures.append(furniture)
        
        # 导入门窗
        if "openings" in payload:
            for opening_data in payload["openings"]:
                opening = Opening(
                    id=opening_data.get("id"),
                    type=opening_data.get("type", "door"),
                    name=opening_data.get("name", "门窗"),
                    room_id=opening_data.get("room_id"),
                    wall=opening_data.get("wall", "top"),
                    offset=opening_data.get("offset", 0),
                    width=opening_data.get("width", 1),
                    height=opening_data.get("height", 2.1),
                    sill=opening_data.get("sill", 0),
                    color=opening_data.get("color", "#8b6a4d"),
                    material=opening_data.get("material", "木纹")
                )
                STATE.openings.append(opening)
        
        # 导入其他设置
        if "show_grid" in payload:
            STATE.show_grid = payload["show_grid"]
        
        # 清空历史记录，避免状态错乱
        STATE.history.clear()
        STATE.future.clear()
        
        return jsonify({"ok": True, "message": "配置文件导入成功", "state": STATE.to_dict()})
    except Exception as e:
        return jsonify({"ok": False, "message": f"导入失败: {str(e)}"}), 500


@app.route("/api/furniture", methods=["POST"])
def api_add_furniture():
    payload = request.get_json(silent=True) or {}
    room = room_by_id(payload.get("room_id"))
    if not room and payload.get("x") is not None and payload.get("y") is not None:
        room = find_room_for_point(float(payload["x"]), float(payload["y"]))
    if not room:
        return jsonify({"ok": False, "message": "请选择一个放置房间 "}), 400

    STATE.push_history()
    ok, msg, item = add_furniture(
        room,
        payload.get("type"),
        payload.get("x"),
        payload.get("y"),
        payload.get("color"),
        payload.get("material"),
        payload.get("width"),
        payload.get("depth"),
        float(payload.get("rotation", 0)),
        payload.get("label"),
    )
    STATE.message = msg
    return jsonify({"ok": ok, "message": msg, "item": asdict(item) if item else None, "state": STATE.to_dict()})


@app.route("/api/furniture/<item_id>", methods=["PATCH"])
def api_update_furniture(item_id: str):
    item = furniture_by_id(item_id)
    if not item:
        return jsonify({"ok": False, "message": "家具不存在 "}), 404

    STATE.push_history()
    ok, msg = update_furniture(item, request.get_json(silent=True) or {})
    STATE.message = msg
    return jsonify({"ok": ok, "message": msg, "item": asdict(item), "state": STATE.to_dict()})


@app.route("/api/furniture/<item_id>", methods=["DELETE"])
def api_delete_furniture(item_id: str):
    item = furniture_by_id(item_id)
    if not item:
        return jsonify({"ok": False, "message": "家具不存在 "}), 404

    STATE.push_history()
    msg = delete_furniture(item)
    STATE.message = msg
    return jsonify({"ok": True, "message": msg, "state": STATE.to_dict()})


@app.route("/api/room", methods=["POST"])
def api_add_room():
    payload = request.get_json(silent=True) or {}
    STATE.push_history()
    ok, msg, room = add_room(
        payload.get("name", ROOM_TYPE_OPTIONS[min(len(STATE.rooms), len(ROOM_TYPE_OPTIONS)-1)]),
        float(payload.get("x", 0)),
        float(payload.get("y", 0)),
        float(payload.get("width", 3.0)),
        float(payload.get("depth", 3.0)),
        payload.get("wall_color", "#f0efe9"),
        payload.get("wall_material", "白色瓷砖"),
    )
    STATE.message = msg
    return jsonify({"ok": ok, "message": msg, "room": asdict(room) if room else None, "state": STATE.to_dict()})


@app.route("/api/room/<room_id>", methods=["PATCH"])
def api_update_room(room_id: str):
    room = room_by_id(room_id)
    if not room:
        return jsonify({"ok": False, "message": "房间不存在 "}), 404

    STATE.push_history()
    ok, msg = update_room(room, request.get_json(silent=True) or {})
    STATE.message = msg
    return jsonify({"ok": ok, "message": msg, "room": asdict(room), "state": STATE.to_dict()})


@app.route("/api/room/<room_id>", methods=["DELETE"])
def api_delete_room(room_id: str):
    room = room_by_id(room_id)
    if not room:
        return jsonify({"ok": False, "message": "房间不存在 "}), 404

    STATE.push_history()
    msg = delete_room(room)
    STATE.message = msg
    return jsonify({"ok": True, "message": msg, "state": STATE.to_dict()})


@app.route("/api/opening", methods=["POST"])
def api_add_opening():
    payload = request.get_json(silent=True) or {}
    room = room_by_id(payload.get("room_id"))
    if not room:
        return jsonify({"ok": False, "message": "房间不存在 "}), 404

    STATE.push_history()
    ok, msg, opening = add_opening(
        room,
        payload.get("type", "door"),
        payload.get("wall", "top"),
        float(payload.get("offset", 0.3)),
        float(payload.get("width", 0.9)),
        payload.get("name"),
    )
    STATE.message = msg
    return jsonify({"ok": ok, "message": msg, "opening": asdict(opening) if opening else None, "state": STATE.to_dict()})


@app.route("/api/opening/<opening_id>", methods=["PATCH"])
def api_update_opening(opening_id: str):
    opening = opening_by_id(opening_id)
    if not opening:
        return jsonify({"ok": False, "message": "门窗不存在 "}), 404

    STATE.push_history()
    ok, msg = update_opening(opening, request.get_json(silent=True) or {})
    STATE.message = msg
    return jsonify({"ok": ok, "message": msg, "opening": asdict(opening), "state": STATE.to_dict()})


@app.route("/api/opening/<opening_id>", methods=["DELETE"])
def api_delete_opening(opening_id: str):
    opening = opening_by_id(opening_id)
    if not opening:
        return jsonify({"ok": False, "message": "门窗不存在 "}), 404

    STATE.push_history()
    msg = delete_opening(opening)
    STATE.message = msg
    return jsonify({"ok": True, "message": msg, "state": STATE.to_dict()})

# AI生成户型图功能实现区域开始

# 调用火山引擎文生图API的函数
def call_volcengine_image_api(params):
    print(f"调用火山引擎文生图API，模型：{params.get('model')}")
    print(f"提示词：{params.get('prompt')}")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {VOLCENGINE_API_KEY_IMAGE}"
    }
    try:
        response = requests.post(f"{VOLCENGINE_API_BASE}/images/generations", headers=headers, json=params)
        print(f"API响应状态码：{response.status_code}")
        print(f"API响应内容：{response.text}")
        return response.json()
    except Exception as e:
        print(f"API调用失败：{str(e)}")
        return {"error": str(e)}

# 生成户型图
def generate_floorplan(prompt):
    # ===================== 关键修正 =====================
    # 1. Seedream 是文生图模型，不是聊天模型！不能用 messages！
    # 2. 直接返回图片URL，彻底弃用Base64
    # ====================================================

    # 文生图专用参数（火山引擎Seedream标准格式）
    image_prompt = f"{prompt}"
    params = {
        "model": DOUBAO_SEEDREAM_MODEL,
        "prompt": image_prompt,  # 文生图只用prompt，不是messages！
        "size": "1920x1920",  # 至少3686400像素
        "response_format": "url"  # 【关键】返回URL，不用Base64
    }

    # 调用火山引擎【文生图API】（和对话API分开，别混用）
    result = call_volcengine_image_api(params)

    # 提取图片URL（文生图标准返回格式）
    if "data" in result and len(result["data"]) > 0:
        image_url = result["data"][0]["url"]
        return image_url  # 直接返回URL，干净！

    raise Exception("AI生成户型图失败，未返回图片")

# API接口：生成户型图

@app.route('/api/ai/generate_floorplan', methods=['POST'])
def api_generate_floorplan():
    data = request.json
    prompt = data.get('prompt', '')
    if not prompt:
        return jsonify({"ok": False, "message": "缺少prompt参数"})
    
    try:
        result = generate_floorplan(prompt)
        return jsonify({"ok": True, "result": result})
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)})

# AI生成户型图功能实现区域结束


# AI解析户型图功能实现区域开始
# 1. 对接火山引擎API的路由
# 2. 户型图解析功能
# 3. 与现有导入接口的集成

# 火山引擎API配置
VOLCENGINE_API_KEY_CHAT = os.getenv("VOLCENGINE_API_KEY_CHAT") or os.getenv("ARK_API_KEY") or ""
VOLCENGINE_API_KEY_IMAGE = os.getenv("VOLCENGINE_API_KEY_IMAGE") or os.getenv("ARK_API_KEY") or ""
VOLCENGINE_API_BASE = os.getenv("VOLCENGINE_API_BASE", "https://ark.cn-beijing.volces.com/api/v3")

# 这里填 Render 后台配置的模型接入点 ID（ep-开头）
DOUBAO_SEED_MODEL = os.getenv("DOUBAO_SEED_MODEL", "")
# 文生图模型接入点 ID
DOUBAO_SEEDREAM_MODEL = os.getenv("DOUBAO_SEEDREAM_MODEL", "")

# 读取外置的Prompt文件（自动处理换行、格式，永不报错！）
def load_system_prompt():
    prompt_path = os.path.join(BASE_DIR, "system_prompt.txt")
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()

# 加载Prompt
system_prompt = load_system_prompt()

# 调用火山引擎API的通用函数（添加日志）
def call_volcengine_api(model, messages, temperature=0.7):
    print(f"调用火山引擎API，模型：{model}")
    print(f"消息：{messages}")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {VOLCENGINE_API_KEY_CHAT}"
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "response_format": {"type": "json_object"}
    }
    try:
        response = requests.post(f"{VOLCENGINE_API_BASE}/chat/completions", headers=headers, json=payload)
        print(f"API响应状态码：{response.status_code}")
        print(f"API响应内容：{response.text}")
        return response.json()
    except Exception as e:
        print(f"API调用失败：{str(e)}")
        return {"error": str(e)}

# ======================
# 【已修复】解析户型图（支持Base64，无损还原）
# ======================
def parse_floorplan(image_base64):
    messages = [
        {
            "role": "system",
            "content": system_prompt
            # "content": "你是一个专业的户型图解析助手，能够从户型图中提取房间布局、尺寸、门窗位置等信息，只返回标准JSON格式，不要多余文字 JSON格式必须包含以下字段：rooms（房间列表）、openings（门窗列表）、furnitures（家具列表） 其中rooms字段包含id、name、width、depth、x、y、height、wall_color、wall_material等属性；openings字段包含id、name、type、room_id、wall、offset、width、height、sill、color、material等
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    # "text": "解析这张户型图，提取房间布局、尺寸、门窗位置和家具信息，返回标准JSON格式 "
                    "text": "解析已经转换为base64的户型图，返回标准JSON格式，只输出JSON，不要多余文字 "
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{image_base64}"
                    }
                }
            ]
        }
    ]
    result = call_volcengine_api(DOUBAO_SEED_MODEL, messages)
    
    # 提取AI返回的内容
    if 'choices' in result and len(result['choices']) > 0:
        # 直接提取纯JSON内容
        pure_json = result["choices"][0]["message"]["content"]
        
        # 转成字典直接用
        try:
            import json
            data = json.loads(pure_json)
            
            # 写入tmp.json文件
            tmp_json_path = os.path.join(BASE_DIR, 'tmp.json')
            with open(tmp_json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            return data
        except json.JSONDecodeError:
            # 如果解析失败，返回原始内容
            return {"error": "Failed to parse AI response as JSON", "content": pure_json}
    
    return result

# ======================
# 【已修复】API接口（接收Base64图片或URL）
# ======================
@app.route('/api/ai/parse_floorplan', methods=['POST'])
def api_parse_floorplan():
    data = request.json
    image_base64 = data.get('image_base64', '')
    image_url = data.get('image_url', '')

    # 【修复】优先用URL，后端下载
    if image_url and not image_base64:
        try:
            import requests
            img_response = requests.get(image_url)
            import base64
            image_base64 = base64.b64encode(img_response.content).decode('utf-8')
        except Exception as e:
            return jsonify({"ok": False, "message": f"后端下载图片失败：{str(e)}"})

    if not image_base64:
        return jsonify({"ok": False, "message": "缺少图片参数"})
    
    try:
        # 【已修复】调用解析函数
        result = parse_floorplan(image_base64)
        return jsonify({"ok": True, "result": result})
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)})
# AI解析户型图功能实现区域结束


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
