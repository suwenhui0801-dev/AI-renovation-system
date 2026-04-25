from __future__ import annotations
import requests
import copy
import json
import os
import re
import time
import uuid
import base64
import urllib.error
import urllib.request
from io import BytesIO
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional

from flask import Flask, jsonify, render_template, request, url_for

app = Flask(__name__)

@app.errorhandler(Exception)
def handle_unexpected_error(e):
    import traceback
    traceback.print_exc()
    return jsonify({
        "ok": False,
        "message": f"服务器内部错误：{str(e)}"
    }), 500

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

GENERATED_FLOORPLAN_DIR = os.path.join(BASE_DIR, "static", "generated_floorplans")
os.makedirs(GENERATED_FLOORPLAN_DIR, exist_ok=True)

# 火山方舟（Ark）配置：
# 1) 推荐把真实 API Key 配到系统环境变量 ARK_API_KEY 中
# 2) 如需切换模型，可修改 ARK_MODEL（也可填 Endpoint ID）
# 3) 保留旧的 DEEPSEEK_* 环境变量兼容，方便从上一个版本平滑迁移
ARK_API_KEY = os.getenv("ARK_API_KEY", "")
ARK_MODEL = os.getenv("ARK_MODEL", "deepseek-v3-2-251201")
ARK_MODEL_LABEL = ARK_MODEL
ARK_API_URL = os.getenv("ARK_API_URL", "")

# ======================
# AI 模型职责绑定（全部使用 Render 环境变量里的 model ID）
# ======================
# 普通语音输入：ARK_MODEL -> /chat/completions
# AI 生成户型图：DOUBAO_SEEDREAM_MODEL -> /images/generations
# 应用户型图 / 解析户型图：DOUBAO_SEED_MODEL -> /chat/completions（视觉/多模态聊天模型）
def get_model_id(env_name: str, purpose: str) -> str:
    model_id = os.getenv(env_name, "").strip()
    if not model_id:
        raise RuntimeError(f"缺少环境变量 {env_name}，无法执行：{purpose}。请在 Render Environment 中填写对应模型的 model ID。")
    return model_id


