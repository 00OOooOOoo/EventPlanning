import pandas as pd

DATA_PATH = "data/mvp_codebook.xlsx"

def parse_time_col(series):
    return pd.to_datetime(
        series.astype(str).str.replace(r'\s+', ' ', regex=True).str.strip(),
        format="mixed",
        dayfirst=False
    )

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