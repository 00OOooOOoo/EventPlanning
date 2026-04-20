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

# 全局缓存排班结果，避免每次查询都重新计算
_cached_results = None

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
    global _cached_results
    try:
        # 把耗时计算放到线程池里跑，不会阻塞服务器
        results = await run_in_threadpool(run_solver_and_return)
        _cached_results = results
        return {
            "status": "success",
            "results": results
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

#── 接口 4：Volunteer界面 ───────────────────────────────
@app.get("/volunteer/{v_id}")
def get_volunteer_tasks(v_id: str):
    """
    根据 v_id 返回该 volunteer 的个人任务详情。
    包括：任务信息、负责人、同组队友、交接人。
    """
    global _cached_results
    
    # 如果还没有排班结果，提示先生成
    if _cached_results is None:
        raise HTTPException(
            status_code=400,
            detail="排班结果尚未生成，请先在 Organizer 页面点击「生成排班方案」"
        )

    try:
        volunteers, time_slots, tasks, rules = load_data()

        # 确认 volunteer 存在
        v_row = volunteers[volunteers["v_id"] == v_id]
        if v_row.empty:
            raise HTTPException(status_code=404, detail=f"找不到 volunteer: {v_id}")

        v_name = str(v_row.iloc[0]["v_name"])

        # 找出该 volunteer 被分配到的所有任务
        my_tasks = []
        for task in _cached_results:
            assigned_ids = [v["v_id"] for v in task["assigned"]]
            if v_id not in assigned_ids:
                continue

            # 找队友（同任务的其他人）
            teammates = [
                {"v_id": v["v_id"], "v_name": v["v_name"]}
                for v in task["assigned"]
                if v["v_id"] != v_id
            ]

            task_rows = tasks[tasks["task_id"] == task["task_id"]]
            if task_rows.empty:
                continue
            task_row = task_rows.iloc[0]

            # 安全地读取每个字段，NaN 一律转成空字符串
            def safe_str(val):
                import math
                if val is None:
                    return ""
                try:
                    if math.isnan(float(val)):
                        return ""
                except (ValueError, TypeError):
                    pass
                return str(val).strip()

            my_tasks.append({
                "task_id":    task["task_id"],
                "task_name":  task["task_name"],
                "time_start": task["time_start"],
                "time_end":   task["time_end"],
                "location":   safe_str(task_row["location"]),
                "detail":     safe_str(task_row["detail"]),
                "1st_lead":   task.get("1st_lead", ""),
                "2nd_lead":   task.get("2nd_lead", ""),
                "teammates":  teammates,
            })

        return {
            "v_id":     v_id,
            "v_name":   v_name,
            "my_tasks": my_tasks
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))