def validate_model_binding(env_name: str, model_id: str, purpose: str) -> None:
    lower_model = (model_id or "").lower()
    if env_name == "DOUBAO_SEED_MODEL" and "seedream" in lower_model:
        raise RuntimeError(
            "DOUBAO_SEED_MODEL 当前填成了 Doubao-Seedream 文生图模型。"
            "应用户型图/AI解析户型图会走 /chat/completions 视觉解析接口，"
            "不能使用 doubao-seedream-5-0-260128 这类文生图 model ID。"
            "请把 DOUBAO_SEED_MODEL 改成支持图片理解/视觉聊天的 Doubao Seed 模型 model ID；"
            "DOUBAO_SEEDREAM_MODEL 才填写 doubao-seedream-5-0-260128。"
        )


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
    # 浴室家具
    "bathroomCabinet": {
        "label": "浴室柜", "model": "bathroomCabinet.glb",
        "width": 1.2, "depth": 0.5, "height": 0.9,
        "color": "#d9d9d9", "material": "木纹",
        "category": "浴室家具", "group": "卫浴收纳",
        "icon": "🛁", "tags": ["浴室", "收纳"], "score": "常用",
        "rotationOffset": 0, "yOffset": 0
    },
    "bathroomSink": {
        "label": "浴室洗手盆", "model": "bathroomSink.glb",
        "width": 0.9, "depth": 0.55, "height": 0.9,
        "color": "#eef2f6", "material": "陶瓷",
        "category": "浴室家具", "group": "卫浴洁具",
        "icon": "🚰", "tags": ["洗手"], "score": "常用",
        "rotationOffset": 0, "yOffset": 0
    },

    "bathtub": {
        "label": "浴缸", "model": "bathtub.glb",
        "width": 1.6, "depth": 0.8, "height": 0.6,
        "color": "#ffffff", "material": "陶瓷",
        "category": "浴室家具", "group": "卫浴洁具",
        "icon": "🛁", "tags": ["浴室"], "score": "展示",
        "rotationOffset": 0, "yOffset": 0
    },
    "shower": {
        "label": "淋浴间", "model": "shower.glb",
        "width": 1.0, "depth": 1.0, "height": 2.0,
        "color": "#dff3ff", "material": "玻璃",
        "category": "浴室家具", "group": "卫浴洁具",
        "icon": "🚿", "tags": ["淋浴"], "score": "常用",
        "rotationOffset": 0, "yOffset": 0
    },
    "showerRound": {
        "label": "圆形淋浴间", "model": "showerRound.glb",
        "width": 1.0, "depth": 1.0, "height": 2.0,
        "color": "#dff3ff", "material": "玻璃",
        "category": "浴室家具", "group": "卫浴洁具",
        "icon": "🚿", "tags": ["淋浴"], "score": "展示",
        "rotationOffset": 0, "yOffset": 0
    },
    "toilet": {
        "label": "马桶", "model": "toilet.glb",
        "width": 0.72, "depth": 0.72, "height": 0.82,
        "color": "#f7f7f7", "material": "陶瓷",
        "category": "浴室家具", "group": "卫浴洁具",
        "icon": "🚽", "tags": ["卫浴"], "score": "高频",
        "rotationOffset": 180, "yOffset": 0
    },
    
    # 卧室家具
    "bedBunk": {
        "label": "双层床", "model": "bedBunk.glb",
        "width": 1.15, "depth": 2.1, "height": 1.85,
        "color": "#d9d0c7", "material": "木纹",
        "category": "卧室家具", "group": "睡眠家具",
        "icon": "🛏️", "tags": ["卧室"], "score": "展示",
        "rotationOffset": 0, "yOffset": 0
    },
    "bedDouble": {
        "label": "双人床", "model": "bedDouble.glb",
        "width": 2.0, "depth": 1.8, "height": 0.62,
        "color": "#d9d0c7", "material": "布艺",
        "category": "卧室家具", "group": "睡眠家具",
        "icon": "🛏️", "tags": ["卧室"], "score": "高人气",
        "rotationOffset": 0, "yOffset": 0
    },
    "bedSingle": {
        "label": "单人床", "model": "bedSingle.glb",
        "width": 1.2, "depth": 2.0, "height": 0.62,
        "color": "#d9d0c7", "material": "布艺",
        "category": "卧室家具", "group": "睡眠家具",
        "icon": "🛏️", "tags": ["卧室"], "score": "常用",
        "rotationOffset": 0, "yOffset": 0
    },
    "cabinetBed": {
        "label": "衣柜", "model": "cabinetBed.glb",
        "width": 1.6, "depth": 0.6, "height": 2.0,
        "color": "#c49a6c", "material": "木纹",
        "category": "卧室家具", "group": "睡眠家具",
        "icon": "🛏️", "tags": ["卧室", "收纳"], "score": "展示",
        "rotationOffset": 0, "yOffset": 0
    },
    "cabinetBedDrawerTable": {
        "label": "抽屉柜", "model": "cabinetBedDrawerTable.glb",
        "width": 1.8, "depth": 0.6, "height": 0.8,
        "color": "#c49a6c", "material": "木纹",
        "category": "卧室家具", "group": "睡眠家具",
        "icon": "🛏️", "tags": ["卧室", "收纳"], "score": "推荐",
        "rotationOffset": 0, "yOffset": 0
    },
    
    # 客厅家具
    "loungeChair": {
        "label": "休闲椅", "model": "loungeChair.glb",
        "width": 0.8, "depth": 0.8, "height": 0.82,
        "color": "#8d7b68", "material": "布艺",
        "category": "客厅家具", "group": "坐具",
        "icon": "🪑", "tags": ["客厅", "阅读"], "score": "高搭配",
        "rotationOffset": 180, "yOffset": 0
    },
    "loungeChairRelax": {
        "label": "躺椅", "model": "loungeChairRelax.glb",
        "width": 1.0, "depth": 1.2, "height": 0.8,
        "color": "#6f7d8c", "material": "布艺",
        "category": "客厅家具", "group": "坐具",
        "icon": "🪑", "tags": ["客厅", "休闲"], "score": "展示",
        "rotationOffset": 180, "yOffset": 0
    },
    "loungeDesignChair": {
        "label": "设计椅", "model": "loungeDesignChair.glb",
        "width": 0.7, "depth": 0.7, "height": 0.8,
        "color": "#333333", "material": "皮质",
        "category": "客厅家具", "group": "坐具",
        "icon": "🪑", "tags": ["客厅", "设计"], "score": "展示",
        "rotationOffset": 180, "yOffset": 0
    },
    "loungeSofa": {
        "label": "沙发", "model": "loungeSofa.glb",
        "width": 1.8, "depth": 0.8, "height": 0.82,
        "color": "#6f7d8c", "material": "布艺",
        "category": "客厅家具", "group": "沙发",
        "icon": "🛋️", "tags": ["客厅", "主件"], "score": "高人气",
        "rotationOffset": 180, "yOffset": 0
    },
    "loungeSofaLong": {
        "label": "长沙发", "model": "loungeSofaLong.glb",
        "width": 2.5, "depth": 0.8, "height": 0.82,
        "color": "#6f7d8c", "material": "布艺",
        "category": "客厅家具", "group": "沙发",
        "icon": "🛋️", "tags": ["客厅", "主件"], "score": "高人气",
        "rotationOffset": 180, "yOffset": 0
    },
    "loungeDesignSofa": {
        "label": "设计沙发", "model": "loungeDesignSofa.glb",
        "width": 1.8, "depth": 0.8, "height": 0.8,
        "color": "#333333", "material": "皮质",
        "category": "客厅家具", "group": "沙发",
        "icon": "🛋️", "tags": ["客厅", "设计"], "score": "展示",
        "rotationOffset": 180, "yOffset": 0
    },
    "loungeDesignSofaCorner": {
        "label": "转角沙发", "model": "loungeDesignSofaCorner.glb",
        "width": 2.0, "depth": 2.0, "height": 0.8,
        "color": "#333333", "material": "皮质",
        "category": "客厅家具", "group": "沙发",
        "icon": "🛋️", "tags": ["客厅", "转角"], "score": "展示",
        "rotationOffset": 180, "yOffset": 0
    },
    "lampWall": {
        "label": "壁灯", "model": "lampWall.glb",
        "width": 0.2, "depth": 0.2, "height": 0.4,
        "color": "#c49a6c", "material": "金属",
        "category": "客厅家具", "group": "灯具",
        "icon": "💡", "tags": ["客厅", "墙面", "上墙"], "score": "墙面",
        "rotationOffset": 0, "yOffset": 1.5, "wallMount": True, "defaultMountHeight": 1.65
    },
    "tableCoffee": {
        "label": "茶几", "model": "tableCoffee.glb",
        "width": 1.0, "depth": 0.6, "height": 0.45,
        "color": "#b58b62", "material": "木纹",
        "category": "客厅家具", "group": "桌几",
        "icon": "☕", "tags": ["客厅", "中心位"], "score": "热销",
        "rotationOffset": 0, "yOffset": 0
    },
    "tableCoffeeGlass": {
        "label": "玻璃茶几", "model": "tableCoffeeGlass.glb",
        "width": 1.0, "depth": 0.6, "height": 0.45,
        "color": "#d9d9d9", "material": "玻璃",
        "category": "客厅家具", "group": "桌几",
        "icon": "☕", "tags": ["客厅", "现代"], "score": "展示",
        "rotationOffset": 0, "yOffset": 0
    },
    "rugRectangle": {
        "label": "长方形地毯", "model": "rugRectangle.glb",
        "width": 1.6, "depth": 1.2, "height": 0.02,
        "color": "#8d7b68", "material": "布艺",
        "category": "客厅家具", "group": "地毯",
        "icon": "🧶", "tags": ["客厅", "地面"], "score": "搭配",
        "rotationOffset": 0, "yOffset": 0
    },
    "rugRound": {
        "label": "圆形地毯", "model": "rugRound.glb",
        "width": 1.2, "depth": 1.2, "height": 0.02,
        "color": "#8d7b68", "material": "布艺",
        "category": "客厅家具", "group": "地毯",
        "icon": "🧶", "tags": ["客厅", "地面"], "score": "搭配",
        "rotationOffset": 0, "yOffset": 0
    },
    "rugRounded": {
        "label": "圆角地毯", "model": "rugRounded.glb",
        "width": 1.4, "depth": 1.0, "height": 0.02,
        "color": "#8d7b68", "material": "布艺",
        "category": "客厅家具", "group": "地毯",
        "icon": "🧶", "tags": ["客厅", "地面"], "score": "搭配",
        "rotationOffset": 0, "yOffset": 0
    },
    "rugDoormat": {
        "label": "门垫", "model": "rugDoormat.glb",
        "width": 0.8, "depth": 0.5, "height": 0.02,
        "color": "#8d7b68", "material": "布艺",
        "category": "客厅家具", "group": "地毯",
        "icon": "🧶", "tags": ["门口"], "score": "常用",
        "rotationOffset": 0, "yOffset": 0
    },

    
    # 厨房家具
    "kitchenBar": {
        "label": "厨房吧台", "model": "kitchenBar.glb",
        "width": 1.2, "depth": 0.6, "height": 1.0,
        "color": "#c49a6c", "material": "木纹",
        "category": "厨房家具", "group": "台面",
        "icon": "🍷", "tags": ["厨房", "吧台"], "score": "展示",
        "rotationOffset": 0, "yOffset": 0
    },

    "kitchenCabinet": {
        "label": "厨柜", "model": "kitchenCabinet.glb",
        "width": 1.6, "depth": 0.6, "height": 0.92,
        "color": "#d7d7d7", "material": "木纹",
        "category": "厨房家具", "group": "收纳",
        "icon": "🍳", "tags": ["厨房", "收纳"], "score": "常用",
        "rotationOffset": 0, "yOffset": 0
    },
    "kitchenCabinetDrawer": {
        "label": "抽屉柜", "model": "kitchenCabinetDrawer.glb",
        "width": 0.8, "depth": 0.6, "height": 0.8,
        "color": "#d7d7d7", "material": "木纹",
        "category": "厨房家具", "group": "收纳",
        "icon": "🗄️", "tags": ["厨房", "收纳"], "score": "常用",
        "rotationOffset": 0, "yOffset": 0
    },

    "kitchenFridgeLarge": {
        "label": "大冰箱", "model": "kitchenFridgeLarge.glb",
        "width": 0.6, "depth": 0.6, "height": 1.8,
        "color": "#ffffff", "material": "金属",
        "category": "厨房家具", "group": "电器",
        "icon": "🧊", "tags": ["厨房", "电器"], "score": "常用",
        "rotationOffset": 0, "yOffset": 0
    },
    "kitchenFridgeSmall": {
        "label": "小冰箱", "model": "kitchenFridgeSmall.glb",
        "width": 0.4, "depth": 0.4, "height": 0.8,
        "color": "#ffffff", "material": "金属",
        "category": "厨房家具", "group": "电器",
        "icon": "🧊", "tags": ["厨房", "电器"], "score": "搭配",
        "rotationOffset": 0, "yOffset": 0
    },

    "kitchenSink": {
        "label": "厨房水槽", "model": "kitchenSink.glb",
        "width": 0.6, "depth": 0.5, "height": 0.2,
        "color": "#eef2f6", "material": "不锈钢",
        "category": "厨房家具", "group": "洁具",
        "icon": "🚰", "tags": ["厨房", "水槽"], "score": "常用",
        "rotationOffset": 0, "yOffset": 0
    },

    
    # 书房/办公家具
    "bookcaseClosedDoors": {
        "label": "带门书柜", "model": "bookcaseClosedDoors.glb",
        "width": 1.2, "depth": 0.4, "height": 1.8,
        "color": "#c49a6c", "material": "木纹",
        "category": "书房/办公家具", "group": "收纳",
        "icon": "📚", "tags": ["书房", "收纳"], "score": "常用",
        "rotationOffset": 0, "yOffset": 0
    },
    "bookcaseClosedWide": {
        "label": "宽书柜", "model": "bookcaseClosedWide.glb",
        "width": 1.6, "depth": 0.4, "height": 1.8,
        "color": "#c49a6c", "material": "木纹",
        "category": "书房/办公家具", "group": "收纳",
        "icon": "📚", "tags": ["书房", "收纳"], "score": "常用",
        "rotationOffset": 0, "yOffset": 0
    },
    "bookcaseOpenLow": {
        "label": "矮书柜", "model": "bookcaseOpenLow.glb",
        "width": 1.2, "depth": 0.4, "height": 1.0,
        "color": "#c49a6c", "material": "木纹",
        "category": "书房/办公家具", "group": "收纳",
        "icon": "📚", "tags": ["书房", "收纳"], "score": "搭配",
        "rotationOffset": 0, "yOffset": 0
    },

    "chairDesk": {
        "label": "办公椅", "model": "chairDesk.glb",
        "width": 0.6, "depth": 0.6, "height": 0.9,
        "color": "#6f7d8c", "material": "布艺",
        "category": "书房/办公家具", "group": "坐具",
        "icon": "🪑", "tags": ["书房", "办公"], "score": "常用",
        "rotationOffset": 0, "yOffset": 0
    },

    "desk": {
        "label": "书桌", "model": "desk.glb",
        "width": 1.2, "depth": 0.6, "height": 0.75,
        "color": "#b8956a", "material": "木纹",
        "category": "书房/办公家具", "group": "桌几",
        "icon": "📝", "tags": ["书房", "办公"], "score": "常用",
        "rotationOffset": 0, "yOffset": 0
    },
    "table": {
        "label": "桌子", "model": "table.glb",
        "width": 1.4, "depth": 0.8, "height": 0.75,
        "color": "#b8956a", "material": "木纹",
        "category": "书房/办公家具", "group": "桌几",
        "icon": "🪑", "tags": ["餐厅", "办公"], "score": "常用",
        "rotationOffset": 0, "yOffset": 0
    },
    "tableGlass": {
        "label": "玻璃桌", "model": "tableGlass.glb",
        "width": 1.4, "depth": 0.8, "height": 0.75,
        "color": "#d9d9d9", "material": "玻璃",
        "category": "书房/办公家具", "group": "桌几",
        "icon": "🪑", "tags": ["现代", "办公"], "score": "展示",
        "rotationOffset": 0, "yOffset": 0
    },
    "tableRound": {
        "label": "圆桌", "model": "tableRound.glb",
        "width": 1.2, "depth": 1.2, "height": 0.75,
        "color": "#b8956a", "material": "木纹",
        "category": "书房/办公家具", "group": "桌几",
        "icon": "🪑", "tags": ["餐厅", "圆形"], "score": "搭配",
        "rotationOffset": 0, "yOffset": 0
    },

    
    # 电器设备
    "dryer": {
        "label": "烘干机", "model": "dryer.glb",
        "width": 0.6, "depth": 0.6, "height": 0.8,
        "color": "#ffffff", "material": "金属",
        "category": "电器设备", "group": "家电",
        "icon": "👕", "tags": ["洗衣", "电器"], "score": "常用",
        "rotationOffset": 0, "yOffset": 0
    },
    "washer": {
        "label": "洗衣机", "model": "washer.glb",
        "width": 0.6, "depth": 0.6, "height": 0.8,
        "color": "#ffffff", "material": "金属",
        "category": "电器设备", "group": "家电",
        "icon": "👕", "tags": ["洗衣", "电器"], "score": "常用",
        "rotationOffset": 0, "yOffset": 0
    },
    "lampRoundFloor": {
        "label": "落地灯", "model": "lampRoundFloor.glb",
        "width": 0.3, "depth": 0.3, "height": 1.5,
        "color": "#c49a6c", "material": "金属",
        "category": "电器设备", "group": "灯具",
        "icon": "💡", "tags": ["照明", "客厅"], "score": "搭配",
        "rotationOffset": 0, "yOffset": 0
    },
    "lampSquareFloor": {
        "label": "方形落地灯", "model": "lampSquareFloor.glb",
        "width": 0.3, "depth": 0.3, "height": 1.5,
        "color": "#333333", "material": "金属",
        "category": "电器设备", "group": "灯具",
        "icon": "💡", "tags": ["照明", "现代"], "score": "展示",
        "rotationOffset": 0, "yOffset": 0
    },
    
    # 其他物品

    "cabinetTelevision": {
        "label": "电视柜", "model": "cabinetTelevision.glb",
        "width": 1.4, "depth": 0.4, "height": 0.68,
        "color": "#2b3038", "material": "木纹",
        "category": "其他物品", "group": "收纳",
        "icon": "📺", "tags": ["客厅", "收纳", "可上墙"], "score": "常用",
        "rotationOffset": 0, "yOffset": 0, "wallMount": True, "defaultMountHeight": 1.25
    },
    "cabinetTelevisionDoors": {
        "label": "带门电视柜", "model": "cabinetTelevisionDoors.glb",
        "width": 1.4, "depth": 0.4, "height": 0.68,
        "color": "#2b3038", "material": "木纹",
        "category": "其他物品", "group": "收纳",
        "icon": "📺", "tags": ["客厅", "收纳"], "score": "常用",
        "rotationOffset": 0, "yOffset": 0
    },
    "coatRack": {
        "label": "衣帽架", "model": "coatRack.glb",
        "width": 0.3, "depth": 0.3, "height": 1.8,
        "color": "#c49a6c", "material": "木纹",
        "category": "其他物品", "group": "收纳",
        "icon": "🧥", "tags": ["门口", "收纳"], "score": "常用",
        "rotationOffset": 0, "yOffset": 0
    },
    "coatRackStanding": {
        "label": "落地衣帽架", "model": "coatRackStanding.glb",
        "width": 0.5, "depth": 0.5, "height": 1.8,
        "color": "#c49a6c", "material": "木纹",
        "category": "其他物品", "group": "收纳",
        "icon": "🧥", "tags": ["门口", "收纳"], "score": "常用",
        "rotationOffset": 0, "yOffset": 0
    },
    "plantSmall1": {
        "label": "小植物1", "model": "plantSmall1.glb",
        "width": 0.2, "depth": 0.2, "height": 0.3,
        "color": "#4caf50", "material": "植物",
        "category": "其他物品", "group": "绿植",
        "icon": "🪴", "tags": ["装饰", "绿植"], "score": "搭配",
        "rotationOffset": 0, "yOffset": 0
    },
    "plantSmall2": {
        "label": "小植物2", "model": "plantSmall2.glb",
        "width": 0.2, "depth": 0.2, "height": 0.3,
        "color": "#4caf50", "material": "植物",
        "category": "其他物品", "group": "绿植",
        "icon": "🪴", "tags": ["装饰", "绿植"], "score": "搭配",
        "rotationOffset": 0, "yOffset": 0
    },
    "plantSmall3": {
        "label": "小植物3", "model": "plantSmall3.glb",
        "width": 0.2, "depth": 0.2, "height": 0.3,
        "color": "#4caf50", "material": "植物",
        "category": "其他物品", "group": "绿植",
        "icon": "🪴", "tags": ["装饰", "绿植"], "score": "搭配",
        "rotationOffset": 0, "yOffset": 0
    },
    "pottedPlant": {
        "label": "盆栽", "model": "pottedPlant.glb",
        "width": 0.4, "depth": 0.4, "height": 0.6,
        "color": "#4caf50", "material": "植物",
        "category": "其他物品", "group": "绿植",
        "icon": "🪴", "tags": ["装饰", "绿植"], "score": "推荐",
        "rotationOffset": 0, "yOffset": 0
    },
    "trashcan": {
        "label": "垃圾桶", "model": "trashcan.glb",
        "width": 0.3, "depth": 0.3, "height": 0.4,
        "color": "#666666", "material": "塑料",
        "category": "其他物品", "group": "收纳",
        "icon": "🗑️", "tags": ["厨房", "收纳"], "score": "常用",
        "rotationOffset": 0, "yOffset": 0
    },
    "stoolBar": {
        "label": "吧凳", "model": "stoolBar.glb",
        "width": 0.3, "depth": 0.3, "height": 0.75,
        "color": "#c49a6c", "material": "木纹",
        "category": "其他物品", "group": "坐具",
        "icon": "🪑", "tags": ["厨房", "吧台"], "score": "搭配",
        "rotationOffset": 0, "yOffset": 0
    },
    "stoolBarSquare": {
        "label": "方形吧凳", "model": "stoolBarSquare.glb",
        "width": 0.3, "depth": 0.3, "height": 0.75,
        "color": "#c49a6c", "material": "木纹",
        "category": "其他物品", "group": "坐具",
        "icon": "🪑", "tags": ["厨房", "吧台"], "score": "搭配",
        "rotationOffset": 0, "yOffset": 0
    },
    "benchCushion": {
        "label": "长凳", "model": "benchCushion.glb",
        "width": 1.2, "depth": 0.4, "height": 0.4,
        "color": "#6f7d8c", "material": "布艺",
        "category": "其他物品", "group": "坐具",
        "icon": "🪑", "tags": ["客厅", "长凳"], "score": "搭配",
        "rotationOffset": 0, "yOffset": 0
    },
    "chairCushion": {
        "label": "带垫椅子", "model": "chairCushion.glb",
        "width": 0.5, "depth": 0.5, "height": 0.9,
        "color": "#6f7d8c", "material": "布艺",
        "category": "其他物品", "group": "坐具",
        "icon": "🪑", "tags": ["餐厅", "坐具"], "score": "常用",
        "rotationOffset": 180, "yOffset": 0
    },
    "chairModernCushion": {
        "label": "现代椅子", "model": "chairModernCushion.glb",
        "width": 0.5, "depth": 0.5, "height": 0.9,
        "color": "#333333", "material": "布艺",
        "category": "其他物品", "group": "坐具",
        "icon": "🪑", "tags": ["现代", "坐具"], "score": "展示",
        "rotationOffset": 180, "yOffset": 0
    },
    "chairRounded": {
        "label": "圆形椅子", "model": "chairRounded.glb",
        "width": 0.5, "depth": 0.5, "height": 0.9,
        "color": "#6f7d8c", "material": "布艺",
        "category": "其他物品", "group": "坐具",
        "icon": "🪑", "tags": ["现代", "坐具"], "score": "展示",
        "rotationOffset": 180, "yOffset": 0
    },
}

