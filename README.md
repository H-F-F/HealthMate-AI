# HealthMate-AI

面向健康管理场景的智能助手 Demo，基于 `Streamlit + LangChain + 通义千问` 构建，集成多轮问答、症状分诊、健康档案、天气联动和本地持久化。

## 项目亮点

- 健康问答与分诊一体化，支持高危症状优先拦截
- 结构化输出，回答内容、风险等级、依据和建议分开呈现
- 健康管理面板覆盖 BMI、饮水、步数、饮食、睡眠
- 天气数据联动健康建议，接口失败自动回退到演示数据
- 用户登录、档案和对话记录本地保存，支持多轮恢复
- 内置评测脚本，便于验证规则分流和模型链路

## 我做了什么

- 设计了“问答 + 分诊 + 工具调用”的健康助手主链路
- 用规则引擎优先处理胸痛、呼吸困难、高烧等急症
- 搭建了可持久化的用户档案和对话系统
- 将天气、步数、饮水和饮食数据接入健康建议生成
- 补充了离线回退和评测机制，提高可用性与可验证性

## 技术栈

- `Streamlit`
- `LangChain`
- `Tongyi / DashScope`
- `Amap API`
- `pytest`

## 核心能力

### 智能问答

支持围绕睡眠、饮食、运动、压力等主题进行多轮对话，并返回结构化健康建议。

### 风险分诊

对高危症状进行关键词优先识别，直接输出就医提醒，避免普通问答误导用户。

### 健康管理

支持体重计划、饮食记录、每日步数、饮水和睡眠管理，并生成个性化建议。

### 天气联动

接入高德地图天气接口，根据实时天气调整运动和防护建议；无接口时自动回退演示数据。

### 数据持久化

按用户保存账号、健康档案和聊天记录，支持重新登录后恢复历史状态。

## 运行方式

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

创建 `.env`：

```env
DASHSCOPE_API_KEY=your_key_here
AMAP_API_KEY=your_amap_key_here
DASHSCOPE_MODEL=qwen-plus
```

启动应用：

```powershell
streamlit run app.py
```

## 评测

```powershell
python scripts/evaluate_assistant.py --mode triage
python scripts/evaluate_assistant.py --mode live
```

## 项目结构

```text
app.py                # Streamlit 入口
agent/                # Agent、Prompt、工具
services/             # 认证、对话、分诊、天气、健康计划
ui/                   # 页面组件
data/                 # 本地数据
scripts/              # 评测脚本
tests/                # 单元测试
```

## 备注

- 没有 `DASHSCOPE_API_KEY` 时，聊天链路无法调用模型
- 没有 `AMAP_API_KEY` 时，天气页会使用本地演示数据
- 高危症状会直接进入急症提示，不再生成普通建议
