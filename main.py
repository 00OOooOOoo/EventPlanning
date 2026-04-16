from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from typing import Optional
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "matching"))

from loader import load_data, check_volunteer_available
from llm_scorer import build_score_matrix
from solver import run_solver_and_return

app = FastAPI(title="Event Planner Matching API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 数据模型（定义 API 接收和返回的数据格式）──────────────
class MatchingResult(BaseModel):
    task_id:   str
    task_name: str
    time_start: str
    time_end:   str
    staff_num:  int
    assigned:   list
    understaffed: int
    status:     str  # "ok" 或 "understaffed"


# ── 接口 1：触发排班 ───────────────────────────────────────
@app.post("/run-matching")
async def run_matching():
    try:
        # 把耗时计算放到线程池里跑，不会阻塞服务器
        results = await run_in_threadpool(run_solver_and_return)
        return {
            "status": "success",
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def health_check():
    return {"status": "ok", "message": "Event Planner API is running"}

@app.get("/data-summary")
def data_summary():
    try:
        volunteers, time_slots, tasks, rules = load_data()
        return {
            "volunteer_count": len(volunteers),
            "task_count":      len(tasks),
            "time_slot_count": len(time_slots),
            "rule_count":      len(rules),
            "volunteers": volunteers[["v_id", "v_name"]].to_dict("records"),
            "tasks":      tasks[["task_id", "task_name", "staff_num"]].to_dict("records"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── 接口 2：健康检查 ───────────────────────────────────────
@app.get("/")
def health_check():
    return {"status": "ok", "message": "Event Planner API is running"}


# ── 接口 3：获取当前数据概况 ───────────────────────────────
@app.get("/data-summary")
def data_summary():
    """
    返回当前 codebook 里的数据概况，
    方便前端确认数据是否正确加载。
    """
    try:
        volunteers, time_slots, tasks, rules = load_data()
        return {
            "volunteer_count": len(volunteers),
            "task_count":      len(tasks),
            "time_slot_count": len(time_slots),
            "rule_count":      len(rules),
            "volunteers": volunteers[["v_id", "v_name"]].to_dict("records"),
            "tasks":      tasks[["task_id", "task_name", "staff_num"]].to_dict("records"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))