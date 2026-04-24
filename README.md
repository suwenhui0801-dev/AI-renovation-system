# 🏠 AI装修模拟小游戏（Web版）

一个基于 Web 的装修模拟系统，支持 2D / 3D 实时编辑，并结合 AI 实现语音控制、户型理解与参考图生成。

👉 打开网页即可使用，无需安装。

***

# 🌐 在线体验

👉 <https://ai-renovation-system.onrender.com>

> 提示：首次打开可能有 10\~30 秒加载时间（服务器冷启动）

***

# ✨ 项目亮点

- 🧠 AI辅助设计：自然语言 → 户型解析 → 自动生成布局
- 🎮 游戏化交互：像小游戏一样拖拽、摆放、修改家具
- 🧭 双视图系统：2D 平面图 + 3D 俯视模型同步
- 🎤 语音控制：通过语音直接完成设计操作
- ✋ 手势识别：用手势抓取、移动、缩放家具

***

# 🎮 如何使用

## 基础操作

1. 创建房间：填写信息 → 点击新增
2. 添加家具：选择家具 → 点击放置
3. 编辑家具：点击家具 → 修改 / 删除
4. 添加门窗：选择类型 → 放置墙面

***

## 🤖 AI 指令

示例：

给客厅添加沙发\
删除卧室的床\
把沙发改成蓝色

***

## 🎤 语音输入

点击语音按钮，说出指令即可

***

## ✋ 手势控制

- 捏合 → 拖动家具
- 双手缩放 → 改变大小
- 👍 → 语音输入
- ✌️ → 删除对象

***

# 🧱 技术架构

前端（HTML + JS + Three.js）\
↓\
Flask 后端\
↓\
AI服务（火山方舟）

***

# 🚀 本地运行

## 克隆项目

git clone <https://github.com/suwenhui0801-dev/AI-renovation-system.git>
git clone <https://gitee.com/suu_1_0/AI-renovation-system.git>

## 安装依赖

pip install -r requirements.txt

## 配置环境变量

Windows（cmd）：

set ARK\_API\_KEY=你的火山方舟Key
set ARK\_MODEL=deepseek的模型ID
set VOLCENGINE\_API\_KEY\_CHAT=你的Key
set VOLCENGINE\_API\_KEY\_IMAGE=你的Key
set VOLCENGINE\_API\_BASE=<https://ark.cn-beijing.volces.com/api/v3>
set DOUBAO\_SEED\_MODEL=你的模型ID
set DOUBAO\_SEEDREAM\_MODEL=你的模型ID

## 启动

python app.py

访问：<http://localhost:5000>

***

# ☁️ 部署（Render）

Build Command:\
pip install -r requirements.txt

Start Command:\
gunicorn app:app

***

# 📁 项目结构

renovation\_game/\
├── pic/            # 图片资源
├── static/         # 静态资源
│   ├── models/     # 3D模型文件
│   ├── app.js      # 前端逻辑
│   └── style.css   # 前端样式
├── templates/      # HTML模板
│   └── index.html  # 主页面
├── app.py          # 主应用
├── main.py         # 辅助脚本
├── requirements.txt # 依赖项
├── system\_prompt.txt # AI系统提示
├── tmp.json        # 临时数据
└── README.md       # 项目说明

***

# 📦 可用设备

## 卧室家具

- 床（单人床、双人床、双层床）
- 衣柜
- 床头柜
- 书架
- 书桌

## 客厅家具

- 沙发（多种样式）
- 单人椅
- 茶几
- 边柜
- 电视柜

## 餐厅家具

- 餐桌
- 餐椅

## 厨房设备

- 橱柜
- 台面
- 冰箱
- 水槽

## 浴室设备

- 马桶
- 浴缸
- 洗手台
- 淋浴

## 其他设备

- 落地灯（圆形、方形）
- 壁灯
- 洗衣机
- 烘干机
- 衣帽架
- 植物
- 地毯

***

# ⚠️ 注意事项

- 需要 API Key 才能使用 AI
- Render 免费版会休眠
- 手势识别需要摄像头

***

