# Life Choice Advisor

Multi-Agent 人生选择顾问：**高考志愿** + **职业选择**，含前端问卷、RAG 知识库、Supervisor 辩论协调、JWT 认证与 MySQL 历史报告。

## 功能

| 模块 | 说明 |
|------|------|
| **前端问卷** | `/`、`/gaokao`、`/career`、`/history` 静态页面 |
| **Multi-Agent** | 并行专家 → 辩论 Supervisor → 总协调员 |
| **RAG** | Hybrid 检索（关键词 + Chroma 持久化向量）→ RRF 融合 → DashScope Rerank → 低置信拒答 + 引用编号 |
| **JWT** | 与 langchain-learn 相同测试账号 |
| **MySQL** | `t_advisory_report` 持久化报告 |

## 架构

```
并行阶段1（分数+心理 / 能力+心理）
    → 并行阶段2（专业+院校 / 行业+岗位）  + RAG 注入
    → 辩论 Supervisor（识别分歧、协调）
    → 总协调员（输出结构化报告 + JSON）
    → 保存 MySQL
```

## 快速开始

```powershell
cd D:\code\life-choice-advisor
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

copy .env.example .env
# 填入 DASHSCOPE_API_KEY、MySQL 配置
```

### 初始化数据库

在 MySQL `test1` 库执行（可与 langchain-learn 共用）：

```powershell
mysql -u root -p test1 < sql/init.sql
```

或启动应用时自动 `create_all`（首次运行会建表）。

### 启动

```powershell
uvicorn app.main:app --reload --port 8082
```

- 首页（登录 + 入口）：http://localhost:8082/
- API 文档：http://localhost:8082/docs
- 测试账号：`user1` / `vip01` / `admin01`，密码 `123456`

## API

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| POST | `/api/auth/login` | 否 | 登录获取 JWT |
| POST | `/api/report-import/parse` | JWT | 上传 PDF/图片，解析测评报告 |
| POST | `/api/gaokao/advise` | JWT | 高考志愿分析（body: `{ profile, imported_report_context? }`） |
| POST | `/api/gaokao/advise/stream` | JWT | **SSE 流式**：实时进度 + 最终报告 |
| POST | `/api/career/advise` | JWT | 职业选择分析 + 存报告 |
| POST | `/api/career/advise/stream` | JWT | **SSE 流式**职业分析 |
| GET | `/api/reports` | JWT | 历史报告列表 |
| GET | `/api/reports/{id}` | JWT | 报告详情 |

## 项目结构

```
life-choice-advisor/
├── static/                  # 前端问卷页面
├── data/knowledge/          # RAG 知识库（majors/schools/industries.txt）
├── sql/init.sql             # MySQL 建表
├── app/
│   ├── agents/              # Agent 执行器 + 提示词
│   ├── graphs/              # LangGraph Supervisor 工作流
│   ├── service/             # RAG、报告、咨询编排
│   ├── security/            # JWT
│   ├── db/                  # SQLAlchemy
│   └── controller/          # REST API
└── examples/                # 命令行 Demo（无需 JWT）
```

## RAG 知识库格式

`data/knowledge/*.txt` 每行：

```
关键词|内容描述
```

文件名即分类：`majors`、`schools`、`industries`。

### RAG 流水线

```
多路召回（关键词 + Chroma 向量）
  → RRF 融合
  → DashScope Rerank（gte-rerank / qwen3-rerank）
  → 相关度 < 阈值则拒答（不编造事实）
  → 注入 Agent 上下文（带 [1][2] 引用）
```

向量索引持久化在 `data/chroma/`（知识库变更后自动重建）。  
可在 `.env` 调整 `RAG_RERANK_THRESHOLD`（默认 0.35）、`RAG_RERANK_TOP_N` 等。

### 测评报告导入（免填问卷）

用户可直接上传 **PDF / 图片** 形式的心理或职业测评报告：

```text
PDF/图片 → 文字提取（PDF 文本 / Qwen-VL OCR）
  → 结构感知分块（段落/表格）+ 重叠切分（非固定 500 字硬切）
  → LLM 结构化抽取（维度得分、参考标准、MBTI 等）
  → 注入 Agent 上下文 + 自动预填画像
```

- 前端：页面顶部「导入测评报告」，成功后隐藏心理测评表单
- 若报告未含高考分数/省份，仅需补充少量基本信息
- 配置：`REPORT_CHUNK_SIZE=1200`、`REPORT_CHUNK_OVERLAP=250`

### 可观测与评测

- **SSE 进度**：前端默认走 `/advise/stream`，实时显示 RAG / 各 Agent 阶段
- **结构化日志**：`request_id`、Agent 耗时、Token 用量（见控制台）
- **迷你 Eval**：`python eval/run_eval.py` 回归 RAG 召回与拒答

## 命令行 Demo（不存库）

```powershell
python examples/demo_gaokao.py
python examples/demo_career.py
```

## 使用说明

本系统为 **智能辅助决策工具**，通过 Multi-Agent 协作与 RAG 知识库，为用户生成个性化分析报告。

报告内容供决策参考，填报志愿或职业选择时，请结合官方政策、院校招生简章及专业人士意见综合判断。
