# 大模型赋能的智能股票投资助手

### （Large Model-Enabled Intelligent Stock Investment Assistant）

## 项目简介

本项目是一个利用大模型技术实现的智能股票投资助手，旨在为投资者提供一站式的股票投资服务，包括股票数据查询、交易处理、风险评估、投资策略生成以及知识咨询等功能。通过整合多维股票数据、构建知识图谱挖掘公司间关联关系，结合大模型实现智能指令解析和策略生成，帮助投资者做出更科学、更明智的投资决策。

## 项目结构

```python
stock-assistant/
├── main.py                # 主入口（命令行交互）
├── backend.py             # FastAPI 后端服务
├── agent/                 # 智能代理模块
│   ├── transaction_agent.py   # 交易代理（处理买入/卖出指令）
│   ├── risk_assessment.py     # 风险评估（计算股票风险评分）
│   ├── knowledge_agent.py     # 知识图谱查询代理（回答股票/行业问题）
│   └── strategy_agent.py      # 策略生成代理（生成投资策略）
├── api/                   # 数据接口层
│   ├── stock_api.py         # 股票数据接口（实时/历史数据、行业信息）
│   └── transaction_api.py   # 交易接口（模拟交易执行）
├── knowledge_graph/       # 知识图谱模块
│   ├── kg_importer.py       # 知识图谱数据导入
│   └── kg_query.py          # 知识图谱查询（供应链/行业关系）
├── utils/                 # 工具模块
│   ├── db_utils.py          # 数据库管理（用户/交易记录）
│   └── logger.py            # 日志工具
├── data/                  # 数据存储
│   ├── stock_industry_data.csv  # 股票行业数据
│   └── web_data.py          # 网络数据获取（LLM辅助）
├── frontend_001/          # 前端页面（基础版）
│   ├── login.html           # 登录页
│   ├── trade.html           # 交易页
│   └── consult.html         # 咨询页
└── stock_assistant.db     # SQLite 数据库（用户/交易数据）
```

------

## 核心功能

### 1、指令解析与分发

- 用户输入指令后，InstructionParser 利用大模型解析指令类型，将其准确分发给对应的代理模块进行处理。

### 2、交易处理

- TransactionAgent 解析交易指令，获取股票实时价格，进行风险评估，若风险过高则拒绝交易，否则执行买入或卖出操作。

### 3、风险评估

- RiskAssessment 通过计算股票的波动率、市值和价格趋势等指标，动态调整权重，评估股票的风险。

### 4、策略生成

- StrategyAgent 根据用户的策略指令，结合市场数据和知识图谱信息，选择合适的行业和推荐股票，构建提示词，调用大模型生成投资策略。

### 5、知识查询

- KnowledgeAgent 提供知识图谱查询功能，能够回答用户关于股票的各类咨询问题，如供应链关系查询、行业信息查询等。

### 6、前端交互

- 前端页面提供用户注册、登录、股票交易、投资策略查询和股票咨询等功能，与后端接口进行交互，为用户提供良好的使用体验。

## 快速开始

### 1、环境要求
- Python 3.8+
- 依赖库： requirements.txt （需手动生成，包含fastapi、py2neo、openai等）
- 环境变量： DEEPSEEK_API_KEY （用于LLM调用）
### 2、配置文件设置

- 在 utils/config.py 中配置 API 密钥、数据库连接信息等。

### 3、安装与运行
1. 安装依赖：

   ```
   pip install -r requirements.txt
   ```

2. 启动后端服务：

   ```
   uvicorn backend:app --reload
   ```

3. 访问前端页面：
   打开 frontend_001/login.html 进行用户注册/登录

## 注意事项

- 部分数据为模拟数据，可能与实际情况存在偏差，可根据实际需求替换为真实数据。
- 大模型的调用可能存在延迟和成本问题，可优化模型调用方式，选择更合适的大模型。
- 前端页面的设计和交互功能可根据用户反馈进一步优化，提升用户体验。

## 贡献与反馈

欢迎对本项目进行贡献和反馈，你可以通过以下方式参与：

- 提交代码改进建议或修复问题。
- 提出新的功能需求和想法。
- 报告使用过程中遇到的问题和错误。