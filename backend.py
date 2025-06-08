import sys
import os
from fastapi.middleware.cors import CORSMiddleware  # 新增导入
# 将项目根目录添加到Python搜索路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

from pydantic import BaseModel
import uuid
from utils.db_utils import DatabaseManager
from agent.transaction_agent import TransactionAgent
from agent.strategy_agent import StrategyAgent
from agent.knowledge_agent import Knowledge_Graph_Agent
from fastapi import FastAPI, Depends, HTTPException
from typing import Annotated
from fastapi.security import OAuth2PasswordBearer
import secrets
from datetime import datetime, timedelta, timezone  


from jose import jwt

SECRET_KEY = "xV7z2B9dR5tF8gH3jK6sP4mN7wQ2eA8rT5yU9fD1sL"  # 替换为长随机字符串
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # Token 有效期（分钟）

# 假设已有的认证逻辑（实际需根据项目调整）
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class UserRegister(BaseModel):
    username: str
    password: str
    initial_funds: float = 10000.0


# ========== 用户服务 ==========
@app.post("/register")
def register(user: UserRegister):
    """用户注册接口"""
    db = DatabaseManager()
    try:
        if db.get_user_by_username(user.username):
            raise HTTPException(400, "用户名已存在")
        
        user_id = str(uuid.uuid4())
        success = db.add_user(
            username=user.username,
            uid=user_id,
            funds=user.initial_funds,
            hashed_password=user.password
        )
        
        if not success:
            raise HTTPException(500, "注册失败")
        return {"user_id": user_id}
    finally:
        db.close()

class UserLogin(BaseModel):
    username: str
    password: str

@app.post("/login")
def login(credentials: UserLogin):
    """用户登录接口"""
    db = DatabaseManager()
    try:
        user = db.get_user_by_username(credentials.username)
        
        if not user or user[3] != credentials.password:
            raise HTTPException(401, "认证失败")
        
        # 生成 JWT Token
        user_id = user[0]  # 用户 ID（从数据库查询结果中获取）
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        token_data = {"sub": user_id, "exp": expire}
        token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)
        
        return {
            "user_id": user_id,
            "balance": user[2],
            "risk_profile": user[4] if len(user) > 4 else "balanced",
            "token": token  # 新增 Token 字段
        }
    finally:
        db.close()  

async def get_current_user_id(token: Annotated[str, Depends(oauth2_scheme)]):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])  # 与编码算法一致
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="无效 Token（缺少用户ID）")
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token 已过期")
    except jwt.InvalidSignatureError:
        raise HTTPException(status_code=401, detail="Token 签名验证失败（可能被篡改）")
    except jwt.JWTError as e:
        raise HTTPException(status_code=401, detail=f"Token 解码失败: {str(e)}")

# 新增：登录状态验证接口
@app.get("/check-auth")
def check_auth(user_id: Annotated[str, Depends(get_current_user_id)]):
    """验证登录状态有效性"""
    return {
        "success": True,
        "user_id": user_id,
        "message": "登录状态有效"
    }

# ========== 核心功能接口 ==========
@app.get("/positions")
def get_user_positions(user_id: Annotated[str, Depends(get_current_user_id)]):
    print(f"接收到持仓请求，用户ID: {user_id}")
    db = DatabaseManager()
    try:
        # 检查用户是否存在
        if not db.get_user_by_uid(user_id):
            raise HTTPException(404, "用户不存在")
        
        positions = db.get_user_positions(user_id)
        if not positions:
            return {"data": []}  # 无持仓时返回空数组
    # 返回格式需与前端匹配（前端期望 result.data 是持仓列表）
        return {"data": positions}
    finally:
        db.close()

class TradeRequest(BaseModel):
    action: str  # buy/sell
    stock_code: str
    quantity: int
# ========== 核心功能接口 ==========
@app.post("/trade")
def execute_trade(request: TradeRequest, user_id: Annotated[str, Depends(get_current_user_id)]):
    """股票交易接口"""
    print(f"接收到交易请求，用户ID: {user_id}")
    db = DatabaseManager()
    try:
        if not db.get_user_by_uid(user_id):
            raise HTTPException(404, "用户不存在")
        if request.action == "buy":
           request.action = "买入"
        elif request.action == "sell":
            request.action = "卖出"
        else:
            raise HTTPException(400, "无效操作")
        request.stock_code = request.stock_code.strip().lower()
        instruction = f"{request.action}{request.quantity}股{request.stock_code}"
        print(f"交易指令: {instruction}")
        agent = TransactionAgent()
        result = agent.process_transaction(
            instruction,user_id
        )
        print(f"交易结果: {result}")
        # 新增结果判断：失败时返回明确信息
        if not result.get("success", False):
            # raise HTTPException(
            #     status_code=400,
            #     detail={"success": False, "message": f"交易失败: {result.get('message', '未知错误')}"}
            # )
            return {"success": False,"status_code":400, 
            "message": f"交易失败: {result.get("message", "未知错误")}"}
        return {"success": True, 
        "message": result.get("message", "交易成功"),
        "transaction_id": str(uuid.uuid4()),  # 新增交易唯一ID
        "timestamp": datetime.now().isoformat()
        } 
    finally:
        db.close()

class StrategyRequestBody(BaseModel):
    instruction: str  # 明确请求体包含 instruction 字段

@app.post("/strategy")
def generate_investment_strategy(request: StrategyRequestBody):
    """投资策略生成接口（修复后）"""
    print("enter strategy!!!")
    agent = StrategyAgent()
    strategy_content = agent.generate_strategy(request.instruction)  # 结果可能是成功字典或错误字典
    
    # 判断是否为错误状态
    if strategy_content.get("error", False):
        return {
            "success": False,
            "message": strategy_content["message"],
            "suggestions": strategy_content["suggestions"]
        }
    else:
        # 构造正常响应（原逻辑）
        print(f"正常返回: {strategy_content}")
        return {
            "success": True,
            "data": [
                {
                    "title": strategy_content["title"],
                    "description": strategy_content["description"],
                    "riskLevel": strategy_content["riskLevel"],
                    "annualReturn": strategy_content["annualReturn"],
                    "recommendedStocks": strategy_content["recommendedStocks"]
                }
            ]
        }


class KnowledgeRequest(BaseModel):
    question: str  # 明确请求体包含 instruction 字段

@app.post("/knowledge")
def answer_stock_question(request: KnowledgeRequest):
    """股票知识问答接口（优化版）"""
    import logging  # 新增日志模块导入
    
    logger = logging.getLogger(__name__)  # 获取模块级日志器
    try:
        # 参数校验：问题不能为空
        if not request.question.strip():
            return {
                "success": False,
                "code": 400,
                "message": "问题不能为空"
            }

        # 记录请求日志（替换为 logger）
        logger.info(f"知识问答请求: 问题={request.question}")  # 修改此处

        # 调用知识图谱代理
        agent = Knowledge_Graph_Agent()
        result = agent.answer_question(request.question)

        # 记录处理结果日志（替换为 logger）
        logger.info(f"知识问答结果: success={result['success']}, message={result['message']}")  # 修改此处

        # 标准化返回结构（与其他接口一致）
        return {
            "success": result["success"],
            "code": 200 if result["success"] else 500,
            "message": result["message"]
        }

    except Exception as e:
        # 捕获未知异常并记录（替换为 logger）
        error_msg = f"知识问答接口异常: {str(e)}"
        logger.error(error_msg)  # 修改此处
        return {
            "success": False,
            "code": 500,
            "message": "服务器内部错误，请稍后重试"
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
