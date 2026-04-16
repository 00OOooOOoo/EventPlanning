from sentence_transformers import SentenceTransformer, util

# 模型只加载一次，避免每次调用都重新下载
_model = None

def get_model():
    global _model
    if _model is None:
        print("正在加载语义模型（首次加载需要几秒）...")
        _model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        print("模型加载完成")
    return _model


def compute_similarity(text_a: str, text_b: str) -> float:
    """
    计算两段文字的语义相似度，返回 0.0 到 1.0 之间的分数。
    1.0 = 完全一致，0.0 = 完全无关。
    """
    if not text_a.strip() or not text_b.strip():
        return 0.0  # 任一为空则返回 0，不加分也不扣分

    model = get_model()
    emb_a = model.encode(text_a, convert_to_tensor=True)
    emb_b = model.encode(text_b, convert_to_tensor=True)
    score = util.cos_sim(emb_a, emb_b).item()

    # cos_sim 范围是 -1 到 1，压缩到 0 到 1
    return max(0.0, float(score))


def score_volunteer_task(volunteer: dict, task: dict) -> dict:
    """
    给一对 volunteer-task 计算三个维度的语义分数。

    返回格式：
    {
        "skill_match":      0.0~1.0  技能是否匹配
        "preference_score": 0.0~1.0  preference 与 task detail 的匹配度
        "unwilling_score":  0.0~1.0  not_willing 与 task detail 的匹配度（越高越不应该分配）
    }
    """
    task_detail   = task.get("detail", "")
    skill_required = task.get("skill_required", "")

    v_skills      = volunteer.get("v_skills", "")
    v_preference  = volunteer.get("v_preference", "")
    v_not_willing = volunteer.get("v_not_willing", "")

    # 技能匹配：v_skills 和 skill_required 语义相似度
    skill_match = compute_similarity(v_skills, skill_required) if skill_required else 1.0

    # preference 匹配：volunteer 的偏好和任务描述的相似度
    preference_score = compute_similarity(v_preference, task_detail)

    # not_willing 匹配：volunteer 不想做的事和任务描述的相似度
    unwilling_score = compute_similarity(v_not_willing, task_detail)

    return {
        "skill_match":      round(skill_match, 3),
        "preference_score": round(preference_score, 3),
        "unwilling_score":  round(unwilling_score, 3),
    }


def build_score_matrix(volunteers, tasks) -> dict:
    """
    为所有 volunteer-task 组合计算分数，返回一个字典。

    格式：scores[v_id][task_id] = {"skill_match": x, "preference_score": x, "unwilling_score": x}
    """
    scores = {}
    v_list = volunteers.to_dict("records")
    t_list = tasks.to_dict("records")

    print(f"\n正在计算语义匹配分数（{len(v_list)} 个 volunteer × {len(t_list)} 个任务）...")

    for v in v_list:
        v_id = v["v_id"]
        scores[v_id] = {}
        for t in t_list:
            t_id = t["task_id"]
            scores[v_id][t_id] = score_volunteer_task(v, t)

    print("语义分数计算完成\n")
    return scores


if __name__ == "__main__":
    from loader import load_data

    volunteers, time_slots, tasks, rules = load_data()
    scores = build_score_matrix(volunteers, tasks)

    print("========== 语义匹配分数矩阵 ==========")
    print(f"{'volunteer':<8} {'task':<6} {'技能匹配':>8} {'偏好匹配':>8} {'排斥匹配':>8}")
    print("-" * 46)

    for v_id, task_scores in scores.items():
        v_name = volunteers.loc[volunteers["v_id"] == v_id, "v_name"].values[0]
        for t_id, s in task_scores.items():
            t_name = tasks.loc[tasks["task_id"] == t_id, "task_name"].values[0]
            print(f"{v_name:<8} {t_name:<8} "
                  f"{s['skill_match']:>8.3f} "
                  f"{s['preference_score']:>8.3f} "
                  f"{s['unwilling_score']:>8.3f}")
        print()