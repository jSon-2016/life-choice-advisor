# Life Choice Advisor

Multi-Agent 人生选择顾问：**高考志愿** + **职业选择**，含前端问卷、RAG 知识库、Supervisor 辩论协调、JWT 认证与 MySQL 历史报告。

## 功能

| 模块 | 说明 |
|------|------|
| **前端问卷** | `/`、`/gaokao`、`/career`、`/history` 静态页面 |
| **Multi-Agent** | 并行专家 → 辩论 Supervisor → 总协调员 |
| **RAG** | `data/knowledge/` 院校、专业、行业知识库 |
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
| POST | `/api/gaokao/advise` | JWT | 高考志愿分析 + 存报告 |
| POST | `/api/career/advise` | JWT | 职业选择分析 + 存报告 |
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

## 命令行 Demo（不存库）

```powershell
python examples/demo_gaokao.py
python examples/demo_career.py
```

## 免责声明

AI 生成内容仅供参考，不构成正式志愿或职业咨询建议。