FURNITURE_GROUPS = {k: v["group"] for k, v in FURNITURE_DEFAULTS.items()}
FURNITURE_ALIASES = {
    # 浴室家具
    "浴室柜": "bathroomCabinet",
    "浴室洗手盆": "bathroomSink",

    "浴缸": "bathtub",
    "淋浴间": "shower",
    "圆形淋浴间": "showerRound",
    "马桶": "toilet",
    
    # 卧室家具
    "双层床": "bedBunk",
    "双人床": "bedDouble",
    "单人床": "bedSingle",
    "多功能柜": "cabinetBed",
    "抽屉桌": "cabinetBedDrawerTable",
    
    # 客厅家具
    "带坐垫的长椅": "benchCushion",
    "带坐垫的椅子": "chairCushion",
    "现代带坐垫的椅子": "chairModernCushion",
    "圆角椅子": "chairRounded",
    "休闲椅": "loungeChair",
    "放松休闲椅": "loungeChairRelax",
    "设计款休闲椅": "loungeDesignChair",
    "设计款沙发": "loungeDesignSofa",
    "设计款转角沙发": "loungeDesignSofaCorner",
    "沙发": "loungeSofa",
    "长沙发": "loungeSofaLong",

    "门垫": "rugDoormat",
    "长方形地毯": "rugRectangle",
    "圆形地毯": "rugRound",
    "圆角地毯": "rugRounded",
    "咖啡桌": "tableCoffee",
    "玻璃咖啡桌": "tableCoffeeGlass",
    "壁灯": "lampWall",
    
    # 厨房家具
    "厨房吧台": "kitchenBar",
    "厨柜": "kitchenCabinet",
    "抽屉柜": "kitchenCabinetDrawer",
    "大冰箱": "kitchenFridgeLarge",
    "小冰箱": "kitchenFridgeSmall",
    "厨房水槽": "kitchenSink",
    
    # 书房/办公家具
    "带门书柜": "bookcaseClosedDoors",
    "宽书柜": "bookcaseClosedWide",
    "矮书柜": "bookcaseOpenLow",
    "办公椅": "chairDesk",
    "书桌": "desk",
    "桌子": "table",
    "玻璃桌": "tableGlass",
    "圆桌": "tableRound",
    
    # 电器设备
    "烘干机": "dryer",
    "洗衣机": "washer",
    "落地灯": "lampRoundFloor",
    "方形落地灯": "lampSquareFloor",
    
    # 其他物品

    "电视柜": "cabinetTelevision",
    "带门电视柜": "cabinetTelevisionDoors",
    "衣帽架": "coatRack",
    "落地衣帽架": "coatRackStanding",
    "小植物1": "plantSmall1",
    "小植物2": "plantSmall2",
    "小植物3": "plantSmall3",
    "盆栽": "pottedPlant",
    "垃圾桶": "trashcan",
    "吧凳": "stoolBar",
    "方形吧凳": "stoolBarSquare",
}

# 旧家具类型映射到新家具类型
LEGACY_FURNITURE_TYPE_MAP = {
    "sofa": "loungeSofa",
    "armchair": "loungeChair",
    "tv": "cabinetTelevision",
    "coffee_table": "tableCoffee",
    "sideboard": "cabinetTelevisionDoors",
    "bed": "bedDouble",
    "wardrobe": "bookcaseClosedWide",
    "nightstand": "cabinetBedDrawerTable",
    "bookshelf": "bookcaseOpenLow",
    "dining_table": "table",
    "dining_chair": "chairCushion",
    "kitchen_counter": "kitchenCabinet",
    "sink": "bathroomSink",
    "potted_plant": "pottedPlant",
    "flower_pot": "plantSmall2",
    "indoor_tree": "plantSmall3",
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
    floor_color: str = "#d8d0bd"
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
    placement: str = "floor"
    wall: Optional[str] = None
    wall_offset: float = 0.0
    mount_height: float = 1.5


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
        self.message = "欢迎来到装修小游戏工作台。"
        self.rooms: List[Room] = [
            Room("room_1", "客厅", 0.0, 0.0, 4.8, 4.0, wall_material="原木风", wall_color="#ede6d8", floor_color="#d8d0bd"),
            Room("room_2", "饭厅", 4.8, 0.0, 3.0, 3.0, wall_material="白色瓷砖", wall_color="#f7f4ee", floor_color="#eee9da"),
            Room("room_3", "卧室", 0.0, 4.0, 3.8, 3.4, wall_material="木纹", wall_color="#efe7da", floor_color="#d9cbb5"),
            Room("room_4", "阳台", 3.8, 4.0, 2.6, 1.8, wall_material="白色瓷砖", wall_color="#eef3ea", floor_color="#dfe7df"),
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
            self.message = "没有可撤销的操作。"
            return self.message
        self.future.append(copy.deepcopy(self.snapshot()))
        self.restore(self.history.pop())
        self.message = "已撤销上一步。"
        return self.message

    def redo(self) -> str:
        if not self.future:
            self.message = "没有可重做的操作。"
            return self.message
        self.history.append(copy.deepcopy(self.snapshot()))
        self.restore(self.future.pop())
        self.message = "已恢复刚才撤销的操作。"
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
                        "model": meta.get("model"),
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
                        "rotationOffset": meta.get("rotationOffset", 0),
                        "yOffset": meta.get("yOffset", 0),
                        "wallMount": bool(meta.get("wallMount", False)),
                        "defaultMountHeight": meta.get("defaultMountHeight", meta.get("yOffset", 1.5)),
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
    if is_wall_furniture(item):
        clamp_wall_furniture(item)
        return
    room = room_by_id(item.room_id)
    if not room:
        return
    fw, fd = get_furniture_footprint(item)
    item.x = clamp(item.x, room.x + 0.05, room.x + room.width - fw - 0.05)
    item.y = clamp(item.y, room.y + 0.05, room.y + room.depth - fd - 0.05)


def collides(item: Furniture) -> bool:
    if is_wall_furniture(item):
        return False
    fw, fd = get_furniture_footprint(item)
    for other in STATE.furnitures:
        if other.id == item.id or other.room_id != item.room_id or is_wall_furniture(other):
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


def wall_length(room: Room, wall: str) -> float:
    return room.width if wall in {"top", "bottom"} else room.depth


def normalize_wall(value: Optional[str]) -> str:
    return value if value in WALLS else "top"


def clamp_wall_furniture(item: Furniture) -> None:
    room = room_by_id(item.room_id)
    if not room:
        return
    item.wall = normalize_wall(item.wall)
    length = wall_length(room, item.wall)
    item.wall_offset = clamp(float(item.wall_offset or 0), 0.05, max(0.05, length - 0.05))
    item.mount_height = clamp(float(item.mount_height or 1.5), 0.25, max(0.25, room.height - 0.15))
    item.placement = "wall"
    if item.wall == "top":
        item.x = room.x + item.wall_offset
        item.y = room.y
        item.rotation = 0
    elif item.wall == "bottom":
        item.x = room.x + item.wall_offset
        item.y = room.y + room.depth
        item.rotation = 180
    elif item.wall == "left":
        item.x = room.x
        item.y = room.y + item.wall_offset
        item.rotation = 90
    else:
        item.x = room.x + room.width
        item.y = room.y + item.wall_offset
        item.rotation = 270


def is_wall_furniture(item: Furniture) -> bool:
    return getattr(item, "placement", "floor") == "wall"


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
    placement: str = "floor",
    wall: Optional[str] = None,
    wall_offset: Optional[float] = None,
    mount_height: Optional[float] = None,
) -> tuple[bool, str, Optional[Furniture]]:
    if ftype not in FURNITURE_DEFAULTS:
        return False, "家具类型不存在。", None

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
        placement="wall" if placement == "wall" and meta.get("wallMount") else "floor",
        wall=normalize_wall(wall),
        wall_offset=float(wall_offset if wall_offset is not None else 0.3),
        mount_height=float(mount_height if mount_height is not None else meta.get("defaultMountHeight", meta.get("yOffset", 1.5))),
    )

    if item.placement == "wall":
        clamp_wall_furniture(item)
    else:
        clamp_furniture_inside_room(item)
        snap_furniture(item)
        if collides(item):
            return False, f"{item.label}放置失败：与其他家具重叠。", None

    STATE.furnitures.append(item)
    return True, f"已添加{item.label}{'（墙面）' if item.placement == 'wall' else ''}。", item


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

    for key in ["label", "x", "y", "width", "depth", "rotation", "color", "material", "placement", "wall", "wall_offset", "mount_height"]:
        if key not in payload:
            continue
        value = payload[key]
        if key in {"x", "y", "width", "depth", "rotation", "wall_offset", "mount_height"}:
            value = float(value)
        setattr(item, key, value)

    item.width = clamp(item.width, 0.25, 5.0)
    item.depth = clamp(item.depth, 0.25, 5.0)
    item.rotation = normalize_rotation(item.rotation)

    if item.placement == "wall":
        if item.type not in FURNITURE_DEFAULTS or not FURNITURE_DEFAULTS[item.type].get("wallMount"):
            item.placement = "floor"
        else:
            clamp_wall_furniture(item)
    if item.placement != "wall":
        fw, fd = get_furniture_footprint(item)
        center_room = find_room_for_point(item.x + fw / 2, item.y + fd / 2)
        if center_room:
            item.room_id = center_room.id
        clamp_furniture_inside_room(item)
        snap_furniture(item)

    if collides(item):
        for k, v in old.items():
            setattr(item, k, v)
        return False, f"{item.label}调整失败：与其他家具重叠。"

    return True, f"{item.label}已更新。"


