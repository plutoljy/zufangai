"""
租房避坑局 FastAPI 主应用
提供合同上传、SSE流式分析、报告获取接口
"""
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import asyncio
import json
import uuid
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import settings
from graph.rental_analysis_graph import create_analysis_graph

app = FastAPI(title="租房避坑局 API", version="1.0.0")

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 内存存储 (简化版,生产环境应使用数据库)
contracts_store = {}
analysis_results = {}

class UploadResponse(BaseModel):
    contract_id: str
    status: str

@app.get("/")
async def root():
    """健康检查"""
    return {"status": "ok", "message": "租房避坑局 API"}

@app.post("/api/contracts/upload", response_model=UploadResponse)
async def upload_contract(
    file: UploadFile = File(...),
    location: Optional[str] = "beijing"
):
    """
    上传合同文件

    支持格式: txt, pdf, docx, jpg, png
    """
    try:
        # 生成合同ID
        contract_id = str(uuid.uuid4())

        # 读取文件内容
        content = await file.read()

        # 检查文件大小（50MB限制）
        MAX_FILE_SIZE = 50 * 1024 * 1024
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail="文件大小超过50MB限制")

        # 简化处理: 假设是文本文件
        # TODO: 后续添加PDF/图片解析
        try:
            text = content.decode('utf-8')
        except UnicodeDecodeError:
            text = content.decode('gbk', errors='ignore')

        # 保存到内存
        contracts_store[contract_id] = {
            "id": contract_id,
            "filename": file.filename,
            "text": text,
            "location": location,
            "status": "uploaded"
        }

        return UploadResponse(
            contract_id=contract_id,
            status="uploaded"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/contracts/{contract_id}/analyze")
async def analyze_contract(contract_id: str):
    """
    SSE流式分析合同
    """
    # 检查合同是否存在
    if contract_id not in contracts_store:
        raise HTTPException(status_code=404, detail="合同不存在")

    contract = contracts_store[contract_id]

    async def event_generator():
        try:
            # 发送开始事件
            yield f"data: {json.dumps({'type': 'analysis_started'}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.1)

            # 创建分析图
            app_graph = create_analysis_graph()

            # 初始状态
            initial_state = {
                "contract_text": contract["text"],
                "location": contract["location"]
            }

            # 执行分析 (同步转异步)
            loop = asyncio.get_event_loop()
            final_state = await loop.run_in_executor(
                None,
                app_graph.invoke,
                initial_state
            )

            # 发送Owl完成事件
            yield f"data: {json.dumps({'type': 'owl_analysis', 'data': {'entities': final_state['entities'], 'risk_count': len(final_state['risk_items'])}}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.1)

            # 发送Dog完成事件
            yield f"data: {json.dumps({'type': 'dog_retrieval', 'data': {'legal_docs': len(final_state['legal_references']), 'cases': len(final_state['case_references'])}}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.1)

            # 发送Beaver完成事件
            yield f"data: {json.dumps({'type': 'beaver_calculation', 'data': {'compliant': final_state['calculations']['deposit_check']['compliant']}}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.1)

            # 发送Cat完成事件
            yield f"data: {json.dumps({'type': 'cat_report', 'data': final_state['report']['summary']}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.1)

            # 保存结果
            analysis_results[contract_id] = final_state

            # 发送完成事件
            yield f"data: {json.dumps({'type': 'analysis_complete', 'contract_id': contract_id}, ensure_ascii=False)}\n\n"

        except Exception as e:
            error_data = {"type": "error", "message": str(e)}
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

@app.get("/api/contracts/{contract_id}/report")
async def get_report(contract_id: str):
    """获取分析报告"""
    if contract_id not in analysis_results:
        raise HTTPException(status_code=404, detail="报告不存在")

    result = analysis_results[contract_id]

    return {
        "contract_id": contract_id,
        "entities": result["entities"],
        "risk_items": result["risk_items"],
        "legal_references": result["legal_references"],
        "calculations": result["calculations"],
        "report_markdown": result["report"]["report_markdown"],
        "summary": result["report"]["summary"]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )
