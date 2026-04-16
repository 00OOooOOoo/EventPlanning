import pandas as pd

DATA_PATH = "data/mvp_codebook.xlsx"

def parse_time_col(series):
    return pd.to_datetime(
        series.astype(str).str.replace(r'\s+', ' ', regex=True).str.strip(),
        format="mixed",
        dayfirst=False
    )

def extract_profile_from_freetext(free_text: str) -> dict:
    """
    【接口预留】从 volunteer 的自由文本回答中提取结构化信息。
    
    MVP 阶段直接返回空值，后续接入 Kimi API 时只需替换这个函数内部的实现，
    loader.py 其他部分和 solver.py / llm_scorer.py 完全不需要改动。

    未来实现思路：
    - 调用 Kimi API，prompt 要求它从 free_text 里提取技能、偏好、排斥信息
    - 返回格式保持不变，solver 直接消费

    Args:
        free_text: volunteer 填写的自由文本，例如
                   "我喜欢拍照，有单反。不太擅长搬重物，腰不好。"

    Returns:
        dict，格式固定为：
        {
            "v_skills":      str,  # 提取出的技能
            "v_preference":  str,  # 提取出的偏好
            "v_not_willing": str   # 提取出的排斥项
        }
    """
    # ── MVP 阶段：直接返回空值，不影响现有流程 ── 
    #以后要接入 Kimi 的时候，只需要把注释掉的那段取消注释，
    #删掉 return {"v_skills": "", ...} 那三行，完成。
    return {
        "v_skills":      "",
        "v_preference":  "",
        "v_not_willing": ""
    }

    # ── 未来替换成这段（现在注释掉）──────────────
    # from openai import OpenAI
    # client = OpenAI(
    #     api_key=os.environ.get("MOONSHOT_API_KEY"),
    #     base_url="https://api.moonshot.cn/v1"
    # )
    # response = client.chat.completions.create(
    #     model="moonshot-v1-8k",
    #     messages=[{
    #         "role": "user",
    #         "content": f"""
    #         从下面这段 volunteer 的自我介绍中，提取三类信息。
    #         只返回 JSON，不要任何解释。
    #
    #         自我介绍：{free_text}
    #
    #         返回格式：
    #         {{
    #             "v_skills": "提取到的技能，用逗号分隔",
    #             "v_preference": "提取到的偏好描述",
    #             "v_not_willing": "提取到的不愿意做的事"
    #         }}
    #         """
    #     }]
    # )
    # import json
    # return json.loads(response.choices[0].message.content)

def load_data():
    volunteers = pd.read_excel(DATA_PATH, sheet_name="volunteer_profile")
    time_slots  = pd.read_excel(DATA_PATH, sheet_name="volunteer_time")
    tasks       = pd.read_excel(DATA_PATH, sheet_name="tasklist")
    rules       = pd.read_excel(DATA_PATH, sheet_name="rule_table")

    time_slots["v_start_time"] = parse_time_col(time_slots["v_start_time"])
    time_slots["v_end_time"]   = parse_time_col(time_slots["v_end_time"])
    tasks["tasktime_start"]    = parse_time_col(tasks["tasktime_start"])
    tasks["tasktime_end"]      = parse_time_col(tasks["tasktime_end"])

    for col in ["v_skills", "v_preference", "v_not_willing"]:
        volunteers[col] = volunteers[col].fillna("")
    volunteers["v_risk"] = volunteers["v_risk"].fillna(False).astype(bool)

    tasks["detail"]         = tasks["detail"].fillna("")
    tasks["skill_required"] = tasks["skill_required"].fillna("")
    for col in ["1st_lead", "2nd_lead"]:
        tasks[col] = tasks[col].fillna("")

    return volunteers, time_slots, tasks, rules


def check_volunteer_available(volunteer_id, task_start, task_end, time_slots):
    v_slots = time_slots[time_slots["v_id"] == volunteer_id]
    for _, slot in v_slots.iterrows():
        if slot["v_start_time"] <= task_start and slot["v_end_time"] >= task_end:
            return True
    return False


if __name__ == "__main__":
    volunteers, time_slots, tasks, rules = load_data()

    print(f"读取成功！")
    print(f"  Volunteer 数量：{len(volunteers)}")
    print(f"  时间段记录数：{len(time_slots)}")
    print(f"  任务数量：{len(tasks)}")
    print(f"  规则数量：{len(rules)}")
    print()
    print("--- Volunteers ---")
    print(volunteers[["v_id", "v_name", "v_risk"]].to_string(index=False))
    print()
    print("--- Tasks ---")
    print(tasks[["task_id", "task_name", "staff_num", "tasktime_start", "tasktime_end"]].to_string(index=False))