def delete_furniture(item: Furniture) -> str:
    STATE.furnitures = [f for f in STATE.furnitures if f.id != item.id]
    return f"已删除{item.label}。"


def update_room(room: Room, payload: Dict) -> tuple[bool, str]:
    old = asdict(room)

    for key in ["name", "x", "y", "width", "depth", "height", "wall_color", "floor_color", "wall_material"]:
        if key not in payload:
            continue
        value = payload[key]
        if key in {"x", "y", "width", "depth", "height"}:
            value = float(value)
        setattr(room, key, value)

    room.width = clamp(room.width, 1.6, float('inf'))
    room.depth = clamp(room.depth, 1.6, float('inf'))
    room.height = max(0.1, room.height)

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
            return False, f"{room.name}调整失败：与{other.name}重叠。"

    return True, f"{room.name}已更新。"


def delete_room(room: Room) -> str:
    STATE.rooms = [r for r in STATE.rooms if r.id != room.id]
    STATE.furnitures = [f for f in STATE.furnitures if f.room_id != room.id]
    STATE.openings = [o for o in STATE.openings if o.room_id != room.id]
    return f"已删除{room.name}及其相关家具、门窗。"


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
    height: float = 3.0,
    wall_color: str = "#f0efe9",
    floor_color: str = "#d8d0bd",
    wall_material: str = "白色瓷砖",
) -> tuple[bool, str, Optional[Room]]:
    width = clamp(width, 1.6, 12.0)
    depth = clamp(depth, 1.6, 12.0)
    height = max(0.1, float(height))
    room_x, room_y = find_available_room_position(width, depth, x, y)
    room_name = name or ROOM_TYPE_OPTIONS[min(len(STATE.rooms), len(ROOM_TYPE_OPTIONS) - 1)]
    room = Room(next_id("room", STATE.rooms), room_name, room_x, room_y, width, depth, height=height, wall_color=wall_color, floor_color=floor_color, wall_material=wall_material)

    overlap = room_overlaps(room)
    if overlap:
        return False, f"新增房间失败：与{overlap.name}重叠。", None

    STATE.rooms.append(room)
    if room_x != x or room_y != y:
        return True, f"已添加{room.name}，并自动避让到空位置。", room
    return True, f"已添加{room.name}。", room


def add_opening(
    room: Room,
    opening_type: str,
    wall: str,
    offset: float,
    width: float,
    name: Optional[str] = None,
    height: Optional[float] = None,
    sill: Optional[float] = None,
    color: Optional[str] = None,
    material: Optional[str] = None,
) -> tuple[bool, str, Optional[Opening]]:
    if opening_type not in OPENING_TYPE_LABELS or wall not in WALLS:
        return False, "é¨çªåæ°ä¸æ­£ç¡®ã", None

    same_type_count = len([o for o in STATE.openings if o.type == opening_type and o.room_id == room.id]) + 1
    opening = Opening(
        id=next_id("opening", STATE.openings),
        type=opening_type,
        name=name or opening_default_name(opening_type, room, same_type_count),
        room_id=room.id,
        wall=wall,
        offset=float(offset),
        width=float(width),
        height=float(height if height is not None else (1.5 if opening_type == "window" else 2.1)),
        sill=float(sill if sill is not None else (0.9 if opening_type == "window" else 0.0)),
        color=color or ("#79bdf8" if opening_type == "window" else "#8b6a4d"),
        material=material or ("ç»ç" if opening_type == "window" else "æ¨è´¨"),
    )

    clamp_opening(opening)
    STATE.openings.append(opening)
    return True, f"å·²å¨{room.name}æ·»å {OPENING_TYPE_LABELS[opening_type]}ã", opening


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
        opening.material = "ç»ç" if opening.type == "window" else "æ¨è´¨"

    for key in ["name", "offset", "width", "height", "sill", "color", "material"]:
        if key in payload:
            value = payload[key]
            if key in {"offset", "width", "height", "sill"}:
                value = float(value)
            setattr(opening, key, value)

    opening.height = max(0.2, float(opening.height))
    opening.sill = max(0.0, float(opening.sill))
    clamp_opening(opening)
    return True, f"å·²æ´æ°{opening.name or OPENING_TYPE_LABELS[opening.type]}ã"


def delete_opening(opening: Opening) -> str:
    STATE.openings = [o for o in STATE.openings if o.id != opening.id]
    return f"å·²å é¤{opening.name or OPENING_TYPE_LABELS[opening.type]}ã"


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


ROOM_NAME_EN_MAP = {
    "bedroom": "卧室",
    "masterbedroom": "主卧",
    "guestbedroom": "次卧",
    "livingroom": "客厅",
    "diningroom": "餐厅",
    "kitchen": "厨房",
    "bathroom": "卫生间",
    "restroom": "卫生间",
    "toilet": "卫生间",
    "balcony": "阳台",
    "study": "书房",
    "office": "书房",
    "room": "房间",
    "livingdiningkitchen": "客餐厨",
    "livingdining": "客餐厅",
}

ROOM_ALIASES = {
    "客厅": ["客厅", "客餐厅", "客餐厨", "起居室", "living room", "living"],
    "卧室": ["卧室", "主卧", "次卧", "bedroom", "master bedroom", "guest bedroom"],
    "阳台": ["阳台", "balcony"],
    "厨房": ["厨房", "厨", "kitchen"],
    "卫生间": ["卫生间", "浴室", "厕所", "洗手间", "bathroom", "toilet", "restroom"],
    "书房": ["书房", "office", "study"],
    "餐厅": ["餐厅", "饭厅", "dining room", "dining"],
}

ACTION_SYNONYMS = {
    "add": ["添加", "新增", "加", "放", "摆放", "放入", "来一个"],
    "delete": ["删除", "移除", "去掉", "拿掉", "取消"],
    "update": ["修改", "调整", "改成", "改为", "设置为", "设为", "变成", "换成"],
    "move": ["移动", "移到", "挪到", "放到", "搬到"],
    "rotate": ["旋转", "转动", "转向"],
}

PROPERTY_ALIASES = {
    "height": ["高度", "高", "墙高", "层高", "墙面高度", "窗高", "门高", "窗户高度", "门高度"],
    "width": ["宽度", "宽", "门宽", "窗宽"],
    "depth": ["深度", "进深", "长度", "长"],
    "sill": ["窗台高度", "窗台高"],
    "wall_color": ["墙颜色", "墙面颜色", "墙色", "墙面改成"],
    "floor_color": ["地板颜色", "地面颜色", "地砖颜色", "地板改成", "地面改成"],
    "material": ["材质", "材料"],
    "rotation": ["角度", "旋转", "朝向"],
}

VOICE_TEXT_REPLACEMENTS = {
    "二弟": "2D",
    "二维": "2D",
    "三弟": "3D",
    "三维": "3D",
    "第一视角": "第一人称视角",
    "第一人称模式": "第一人称视角",
    "窗台高": "窗台高度",
    "墙高": "墙面高度",
    "地砖": "地板",
}


def sanitize_token(value: str) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]", "", (value or "").lower())


def build_furniture_display_names() -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for alias, ftype in FURNITURE_ALIASES.items():
        mapping.setdefault(ftype, alias)
    return mapping


FURNITURE_TYPE_DISPLAY_NAMES = build_furniture_display_names()


