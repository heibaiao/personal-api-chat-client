# 模型图标说明

`assets/logos/` 下的 PNG 是各模型**品牌标识**的缩略图（34×34），仅用于在模型列表中
直观区分不同服务商。

- 所有名称、标识、商标归各自所有者所有（DeepSeek、OpenAI、Alibaba、Google、
  Anthropic、Moonshot、Zhipu、xAI、Mistral、Groq、MiniMax、Tencent、iFlytek 等）
- 本项目与上述公司**无任何隶属、合作或背书关系**
- 这些图标仅作**指示性使用**（identifying the corresponding service），不暗示授权
- 如权利人认为使用不当，请提交 Issue 或联系维护者，我们会立即移除对应图片

## 文件命名

| 文件 | 用途 |
|---|---|
| `<model_id>.png` | 已导入 API 时显示的彩色图标 |
| `<model_id>_dim.png` | 未导入 API 时显示的灰度图标 |

`model_id` 与 `deepseek_chat.py` 中 `MODEL_REGISTRY` 的 `id` 一一对应。
缺少图标时会自动回退为「品牌色 + 首字母」的字母徽标，功能不受影响。

## 自行替换

把 34×34 的 PNG 放进本目录、按上述规则命名即可，重启后生效，无需改代码。
