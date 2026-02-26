"""
Web API服务
提供RESTful接口供前端调用
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import os
import sys
import uvicorn

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 确保日志系统已初始化
try:
    from config import get
    get()  # 这会触发日志初始化
except Exception:
    # 如果配置加载失败，使用基本日志配置
    from config.logger import setup, LoggerSettings
    setup(LoggerSettings())

# 导入路由
from backend.api.routes.health import router as health_router
from backend.api.routes.frontend import router as frontend_router
from backend.api.routes.monitor import router as monitor_router
from backend.api.routes.stocks import router as stocks_router
from backend.api.routes.signals import router as signals_router
from backend.api.routes.my_stocks import router as my_stocks_router
from backend.api.routes.config import router as config_router
from backend.api.routes.backtest import router as backtest_router

# 导入依赖
from backend.api.dependencies import load_historical_backtest_jobs


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("API服务启动")
    count = load_historical_backtest_jobs()
    logger.info(f"加载了 {count} 个历史回测任务")
    yield
    # 关闭时执行
    logger.info("API服务关闭")


# 全局变量
app = FastAPI(
    title="A股涨停ETF溢价监控API",
    description="监控个股涨停，通过ETF获取溢价的辅助工具",
    version="1.0.0",
    lifespan=lifespan
)

# 添加CORS支持
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 注册所有路由
app.include_router(health_router)
app.include_router(frontend_router)
app.include_router(monitor_router)
app.include_router(stocks_router)
app.include_router(signals_router)
app.include_router(my_stocks_router)
app.include_router(config_router)
app.include_router(backtest_router)


def start_server(host: str = "0.0.0.0", port: int = 8000):
    """
    启动API服务器

    Args:
        host: 监听地址
        port: 监听端口
    """
    logger.info(f"启动API服务器: http://{host}:{port}")
    logger.info(f"API文档: http://{host}:{port}/docs")

    uvicorn.run(
        "backend.api.app:app",
        host=host,
        port=port,
        reload=True,  # 开发模式，生产环境设为False
        log_level="info"
    )


if __name__ == "__main__":
    start_server()
