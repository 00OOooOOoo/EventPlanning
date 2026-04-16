import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from ortools.sat.python import cp_model
from loader import load_data, check_volunteer_available
from llm_scorer import build_score_matrix

SKILL_THRESHOLD = 0.5  # 技能匹配分数低于这个值视为不满足技能要求

def run_solver():
    volunteers, time_slots, tasks, rules = load_data()

    V = list(volunteers["v_id"])
    T = list(tasks["task_id"])

    v_info = volunteers.set_index("v_id").to_dict("index")
    t_info = tasks.set_index("task_id").to_dict("index")

    # 计算语义分数矩阵
    scores = build_score_matrix(volunteers, tasks)

    model = cp_model.CpModel()

    # ── 决策变量 ──────────────────────────────────────────────
    assign = {}
    for v in V:
        for t in T:
            assign[v, t] = model.new_bool_var(f"assign_{v}_{t}")

    # ── HARD RULES ────────────────────────────────────────────

    # Hard Rule 1：时间 available
    for v in V:
        for t in T:
            t_start = t_info[t]["tasktime_start"]
            t_end   = t_info[t]["tasktime_end"]
            if not check_volunteer_available(v, t_start, t_end, time_slots):
                model.add(assign[v, t] == 0)

    # Hard Rule 2：同一时间只做一件事
    for v in V:
        for i, t1 in enumerate(T):
            for t2 in T[i+1:]:
                s1, e1 = t_info[t1]["tasktime_start"], t_info[t1]["tasktime_end"]
                s2, e2 = t_info[t2]["tasktime_start"], t_info[t2]["tasktime_end"]
                if s1 < e2 and s2 < e1:
                    model.add(assign[v, t1] + assign[v, t2] <= 1)

    # Hard Rule 3：staff_num（缺人标红）
    understaffed = {}
    for t in T:
        need = int(t_info[t]["staff_num"])
        understaffed[t] = model.new_int_var(0, need, f"understaffed_{t}")
        total_assigned = sum(assign[v, t] for v in V)
        model.add(total_assigned + understaffed[t] == need)

    # Hard Rule 4：v_risk=True 不能分配到 staff_num=1 的任务
    for v in V:
        if v_info[v]["v_risk"]:
            for t in T:
                if int(t_info[t]["staff_num"]) == 1:
                    model.add(assign[v, t] == 0)

    # Hard Rule 5：技能匹配——用语义分数替代字符串匹配
    for v in V:
        for t in T:
            required = str(t_info[t]["skill_required"]).strip()
            if required:  # 任务有技能要求
                skill_score = scores[v][t]["skill_match"]
                if skill_score < SKILL_THRESHOLD:
                    model.add(assign[v, t] == 0)

    # ── SOFT RULES（objective 函数）───────────────────────────
    # 把 0~1 的浮点分数转成整数（×1000），CP-SAT 只处理整数
    soft_scores = []
    for v in V:
        for t in T:
            s = scores[v][t]
            pref_pts     = int(s["preference_score"] * 1000) * 200
            unwill_pts   = int(s["unwilling_score"]  * 1000) * 100
            net = pref_pts - unwill_pts
            if net != 0:
                soft_scores.append(assign[v, t] * net)

    understaffed_penalty = sum(understaffed[t] * 10_000_000 for t in T)
    soft_total = sum(soft_scores) if soft_scores else 0

    model.maximize(soft_total - understaffed_penalty)

    # ── 求解 ──────────────────────────────────────────────────
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 30.0
    status = solver.solve(model)

    # ── 输出结果 ──────────────────────────────────────────────
    print("\n========== 排班结果 ==========")

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for t in T:
            t_name  = t_info[t]["task_name"]
            t_start = t_info[t]["tasktime_start"]
            t_end   = t_info[t]["tasktime_end"]
            need    = int(t_info[t]["staff_num"])
            assigned_volunteers = [v for v in V if solver.value(assign[v, t]) == 1]
            short = solver.value(understaffed[t])

            status_tag = "⚠ 缺人" if short > 0 else "✓"
            print(f"\n[{status_tag}] {t_name}  ({t_start.strftime('%H:%M')}–{t_end.strftime('%H:%M')})  需要 {need} 人")

            for v in assigned_volunteers:
                s = scores[v][t]
                print(f"     → {v_info[v]['v_name']} ({v})"
                      f"  技能={s['skill_match']:.2f}"
                      f"  偏好={s['preference_score']:.2f}"
                      f"  排斥={s['unwilling_score']:.2f}")
            if short > 0:
                print(f"     !! 仍缺 {short} 人，请手动补充")
    else:
        print("solver 无法找到可行方案，请检查数据")

    print("\n==============================")