def chinese_digit_to_number(text: str) -> float:
    if not text:
        return 0.0
    digit_map = {"零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
    unit_map = {"十": 10, "百": 100, "千": 1000}
    if "点" in text:
        integer_part, decimal_part = text.split("点", 1)
        integer_value = int(chinese_digit_to_number(integer_part)) if integer_part else 0
        decimal_digits = "".join(str(digit_map.get(ch, "")) for ch in decimal_part if ch in digit_map)
        return float(f"{integer_value}.{decimal_digits or '0'}")

    total = 0
    current = 0
    for ch in text:
        if ch in digit_map:
            current = digit_map[ch]
        elif ch in unit_map:
            if current == 0:
                current = 1
            total += current * unit_map[ch]
            current = 0
    return float(total + current)


def replace_chinese_numbers(text: str) -> str:
    def repl(match: re.Match) -> str:
        token = match.group(0)
        try:
            value = chinese_digit_to_number(token)
            if value.is_integer():
                return str(int(value))
            return str(value)
        except Exception:
            return token

    return re.sub(r"[零一二两三四五六七八九十百千点]+", repl, text)


def normalize_command_text(text: str, source: str = "typed") -> str:
    normalized = (text or "").strip()
    if not normalized:
        return ""
    normalized = normalized.replace("，", " ").replace("。", " ").replace("：", " ").replace("；", " ")
    normalized = normalized.replace("　", " ").replace(",", " ").replace("/", " ")
    normalized = re.sub(r"\s+", " ", normalized).strip()
    normalized = replace_chinese_numbers(normalized)
    if source == "voice":
        for src, target in VOICE_TEXT_REPLACEMENTS.items():
            normalized = normalized.replace(src, target)
    return normalized


def localize_room_name(name: str, index: int = 1) -> str:
    raw = (name or "").strip()
    if not raw:
        return f"房间{index}"
    if re.search(r"[\u4e00-\u9fff]", raw):
        return raw
    token = sanitize_token(raw)
    if token in ROOM_NAME_EN_MAP:
        return ROOM_NAME_EN_MAP[token]
    for key, value in ROOM_NAME_EN_MAP.items():
        if key in token:
            return value
    return f"房间{index}"


def localize_furniture_label(label: str, furniture_type: str) -> str:
    raw = (label or "").strip()
    if raw and re.search(r"[\u4e00-\u9fff]", raw):
        return raw
    return FURNITURE_TYPE_DISPLAY_NAMES.get(furniture_type, "家具")


def localize_opening_name(name: str, opening_type: str, room_name: str, index: int = 1) -> str:
    raw = (name or "").strip()
    if raw and re.search(r"[\u4e00-\u9fff]", raw):
        return raw
    suffix = "窗" if opening_type == "window" else "门"
    if room_name:
        return f"{room_name}{suffix}"
    return f"{suffix}{index}"


def detect_room_by_alias(text: str) -> Optional[Room]:
    room = detect_room(text)
    if room:
        return room
    lowered = text.lower()
    for canonical, aliases in ROOM_ALIASES.items():
        if any(alias.lower() in lowered for alias in aliases):
            for candidate in STATE.rooms:
                if canonical in candidate.name:
                    return candidate
    return None


def get_selected_entities(selected_context: Optional[Dict]) -> Dict[str, Optional[object]]:
    result = {"room": None, "opening": None, "furniture": None}
    if not isinstance(selected_context, dict):
        return result
    selected_type = selected_context.get("type")
    selected_id = selected_context.get("id")
    if selected_type == "room":
        result["room"] = room_by_id(selected_id)
    elif selected_type == "opening":
        opening = opening_by_id(selected_id)
        result["opening"] = opening
        if opening:
            result["room"] = room_by_id(opening.room_id)
    elif selected_type == "furniture":
        furniture = furniture_by_id(selected_id)
        result["furniture"] = furniture
        if furniture:
            result["room"] = room_by_id(furniture.room_id)
    return result


def extract_metric_value(text: str, keywords: List[str]) -> Optional[float]:
    keyword_group = "|".join(re.escape(word) for word in keywords)
    patterns = [
        rf"(?:{keyword_group})(?:改成|改为|调整为|设置为|设为|到)?\s*(-?\d+(?:\.\d+)?)\s*米?",
        rf"(-?\d+(?:\.\d+)?)\s*米?(?:的)?(?:{keyword_group})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return float(match.group(1))
    return None


def extract_rotation_value(text: str) -> Optional[float]:
    match = re.search(r"(?:旋转|角度|朝向)(?:改成|改为|调整为|设置为|设为|到)?\s*(-?\d+(?:\.\d+)?)", text)
    if match:
        return float(match.group(1))
    return None


def extract_target_room(text: str) -> Optional[Room]:
    move_markers = ["移到", "移动到", "挪到", "搬到", "放到"]
    for marker in move_markers:
        if marker in text:
            trailing = text.split(marker, 1)[1]
            return detect_room_by_alias(trailing)
    return None


def infer_action_type(text: str) -> str:
    for action, words in ACTION_SYNONYMS.items():
        if any(word in text for word in words):
            return action
    return "update"


def detect_client_action(text: str) -> Optional[Dict[str, str]]:
    normalized = (text or "").strip().lower()
    if not normalized:
        return None
    if "第一人称" in normalized and any(token in normalized for token in ["进入", "开启", "切换到", "打开"]):
        return {"type": "enter_first_person"}
    if "第一人称" in normalized and any(token in normalized for token in ["退出", "关闭", "离开"]):
        return {"type": "exit_first_person"}
    if any(token in normalized for token in ["切换到2d", "切换到 2d", "2d视图", "2d模式", "二维视图", "平面视图"]):
        return {"type": "show_2d"}
    if any(token in normalized for token in ["切换到3d", "切换到 3d", "3d视图", "3d模式", "三维视图", "立体视图"]):
        return {"type": "show_3d"}
    return None


def detect_opening(text: str, room: Optional[Room] = None, opening_type: Optional[str] = None, selected_context: Optional[Dict] = None) -> Optional[Opening]:
    selected = get_selected_entities(selected_context)
    if selected.get("opening"):
        opening = selected["opening"]
        if (not room or opening.room_id == room.id) and (not opening_type or opening.type == opening_type):
            return opening

    candidates = STATE.openings
    if room:
        candidates = [item for item in candidates if item.room_id == room.id]
    if opening_type:
        candidates = [item for item in candidates if item.type == opening_type]

    for opening in candidates:
        if opening.name and opening.name in text:
            return opening

    if opening_type == "window" or "窗" in text:
        return next((item for item in candidates if item.type == "window"), None)
    if opening_type == "door" or "门" in text:
        return next((item for item in candidates if item.type == "door"), None)
    return candidates[0] if candidates else None


def detect_furniture_item(text: str, room: Optional[Room] = None, selected_context: Optional[Dict] = None) -> Optional[Furniture]:
    selected = get_selected_entities(selected_context)
    if selected.get("furniture"):
        furniture = selected["furniture"]
        if not room or furniture.room_id == room.id:
            return furniture

    furniture_type = detect_furniture_type(text)
    candidates = STATE.furnitures
    if room:
        candidates = [item for item in candidates if item.room_id == room.id]

    for item in candidates:
        if item.label and item.label in text:
            return item
    if furniture_type:
        return next((item for item in candidates if item.type == furniture_type), None)
    return candidates[0] if candidates else None


def parse_command(text: str, selected_context: Optional[Dict] = None) -> Dict:
    normalized = normalize_command_text(text, "typed")
    if not normalized:
        return {"ok": False, "message": "请输入指令。", "action": None, "changed": False}

    client_action = detect_client_action(normalized)
    if client_action:
        message_map = {
            "enter_first_person": "已进入第一人称视角。",
            "exit_first_person": "已退出第一人称视角。",
            "show_2d": "已切换到 2D 视图。",
            "show_3d": "已切换到 3D 视图。",
        }
        return {"ok": True, "message": message_map[client_action["type"]], "action": client_action, "changed": False}

    if "撤销" in normalized:
        return {"ok": True, "message": STATE.undo(), "action": None, "changed": False}
    if "重做" in normalized or "恢复" in normalized:
        return {"ok": True, "message": STATE.redo(), "action": None, "changed": False}
    if "显示网格" in normalized or "打开网格" in normalized:
        STATE.show_grid = True
        return {"ok": True, "message": "已显示网格。", "action": None, "changed": True}
    if "隐藏网格" in normalized or "关闭网格" in normalized:
        STATE.show_grid = False
        return {"ok": True, "message": "已隐藏网格。", "action": None, "changed": True}

    selected = get_selected_entities(selected_context)
    room = detect_room_by_alias(normalized) or selected.get("room")
    furniture_type = detect_furniture_type(normalized)
    furniture_item = detect_furniture_item(normalized, room=room, selected_context=selected_context)
    opening_type = "window" if "窗" in normalized else ("door" if "门" in normalized else None)
    opening_item = detect_opening(normalized, room=room, opening_type=opening_type, selected_context=selected_context)
    color = detect_color(normalized)
    action_type = infer_action_type(normalized)

    if room and furniture_type and action_type == "add":
        ok, msg, _ = add_furniture(room, furniture_type, color=color)
        return {"ok": ok, "message": msg, "action": None, "changed": ok}

    if furniture_item and action_type == "delete":
        msg = delete_furniture(furniture_item)
        return {"ok": True, "message": msg, "action": None, "changed": True}

    if furniture_item and action_type == "move":
        target_room = extract_target_room(normalized)
        if not target_room:
            return {"ok": False, "message": "没有识别到要移动到哪个房间。", "action": None, "changed": False}
        ok, msg = update_furniture(furniture_item, {"room_id": target_room.id, "x": target_room.x + 0.3, "y": target_room.y + 0.3})
        return {"ok": ok, "message": msg, "action": None, "changed": ok}

    if furniture_item and (color or action_type in {"update", "rotate"}):
        payload = {}
        if color:
            payload["color"] = color
        rotation = extract_rotation_value(normalized)
        if rotation is not None:
            payload["rotation"] = rotation
        width = extract_metric_value(normalized, PROPERTY_ALIASES["width"])
        depth = extract_metric_value(normalized, PROPERTY_ALIASES["depth"])
        if width is not None:
            payload["width"] = width
        if depth is not None:
            payload["depth"] = depth
        for material in MATERIAL_OPTIONS:
            if material and material in normalized:
                payload["material"] = material
                break
        if payload:
            ok, msg = update_furniture(furniture_item, payload)
            return {"ok": ok, "message": msg, "action": None, "changed": ok}

    room_property_requested = any(
        extract_metric_value(normalized, PROPERTY_ALIASES[key]) is not None
        for key in ["width", "depth", "height", "sill"]
    ) or color is not None or any(material and material in normalized for material in MATERIAL_OPTIONS)

    if room and (room_property_requested or any(token in normalized for token in ["墙", "地板", "地面", "地砖"])):
        payload = {}
        width = extract_metric_value(normalized, PROPERTY_ALIASES["width"])
        depth = extract_metric_value(normalized, PROPERTY_ALIASES["depth"])
        height = extract_metric_value(normalized, PROPERTY_ALIASES["height"])
        if width is not None:
            payload["width"] = width
        if depth is not None:
            payload["depth"] = depth
        if height is not None:
            payload["height"] = height
        if color:
            if any(token in normalized for token in ["地板", "地面", "地砖"]):
                payload["floor_color"] = color
            if any(token in normalized for token in ["墙", "墙面"]):
                payload.setdefault("wall_color", color)
        for material in MATERIAL_OPTIONS:
            if material and material in normalized:
                payload["wall_material"] = material
                break
        if payload:
            ok, msg = update_room(room, payload)
            return {"ok": ok, "message": msg, "action": None, "changed": ok}

    if opening_item:
        payload = {}
        height = extract_metric_value(normalized, ["窗户高度", "窗高", "门高", "门高度", "高度"])
        sill = extract_metric_value(normalized, PROPERTY_ALIASES["sill"])
        width = extract_metric_value(normalized, ["宽度", "窗宽", "门宽"])
        if height is not None:
            payload["height"] = height
        if sill is not None:
            payload["sill"] = sill
        if width is not None:
            payload["width"] = width
        if color:
            payload["color"] = color
        for material in MATERIAL_OPTIONS:
            if material and material in normalized:
                payload["material"] = material
                break
        if payload:
            ok, msg = update_opening(opening_item, payload)
            return {"ok": ok, "message": msg, "action": None, "changed": ok}

    return {
        "ok": False,
        "message": "暂时没有理解这条中文指令。可以试试修改房间高度、给客厅添加家具、删除已有家具、修改窗户高度或切换视图。",
        "action": None,
        "changed": False,
    }


def execute_command(text: str, source: str = "typed", selected_context: Optional[Dict] = None) -> Dict:
    normalized = normalize_command_text(text, source)
    result = parse_command(normalized, selected_context=selected_context)
    result["normalized_text"] = normalized
    return result


def call_ark_chat_json(system_prompt: str, user_prompt: str, max_tokens: int = 260) -> Dict:
    prompt = (user_prompt or "").strip()
    transcript = prompt.replace("请将这段中文语音转成标准中文家装指令：", "").strip()
    if not transcript:
        return {
            "command": "",
            "reason": "未识别到有效语音内容。",
            "confidence": "low",
        }
    return normalize_voice_command_with_llm(transcript)


def normalize_voice_command_with_llm(transcript: str) -> Dict:
    normalized = normalize_command_text(transcript, "voice")
    if not normalized:
        return {
            "command": "",
            "reason": "未识别到有效语音内容。",
            "confidence": "low",
        }
    return {
        "command": normalized,
        "reason": "已按中文规则标准化语音指令。",
        "confidence": "high",
    }


def apply_command(text: str, selected_context: Optional[Dict] = None) -> str:
    return execute_command(text, "typed", selected_context=selected_context)["message"]


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
    selected_context = payload.get("selected")
    if not transcript:
        return jsonify({"ok": False, "message": "未收到语音转写结果。", "state": STATE.to_dict()}), 400

    try:
        llm_result = normalize_voice_command_with_llm(transcript)
    except Exception as exc:
        msg = f"{ARK_MODEL_LABEL} 语音指令规则处理失败：{exc}"
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
        msg = f"无法将语音内容解析为中文指令。{('原因：' + llm_reason) if llm_reason else ''}"
        STATE.message = msg
        return jsonify({
            "ok": False,
            "message": msg,
            "transcript": transcript,
            "llm_reason": llm_reason,
            "llm_confidence": llm_confidence,
            "state": STATE.to_dict(),
        })

    action = detect_client_action(normalized_command)
    if not action and all(token not in normalized_command for token in ["撤销", "重做", "恢复"]):
        STATE.push_history()
    result = execute_command(normalized_command, "voice", selected_context=selected_context)
    STATE.message = result["message"]
    return jsonify({
        "ok": result.get("ok", True),
        "message": STATE.message,
        "transcript": transcript,
        "llm_command": normalized_command,
        "llm_reason": llm_reason,
        "llm_confidence": llm_confidence,
        "action": action,
        "state": STATE.to_dict(),
    })


@app.route("/api/command", methods=["POST"])
def api_command():
    payload = request.get_json(silent=True) or {}
    text = str(payload.get("command", "")).strip()
    selected_context = payload.get("selected")
    normalized_text = normalize_command_text(text, "typed")
    action = detect_client_action(normalized_text)
    if text and not action and all(token not in normalized_text for token in ["撤销", "重做", "恢复"]):
        STATE.push_history()
    result = execute_command(text, "typed", selected_context=selected_context)
    STATE.message = result["message"]
    return jsonify({
        **STATE.to_dict(),
        "action": action,
        "ok": result.get("ok", True),
        "normalized_command": normalized_text,
    })


@app.route("/api/undo", methods=["POST"])
def api_undo():
    STATE.undo()
    return jsonify({"ok": True, "message": "已撤销上一步操作。", "state": STATE.to_dict()})


@app.route("/api/redo", methods=["POST"])
def api_redo():
    STATE.redo()
    return jsonify({"ok": True, "message": "已恢复上一步操作。", "state": STATE.to_dict()})


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
        localized_room_names: Dict[str, str] = {}
        if "rooms" in payload:
            for index, room_data in enumerate(payload["rooms"], start=1):
                localized_name = localize_room_name(room_data.get("name", ""), index)
                room = Room(
                    id=room_data.get("id"),
                    name=localized_name,
                    x=room_data.get("x", 0),
                    y=room_data.get("y", 0),
                    width=room_data.get("width", 3),
                    depth=room_data.get("depth", 3),
                    height=max(0.1, float(room_data.get("height", 3.0))),
                    wall_color=room_data.get("wall_color", "#f0efe9"),
                    floor_color=room_data.get("floor_color", "#d8d0bd"),
                    wall_material=room_data.get("wall_material", "白色瓷砖")
                )
                STATE.rooms.append(room)
                localized_room_names[room.id] = localized_name
        
        # 导入家具
        if "furnitures" in payload:
            for furniture_data in payload["furnitures"]:
                furniture_type = furniture_data.get("type", "loungeSofa")
                # 映射旧家具类型到新家具类型
                furniture_type = LEGACY_FURNITURE_TYPE_MAP.get(furniture_type, furniture_type)

                # 如果AI返回的家具类型不在当前模型库里，直接跳过
                if furniture_type not in FURNITURE_DEFAULTS:
                    print(f"跳过未知家具类型: {furniture_type}")
                    continue

                meta = FURNITURE_DEFAULTS[furniture_type]
                localized_label = localize_furniture_label(furniture_data.get("label", ""), furniture_type)
                furniture = Furniture(
                    id=furniture_data.get("id") or next_id("furniture", STATE.furnitures),
                    type=furniture_type,
                    label=localized_label or meta.get("label", "家具"),
                    room_id=furniture_data.get("room_id") or (STATE.rooms[0].id if STATE.rooms else None),
                    x=float(furniture_data.get("x", 0)),
                    y=float(furniture_data.get("y", 0)),
                    z=float(furniture_data.get("z", 0)),
                    width=float(furniture_data.get("width", meta.get("width", 1))),
                    depth=float(furniture_data.get("depth", meta.get("depth", 1))),
                    height=float(furniture_data.get("height", meta.get("height", 0.8))),
                    rotation=float(furniture_data.get("rotation", 0)),
                    color=furniture_data.get("color", meta.get("color", "#6f7d8c")),
                    material=furniture_data.get("material", meta.get("material", "布艺")),
                    placement=furniture_data.get("placement", "floor"),
                    wall=furniture_data.get("wall"),
                    wall_offset=float(furniture_data.get("wall_offset", 0.3)),
                    mount_height=float(furniture_data.get("mount_height", meta.get("defaultMountHeight", meta.get("yOffset", 1.5)))),
                )
                if furniture.placement == "wall" and meta.get("wallMount"):
                    clamp_wall_furniture(furniture)
                else:
                    furniture.placement = "floor"
                    clamp_furniture_inside_room(furniture)
                STATE.furnitures.append(furniture)
        
        # 导入门窗
        if "openings" in payload:
            for index, opening_data in enumerate(payload["openings"], start=1):
                room_id = opening_data.get("room_id") or (STATE.rooms[0].id if STATE.rooms else None)
                room_name = localized_room_names.get(room_id, room_by_id(room_id).name if room_id and room_by_id(room_id) else "")
                opening = Opening(
                    id=opening_data.get("id"),
                    type=opening_data.get("type", "door"),
                    name=localize_opening_name(opening_data.get("name", ""), opening_data.get("type", "door"), room_name, index),
                    room_id=room_id,
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
        return jsonify({"ok": False, "message": "请选择一个放置房间。"}), 400

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
        payload.get("placement", "floor"),
        payload.get("wall"),
        payload.get("wall_offset"),
        payload.get("mount_height"),
    )
    STATE.message = msg
    return jsonify({"ok": ok, "message": msg, "item": asdict(item) if item else None, "state": STATE.to_dict()})


@app.route("/api/furniture/<item_id>", methods=["PATCH"])
def api_update_furniture(item_id: str):
    item = furniture_by_id(item_id)
    if not item:
        return jsonify({"ok": False, "message": "家具不存在。"}), 404

    STATE.push_history()
    ok, msg = update_furniture(item, request.get_json(silent=True) or {})
    STATE.message = msg
    return jsonify({"ok": ok, "message": msg, "item": asdict(item), "state": STATE.to_dict()})


@app.route("/api/furniture/<item_id>", methods=["DELETE"])
def api_delete_furniture(item_id: str):
    item = furniture_by_id(item_id)
    if not item:
        return jsonify({"ok": False, "message": "家具不存在。"}), 404

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
        float(payload.get("height", 3.0)),
        payload.get("wall_color", "#f0efe9"),
        payload.get("floor_color", "#d8d0bd"),
        payload.get("wall_material", "白色瓷砖"),
    )
    STATE.message = msg
    return jsonify({"ok": ok, "message": msg, "room": asdict(room) if room else None, "state": STATE.to_dict()})


@app.route("/api/room/<room_id>", methods=["PATCH"])
def api_update_room(room_id: str):
    room = room_by_id(room_id)
    if not room:
        return jsonify({"ok": False, "message": "房间不存在。"}), 404

    STATE.push_history()
    ok, msg = update_room(room, request.get_json(silent=True) or {})
    STATE.message = msg
    return jsonify({"ok": ok, "message": msg, "room": asdict(room), "state": STATE.to_dict()})


@app.route("/api/room/<room_id>", methods=["DELETE"])
def api_delete_room(room_id: str):
    room = room_by_id(room_id)
    if not room:
        return jsonify({"ok": False, "message": "房间不存在。"}), 404

    STATE.push_history()
    msg = delete_room(room)
    STATE.message = msg
    return jsonify({"ok": True, "message": msg, "state": STATE.to_dict()})


@app.route("/api/opening", methods=["POST"])
def api_add_opening():
    payload = request.get_json(silent=True) or {}
    room = room_by_id(payload.get("room_id"))
    if not room:
        return jsonify({"ok": False, "message": "房间不存在。"}), 404

    STATE.push_history()
    ok, msg, opening = add_opening(
        room,
        payload.get("type", "door"),
        payload.get("wall", "top"),
        float(payload.get("offset", 0.3)),
        float(payload.get("width", 0.9)),
        payload.get("name"),
        payload.get("height"),
        payload.get("sill"),
        payload.get("color"),
        payload.get("material"),
    )
    STATE.message = msg
    return jsonify({"ok": ok, "message": msg, "opening": asdict(opening) if opening else None, "state": STATE.to_dict()})


@app.route("/api/opening/<opening_id>", methods=["PATCH"])
def api_update_opening(opening_id: str):
    opening = opening_by_id(opening_id)
    if not opening:
        return jsonify({"ok": False, "message": "门窗不存在。"}), 404

    STATE.push_history()
    ok, msg = update_opening(opening, request.get_json(silent=True) or {})
    STATE.message = msg
    return jsonify({"ok": ok, "message": msg, "opening": asdict(opening), "state": STATE.to_dict()})


@app.route("/api/opening/<opening_id>", methods=["DELETE"])
def api_delete_opening(opening_id: str):
    opening = opening_by_id(opening_id)
    if not opening:
        return jsonify({"ok": False, "message": "门窗不存在。"}), 404

    STATE.push_history()
    msg = delete_opening(opening)
    STATE.message = msg
    return jsonify({"ok": True, "message": msg, "state": STATE.to_dict()})

# AI生成户型图功能实现区域开始

def save_generated_floorplan_image(image_url=None, b64_json=None):
    """
    将火山方舟生成的图片保存到本地 static/generated_floorplans，
    避免前端直接加载外部临时图片 URL 导致破图。
    """
    filename = f"floorplan_{int(time.time())}_{uuid.uuid4().hex[:8]}.png"
    save_path = os.path.join(GENERATED_FLOORPLAN_DIR, filename)

    if b64_json:
        try:
            image_bytes = base64.b64decode(b64_json)
            with open(save_path, "wb") as f:
                f.write(image_bytes)
            return url_for("static", filename=f"generated_floorplans/{filename}")
        except Exception as e:
            raise RuntimeError(f"保存 base64 户型图失败：{e}")

    if image_url:
        try:
            headers = {
                "User-Agent": "Mozilla/5.0",
                "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            }

            response = requests.get(image_url, headers=headers, timeout=60)
            if response.status_code >= 400:
                raise RuntimeError(f"下载图片失败：{response.status_code} {response.text[:200]}")

            content_type = response.headers.get("Content-Type", "")
            if "image" not in content_type.lower():
                # 有些临时链接不一定返回标准 content-type，所以这里只做弱校验
                if not response.content or len(response.content) < 1000:
                    raise RuntimeError(f"返回内容不是有效图片：{content_type}")

            with open(save_path, "wb") as f:
                f.write(response.content)

            return url_for("static", filename=f"generated_floorplans/{filename}")
        except Exception as e:
            raise RuntimeError(f"保存远程户型图失败：{e}")

    raise RuntimeError("没有可保存的户型图数据")

# 调用火山引擎文生图API的函数
def call_volcengine_image_api(params):
    api_key = os.getenv("VOLCENGINE_API_KEY_IMAGE", "").strip()
    model = get_model_id("DOUBAO_SEEDREAM_MODEL", "AI生成户型图/文生图")
    validate_model_binding("DOUBAO_SEEDREAM_MODEL", model, "AI生成户型图/文生图")
    base_url = os.getenv("VOLCENGINE_API_BASE", "https://ark.cn-beijing.volces.com/api/v3").rstrip("/")

    if not api_key:
        raise RuntimeError("缺少环境变量 VOLCENGINE_API_KEY_IMAGE")

    url = f"{base_url}/images/generations"

    payload = {
        "model": model,
        "prompt": params.get("prompt", ""),
        "size": params.get("size", "1920x1920"),
        "response_format": "url"
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, headers=headers, json=payload, timeout=90)

    if response.status_code >= 400:
        raise RuntimeError(f"火山方舟文生图调用失败：{response.status_code} {response.text[:500]}")

    return response.json()


# 生成户型图
def generate_floorplan(prompt):
    final_prompt = f"""
请根据以下需求生成一张清晰的室内户型参考图。

用户需求：
{prompt}

要求：
1. 俯视角平面户型图。
2. 房间边界清晰。
3. 家具布局清楚。
4. 风格简洁，适合装修系统参考。
5. 不要生成复杂文字，不要生成水印。
"""

    result = call_volcengine_image_api({
        "prompt": final_prompt,
        "size": "1920x1920"
    })

    image_url = None
    b64_json = None

    if isinstance(result, dict):
        data = result.get("data") or []
        if data and isinstance(data, list):
            first = data[0] or {}
            image_url = (
                first.get("url")
                or first.get("image_url")
                or first.get("image")
            )
            b64_json = (
                first.get("b64_json")
                or first.get("base64")
                or first.get("image_base64")
            )

    if not image_url and not b64_json:
        raise RuntimeError(f"文生图接口返回中没有可用图片数据：{str(result)[:500]}")

    local_image_url = save_generated_floorplan_image(
        image_url=image_url,
        b64_json=b64_json
    )

    return {
        "image_url": local_image_url,
        "source_image_url": image_url,
        "raw": result
    }


# API接口：生成户型图

@app.route('/api/ai/generate_floorplan', methods=['POST'])
def api_generate_floorplan():
    data = request.json
    prompt = data.get('prompt', '')
    if not prompt:
        return jsonify({"ok": False, "message": "缺少prompt参数"})
    
    try:
        result = generate_floorplan(prompt)
        return jsonify({
            "ok": True,
            "result": result,
            "image_url": result.get("image_url") if isinstance(result, dict) else result
        })
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)})

