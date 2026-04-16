from ortools.sat.python import cp_model
from loader import load_data, check_volunteer_available

def run_solver():
    volunteers, time_slots, tasks, rules = load_data()

    # ── 基础数据准备 ──────────────────────────────────────────
    V = list(volunteers["v_id"])          # 所有 volunteer 的 ID 列表
    T = list(tasks["task_id"])            # 所有任务的 ID 列表

    # 用字典快速查找信息，不用每次都去 DataFrame 里搜索
    v_info  = volunteers.set_index("v_id").to_dict("index")
    t_info  = tasks.set_index("task_id").to_dict("index")

    model  = cp_model.CpModel()

    # ── 决策变量 ──────────────────────────────────────────────
    # assign[v][t] = 1 表示 volunteer v 被分配到任务 t，否则为 0
    # 这是 solver 需要决定的事情，每个格子都是一个 0/1 的选择
    assign = {}
    for v in V:
        for t in T:
            assign[v, t] = model.new_bool_var(f"assign_{v}_{t}")

    # ── HARD RULES ────────────────────────────────────────────

    # Hard Rule 1：volunteer 必须在任务时间段内 available
    for v in V:
        for t in T:
            t_start = t_info[t]["tasktime_start"]
            t_end   = t_info[t]["tasktime_end"]
            if not check_volunteer_available(v, t_start, t_end, time_slots):
                model.add(assign[v, t] == 0)  # 没空就强制不分配

    # Hard Rule 2：每位 volunteer 同一时间只能做一件事
    # 如果两个任务时间有重叠，volunteer 最多只能被分配其中一个
    for v in V:
        for i, t1 in enumerate(T):
            for t2 in T[i+1:]:
                s1, e1 = t_info[t1]["tasktime_start"], t_info[t1]["tasktime_end"]
                s2, e2 = t_info[t2]["tasktime_start"], t_info[t2]["tasktime_end"]
                # 判断时间是否重叠
                if s1 < e2 and s2 < e1:
                    model.add(assign[v, t1] + assign[v, t2] <= 1)

    # Hard Rule 3：每个任务的人数必须满足 staff_num 要求
    # 如果实在凑不够人，solver 会尽力而为（见 objective 部分）
    understaffed = {}
    for t in T:
        need = int(t_info[t]["staff_num"])
        understaffed[t] = model.new_int_var(0, need, f"understaffed_{t}")
        total_assigned = sum(assign[v, t] for v in V)
        # total_assigned + understaffed[t] == need
        # understaffed[t] > 0 说明这个任务缺人，最后会标红
        model.add(total_assigned + understaffed[t] == need)

    # Hard Rule 4：v_risk=True 的 volunteer 不能分配到 staff_num=1 的任务
    for v in V:
        if v_info[v]["v_risk"]:
            for t in T:
                if int(t_info[t]["staff_num"]) == 1:
                    model.add(assign[v, t] == 0)

    # Hard Rule 5：skill_required 必须匹配 v_skills
    for v in V:
        v_skills = str(v_info[v]["v_skills"]).lower()
        for t in T:
            required = str(t_info[t]["skill_required"]).strip().lower()
            if required:  # 任务有技能要求
                if required not in v_skills:  # volunteer 没有这个技能
                    model.add(assign[v, t] == 0)

    # ── SOFT RULES（加分项，放进 objective 函数）─────────────
    soft_scores = []

    for v in V:
        v_pref     = str(v_info[v]["v_preference"]).lower()
        v_unwilling = str(v_info[v]["v_not_willing"]).lower()

        for t in T:
            detail = str(t_info[t]["detail"]).lower()

            # Soft Rule：preference 匹配加分（weight=200）
            # 简单版本：看关键词是否出现在任务描述里
            pref_keywords = [w for w in v_pref.split() if len(w) > 1]
            pref_score = sum(1 for kw in pref_keywords if kw in detail)
            if pref_score > 0:
                soft_scores.append(assign[v, t] * 200 * pref_score)

            # Soft Rule：not_willing 匹配扣分（weight=100）
            unwilling_keywords = [w for w in v_unwilling.split() if len(w) > 1]
            unwilling_score = sum(1 for kw in unwilling_keywords if kw in detail)
            if unwilling_score > 0:
                soft_scores.append(assign[v, t] * (-100) * unwilling_score)

    # Soft Rule：减少换班——同一任务尽量让同一个人一直做
    # 这里用"分配人数的多样性"来近似：分配的人越少越好（在满足 staff_num 前提下）
    diversity_penalty = []
    for t in T:
        for v in V:
            diversity_penalty.append(assign[v, t])

    # ── Objective：最大化 soft scores，同时最小化缺人数 ──────
    # 缺人是最严重的问题，权重设很高（×10000）
    understaffed_penalty = sum(understaffed[t] * 10000 for t in T)
    soft_total = sum(soft_scores) if soft_scores else 0

    model.maximize(soft_total - understaffed_penalty)

    # ── 求解 ──────────────────────────────────────────────────
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 30.0  # 最多算 30 秒
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

            if assigned_volunteers:
                for v in assigned_volunteers:
                    print(f"     → {v_info[v]['v_name']} ({v})")
            if short > 0:
                print(f"     !! 仍缺 {short} 人，请手动补充")
    else:
        print("solver 无法找到可行方案，请检查数据（可能是时间冲突或技能要求过严）")

    print("\n==============================")

if __name__ == "__main__":
    run_solver()