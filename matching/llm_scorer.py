import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("MOONSHOT_API_KEY", ""),
    base_url="https://api.moonshot.cn/v1"
)

def compute_similarity(text_a: str, text_b: str) -> float:
    if not text_a.strip() or not text_b.strip():
        return 0.0
    try:
        response = client.chat.completions.create(
            model="moonshot-v1-8k",
            messages=[{
                "role": "user",
                "content": f"""请评估以下两段文字的语义相关程度，只返回一个0到1之间的小数，不要任何解释。
1代表完全相关，0代表完全无关。

文字A：{text_a}
文字B：{text_b}

只返回数字："""
            }],
            temperature=0
        )
        score = float(response.choices[0].message.content.strip())
        return max(0.0, min(1.0, score))
    except Exception:
        return 0.3  # 出错时返回中性分数

def score_volunteer_task(volunteer: dict, task: dict) -> dict:
    task_detail    = task.get("detail", "")
    skill_required = task.get("skill_required", "")
    v_skills       = volunteer.get("v_skills", "")
    v_preference   = volunteer.get("v_preference", "")
    v_not_willing  = volunteer.get("v_not_willing", "")

    skill_match      = compute_similarity(v_skills, skill_required) if skill_required else 1.0
    preference_score = compute_similarity(v_preference, task_detail)
    unwilling_score  = compute_similarity(v_not_willing, task_detail)

    return {
        "skill_match":      round(skill_match, 3),
        "preference_score": round(preference_score, 3),
        "unwilling_score":  round(unwilling_score, 3),
    }

def build_score_matrix(volunteers, tasks) -> dict:
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