# AI生成户型图功能实现区域结束


# AI解析户型图功能实现区域开始
# 1. 对接火山引擎API的路由
# 2. 户型图解析功能
# 3. 与现有导入接口的集成

# 火山引擎API配置
# 本文件不包含任何真实 API Key，适合上传 GitHub/Gitee 并部署到 Render。
VOLCENGINE_API_KEY_CHAT = os.getenv("VOLCENGINE_API_KEY_CHAT", "")
VOLCENGINE_API_KEY_IMAGE = os.getenv("VOLCENGINE_API_KEY_IMAGE", "")
VOLCENGINE_API_BASE = os.getenv("VOLCENGINE_API_BASE", "https://ark.cn-beijing.volces.com/api/v3")
DOUBAO_SEED_MODEL = os.getenv("DOUBAO_SEED_MODEL", "")  # 应用户型图/AI解析户型图模型 model ID
DOUBAO_SEEDREAM_MODEL = os.getenv("DOUBAO_SEEDREAM_MODEL", "")  # AI生成户型图/文生图模型 model ID

# 读取外置的Prompt文件（自动处理换行、格式，永不报错！）
def load_system_prompt():
    prompt_path = os.path.join(BASE_DIR, "system_prompt.txt")
    if not os.path.exists(prompt_path):
        return "你是装修系统的 AI 助手，请严格按要求输出 JSON。"
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()

