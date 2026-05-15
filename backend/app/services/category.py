XIANYU_CATEGORIES = [
    {"id": "digital", "name": "数码", "icon": "laptop"},
    {"id": "clothing", "name": "服装", "icon": "skin"},
    {"id": "beauty", "name": "美妆", "icon": "experiment"},
    {"id": "home", "name": "家居", "icon": "home"},
    {"id": "toys", "name": "潮玩", "icon": "smile"},
    {"id": "baby", "name": "母婴", "icon": "team"},
    {"id": "sports", "name": "运动户外", "icon": "fire"},
    {"id": "luxury", "name": "奢侈品", "icon": "crown"},
    {"id": "books", "name": "图书音像", "icon": "read"},
    {"id": "pet", "name": "宠物", "icon": "github"},
    {"id": "car", "name": "二手车", "icon": "car"},
    {"id": "other", "name": "其他", "icon": "ellipsis"},
]

CUSTOM_INDUSTRIES = [
    "二手手机",
    "奢侈品包",
    "潮鞋",
    "盲盒",
    "相机镜头",
    "机械键盘",
    "文玩手串",
    "明星周边",
    "游戏卡带",
    "家具电器",
]


def get_all_categories():
    return {"xianyu": XIANYU_CATEGORIES, "industries": CUSTOM_INDUSTRIES}