if __name__ == "__main__":
    run_solver()

def run_solver_and_return() -> list:
    """
    供 main.py 调用的版本，返回结构化结果而不是打印。
    """
    volunteers, time_slots, tasks, rules = load_data()

    V = list(volunteers["v_id"])
    T = list(tasks["task_id"])
    v_info = volunteers.set_index("v_id").to_dict("index")
    t_info = tasks.set_index("task_id").to_dict("index")
    scores = build_score_matrix(volunteers, tasks)

    model  = cp_model.CpModel()

    assign = {}
    for v in V:
        for t in T:
            assign[v, t] = model.new_bool_var(f"assign_{v}_{t}")

    for v in V:
        for t in T:
            t_start = t_info[t]["tasktime_start"]
            t_end   = t_info[t]["tasktime_end"]
            if not check_volunteer_available(v, t_start, t_end, time_slots):
                model.add(assign[v, t] == 0)

    for v in V:
        for i, t1 in enumerate(T):
            for t2 in T[i+1:]:
                s1, e1 = t_info[t1]["tasktime_start"], t_info[t1]["tasktime_end"]
                s2, e2 = t_info[t2]["tasktime_start"], t_info[t2]["tasktime_end"]
                if s1 < e2 and s2 < e1:
                    model.add(assign[v, t1] + assign[v, t2] <= 1)

    understaffed = {}
    for t in T:
        need = int(t_info[t]["staff_num"])
        understaffed[t] = model.new_int_var(0, need, f"understaffed_{t}")
        model.add(sum(assign[v, t] for v in V) + understaffed[t] == need)

    for v in V:
        if v_info[v]["v_risk"]:
            for t in T:
                if int(t_info[t]["staff_num"]) == 1:
                    model.add(assign[v, t] == 0)

    for v in V:
        for t in T:
            required = str(t_info[t]["skill_required"]).strip()
            if required and scores[v][t]["skill_match"] < SKILL_THRESHOLD:
                model.add(assign[v, t] == 0)

    soft_scores = []
    for v in V:
        for t in T:
            s = scores[v][t]
            net = int(s["preference_score"] * 1000) * 200 - int(s["unwilling_score"] * 1000) * 100
            if net != 0:
                soft_scores.append(assign[v, t] * net)

    model.maximize(
        (sum(soft_scores) if soft_scores else 0) -
        sum(understaffed[t] * 10_000_000 for t in T)
    )

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 30.0
    solver.solve(model)

    results = []
    for t in T:
        assigned_list = []
        for v in V:
            if solver.value(assign[v, t]) == 1:
                s = scores[v][t]
                assigned_list.append({
                    "v_id":             v,
                    "v_name":           v_info[v]["v_name"],
                    "skill_match":      s["skill_match"],
                    "preference_score": s["preference_score"],
                    "unwilling_score":  s["unwilling_score"],
                })

        short = solver.value(understaffed[t])
        results.append({
            "task_id":      t,
            "task_name":    t_info[t]["task_name"],
            "time_start":   t_info[t]["tasktime_start"].strftime("%H:%M"),
            "time_end":     t_info[t]["tasktime_end"].strftime("%H:%M"),
            "staff_num":    int(t_info[t]["staff_num"]),
            "assigned":     assigned_list,
            "understaffed": int(short),
            "status":       "understaffed" if short > 0 else "ok",
            "1st_lead":     t_info[t]["1st_lead"],
            "2nd_lead":     t_info[t]["2nd_lead"],
        })

    return results