# 加载Prompt
system_prompt = load_system_prompt()

# 调用火山引擎API的通用函数（添加日志）
def extract_json_object(content):
    """
    从模型返回内容中提取 JSON 对象。
    支持：
    1. 纯 JSON
    2. ```json ... ``` 包裹
    3. 前后带少量解释文字
    """
    if isinstance(content, dict):
        return content

    text = str(content or "").strip()

    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
        text = re.sub(r"```$", "", text).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1 or end <= start:
        raise RuntimeError(f"模型返回内容中没有 JSON 对象：{text[:500]}")

    json_text = text[start:end + 1]

    try:
        return json.loads(json_text)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"模型返回 JSON 解析失败：{e}；原始内容：{text[:500]}")

def call_volcengine_api(model, messages, temperature=0.2, max_tokens=2048, timeout=None, prefer_image_key=False):
    if prefer_image_key:
        api_key = (
            os.getenv("VOLCENGINE_API_KEY_IMAGE", "").strip()
            or os.getenv("VOLCENGINE_API_KEY_CHAT", "").strip()
            or os.getenv("ARK_API_KEY", "").strip()
        )
    else:
        api_key = (
            os.getenv("VOLCENGINE_API_KEY_CHAT", "").strip()
            or os.getenv("ARK_API_KEY", "").strip()
            or os.getenv("VOLCENGINE_API_KEY_IMAGE", "").strip()
        )
    base_url = os.getenv(
        "VOLCENGINE_API_BASE",
        "https://ark.cn-beijing.volces.com/api/v3"
    ).rstrip("/")

    if not api_key:
        raise RuntimeError("缺少环境变量 VOLCENGINE_API_KEY_CHAT、VOLCENGINE_API_KEY_IMAGE 或 ARK_API_KEY")

    if not model:
        raise RuntimeError("缺少模型参数 model")

    url = f"{base_url}/chat/completions"

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # Render/Gunicorn 默认 worker timeout 通常约 30 秒。
    # 这里默认 25 秒主动超时，让接口返回 JSON 错误，而不是让 worker 被杀后返回 HTML 500。
    safe_timeout = timeout or float(os.getenv("VOLCENGINE_TIMEOUT", "120"))

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=safe_timeout)
    except requests.Timeout:
        raise RuntimeError(
            f"火山方舟聊天/视觉模型调用超时（{safe_timeout}秒）。"
            "请确认当前调用的模型 model ID 正确，或在 Render 启动命令中增加 gunicorn --timeout 180。"
        )
    except requests.RequestException as e:
        raise RuntimeError(f"火山方舟聊天/视觉模型网络请求失败：{str(e)}")

    if response.status_code >= 400:
        error_text = response.text[:1200]
        lower_error = error_text.lower()
        if "does not support this api" in lower_error and "seedream" in lower_error:
            raise RuntimeError(
                "当前把 Doubao-Seedream 文生图模型传给了聊天/视觉解析接口。"
                "请检查 Render 环境变量：AI生成户型图使用 DOUBAO_SEEDREAM_MODEL；"
                "应用户型图/AI解析户型图必须使用 DOUBAO_SEED_MODEL，且该模型要支持 /chat/completions 图片理解。"
                f" 原始错误：HTTP {response.status_code} {error_text}"
            )
        raise RuntimeError(
            f"火山方舟聊天/视觉模型调用失败：HTTP {response.status_code} {error_text}"
        )

    try:
        return response.json()
    except ValueError:
        raise RuntimeError(f"火山方舟返回的不是 JSON：{response.text[:800]}")



def image_url_to_base64(image_url):
    """
    将前端传来的图片地址转换成 base64。
    支持：
    1. data:image/...;base64,...
    2. /static/generated_floorplans/xxx.png
    3. `https://xxx/static/generated_floorplans/xxx.png`
    4. 普通网络图片 URL
    """
    import base64
    from urllib.parse import urlparse

    if not image_url:
        raise RuntimeError("图片地址为空")

    if image_url.startswith("data:image/"):
        return image_url.split(",", 1)[1]

    parsed = urlparse(image_url)

    # 情况1：前端传的是 /static/xxx.png
    if image_url.startswith("/static/"):
        relative_path = image_url.lstrip("/")
        local_path = os.path.join(BASE_DIR, relative_path)

        if not os.path.exists(local_path):
            raise RuntimeError(f"本地图片不存在：{local_path}")

        with open(local_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    # 情况2：前端传的是完整 Render 地址，例如：
    # `https://ai-renovation-system.onrender.com/static/generated_floorplans/xxx.png`
    if parsed.path.startswith("/static/"):
        relative_path = parsed.path.lstrip("/")
        local_path = os.path.join(BASE_DIR, relative_path)

        if os.path.exists(local_path):
            with open(local_path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")

    # 情况3：普通外部网络图片
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    }

    response = requests.get(image_url, headers=headers, timeout=60)

    if response.status_code >= 400:
        raise RuntimeError(f"下载图片失败：HTTP {response.status_code}")

    if not response.content:
        raise RuntimeError("下载到的图片内容为空")

    return base64.b64encode(response.content).decode("utf-8")


def compact_base64_image(image_base64, max_side=1024, quality=78):
    """
    压缩给视觉模型的户型图，避免 Render/Gunicorn 默认超时：
    - 如果安装了 Pillow，会把图片最长边压到 max_side，并转成 JPEG base64；
    - 如果 Pillow 不可用或压缩失败，则返回原始 base64。
    """
    raw = (image_base64 or "").strip()
    if raw.startswith("data:image/"):
        raw = raw.split(",", 1)[1]

    try:
        from PIL import Image
        image_bytes = base64.b64decode(raw)
        img = Image.open(BytesIO(image_bytes)).convert("RGB")

        width, height = img.size
        longest = max(width, height)
        if longest > max_side:
            scale = max_side / float(longest)
            new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
            img = img.resize(new_size, Image.LANCZOS)

        out = BytesIO()
        img.save(out, format="JPEG", quality=quality, optimize=True)
        return base64.b64encode(out.getvalue()).decode("utf-8")
    except Exception as e:
        print(f"[WARN] compact_base64_image failed, use original image: {e}", flush=True)
        return raw


def make_safe_floorplan_fallback():
    """
    AI 解析失败时的安全兜底。
    注意：这不是最终 AI 结果，只用于保证前端不会因为模型超时/额度/参数错误而崩溃。
    """
    return normalize_ai_floorplan_result({
        "rooms": [
            {"id": "room_1", "name": "客厅", "x": 0, "y": 0, "width": 4.8, "depth": 4.0, "height": 3.0, "wall_color": "#f0efe9", "floor_color": "#d8d0bd"},
            {"id": "room_2", "name": "卧室", "x": 0, "y": 4.2, "width": 3.8, "depth": 3.4, "height": 3.0, "wall_color": "#f0efe9", "floor_color": "#d8d0bd"},
            {"id": "room_3", "name": "饭厅", "x": 5.0, "y": 0, "width": 3.0, "depth": 3.0, "height": 3.0, "wall_color": "#f0efe9", "floor_color": "#d8d0bd"},
            {"id": "room_4", "name": "阳台", "x": 3.9, "y": 4.2, "width": 2.6, "depth": 1.8, "height": 2.8, "wall_color": "#f0efe9", "floor_color": "#d8d0bd"},
        ],
        "furnitures": [],
        "openings": [
            {"id": "opening_1", "type": "window", "name": "窗", "room_id": "room_1", "wall": "top", "offset": 1.4, "width": 1.6, "height": 1.1, "sill": 0.9},
            {"id": "opening_2", "type": "door", "name": "门", "room_id": "room_3", "wall": "right", "offset": 1.2, "width": 0.9, "height": 2.1, "sill": 0},
        ],
        "message": "AI解析失败，已返回安全兜底户型。"
    })


def normalize_ai_floorplan_result(data):
    if not isinstance(data, dict):
        raise RuntimeError("AI 返回结果不是 JSON 对象")

    rooms = data.get("rooms") or []
    furnitures = data.get("furnitures") or []
    openings = data.get("openings") or []

    if not isinstance(rooms, list):
        rooms = []
    if not isinstance(furnitures, list):
        furnitures = []
    if not isinstance(openings, list):
        openings = []

    if not rooms:
        rooms = [
            {
                "id": "room_1",
                "name": "客厅",
                "x": 0,
                "y": 0,
                "width": 4.8,
                "depth": 4.0,
                "height": 3.0,
                "wall_color": "#ede6d8",
                "wall_material": "原木风"
            }
        ]

    normalized_rooms = []
    for index, room in enumerate(rooms):
        if not isinstance(room, dict):
            continue

        normalized_rooms.append({
            "id": str(room.get("id") or f"room_{index + 1}"),
            "name": str(room.get("name") or f"房间{index + 1}"),
            "x": float(room.get("x") or 0),
            "y": float(room.get("y") or 0),
            "width": max(1.0, float(room.get("width") or 3)),
            "depth": max(1.0, float(room.get("depth") or 3)),
            "height": max(0.1, float(room.get("height") or 3)),
            "wall_color": room.get("wall_color") or "#f0efe9",
            "floor_color": room.get("floor_color") or "#d8d0bd",
            "wall_material": room.get("wall_material") or "白色瓷砖",
        })

    default_room_id = normalized_rooms[0]["id"] if normalized_rooms else None

    normalized_furnitures = []
    for index, item in enumerate(furnitures):
        if not isinstance(item, dict):
            continue

        normalized_furnitures.append({
            "id": str(item.get("id") or f"furniture_{index + 1}"),
            "type": item.get("type") or "loungeSofa",
            "label": item.get("label") or "家具",
            "room_id": item.get("room_id") or default_room_id,
            "x": float(item.get("x") or 0),
            "y": float(item.get("y") or 0),
            "z": float(item.get("z") or 0),
            "width": max(0.2, float(item.get("width") or 1)),
            "depth": max(0.2, float(item.get("depth") or 1)),
            "height": max(0.1, float(item.get("height") or 0.8)),
            "rotation": float(item.get("rotation") or 0),
            "color": item.get("color") or "#6f7d8c",
            "material": item.get("material") or "布艺",
            "placement": item.get("placement") or "floor",
            "wall": item.get("wall") or None,
            "wall_offset": float(item.get("wall_offset") or 0),
            "mount_height": float(item.get("mount_height") or 1.5),
        })

    normalized_openings = []
    for index, item in enumerate(openings):
        if not isinstance(item, dict):
            continue

        normalized_openings.append({
            "id": str(item.get("id") or f"opening_{index + 1}"),
            "type": item.get("type") or "door",
            "name": item.get("name") or "门窗",
            "room_id": item.get("room_id") or default_room_id,
            "wall": item.get("wall") or "top",
            "offset": float(item.get("offset") or 0),
            "width": max(0.4, float(item.get("width") or 1)),
            "height": max(0.4, float(item.get("height") or 2.1)),
            "sill": float(item.get("sill") or 0),
            "color": item.get("color") or "#8b6a4d",
            "material": item.get("material") or "木纹",
        })

    return {
        "rooms": normalized_rooms,
        "furnitures": normalized_furnitures,
        "openings": normalized_openings,
        "message": data.get("message") or "户型解析成功"
    }

# ======================
# 【已修复】解析户型图（支持Base64，无损还原）
# ======================
def parse_floorplan(image_base64):
    # 应用户型图 / AI解析户型图：严格调用 DOUBAO_SEED_MODEL 的 model ID。
    # 注意：这里不再使用 DOUBAO_SEEDREAM_MODEL，避免把文生图模型误用于解析。
    model = get_model_id("DOUBAO_SEED_MODEL", "应用户型图/AI解析户型图")
    validate_model_binding("DOUBAO_SEED_MODEL", model, "应用户型图/AI解析户型图")

    # 压缩图片可以显著降低多模态调用耗时，避免 Render 线上 500/worker timeout。
    compact_image_base64 = compact_base64_image(image_base64, max_side=1024, quality=78)

    prompt = """
You are a floorplan parser for an interior renovation app. Return JSON only.
Do not output markdown or explanations.

Keep the result compact and practical.
Priority: room layout and dimensions > doors/windows > wall/floor colors and wall material > major furniture.
Ignore tiny decorative objects. If uncertain, return a reasonable estimate instead of overthinking.

Output schema:
{
  "rooms": [{"id":"room_1","name":"living room","x":0,"y":0,"width":4.8,"depth":4.0,"height":3.0,"wall_color":"#f0efe9","floor_color":"#d8d0bd","wall_material":"paint"}],
  "openings": [{"id":"opening_1","type":"window","name":"window","room_id":"room_1","wall":"top","offset":1.0,"width":1.5,"height":1.5,"sill":0.9,"color":"#79bdf8","material":"glass"}],
  "furnitures": [{"id":"furniture_1","type":"loungeSofa","label":"sofa","room_id":"room_1","x":0.5,"y":0.5,"z":0,"width":1.8,"depth":0.8,"height":0.8,"rotation":0,"color":"#6f7d8c","material":"fabric","placement":"floor"}],
  "message": "parsed"
}

Rules:
1. Use meters.
2. room_id must reference an existing room id.
3. wall must be one of top, right, bottom, left.
4. Every room must include id, name, x, y, width, depth, height.
5. If wall or floor colors are visible, output the closest hex colors.
6. If wall material is visible, output a short wall_material string.
7. Keep only major furniture items.
"""
    messages = [
        {
            "role": "system",
            "content": "你是一个只输出 JSON 的户型图解析模型。"
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": prompt
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{compact_image_base64}"
                    }
                }
            ]
        }
    ]

    result = call_volcengine_api(
        model=model,
        messages=messages,
        temperature=0.1,
        max_tokens=4096,
        prefer_image_key=False
    )

    content = (
        result.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
    )

    if not content:
        raise RuntimeError(f"模型没有返回可解析内容：{str(result)[:500]}")

    data = extract_json_object(content)
    return normalize_ai_floorplan_result(data)



# ======================
# 【已修复】API接口（接收Base64图片或URL）
# ======================
@app.route('/api/ai/parse_floorplan', methods=['POST'])
def api_parse_floorplan():
    try:
        data = request.get_json(silent=True) or {}

        image_base64 = (data.get("image_base64") or "").strip()
        image_url = (data.get("image_url") or "").strip()

        if image_base64.startswith("data:image/"):
            image_base64 = image_base64.split(",", 1)[1]

        if image_url and not image_base64:
            try:
                image_base64 = image_url_to_base64(image_url)
            except Exception as e:
                return jsonify({
                    "ok": False,
                    "message": f"后端读取户型图失败：{str(e)}"
                }), 200

        if not image_base64:
            return jsonify({
                "ok": False,
                "message": "缺少图片参数，请先生成或上传户型图。"
            }), 200

        try:
            result = parse_floorplan(image_base64)
            return jsonify({
                "ok": True,
                "result": result
            }), 200
        except Exception as e:
            import traceback
            traceback.print_exc()

            return jsonify({
                "ok": False,
                "message": f"AI????????{str(e)}"
            }), 200
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "ok": False,
            "message": f"户型解析接口异常：{str(e)}"
        }), 200

# AI解析户型图功能实现区域结束


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
