import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import google.generativeai as genai
from datetime import datetime, timedelta

st.set_page_config(page_title="24時間自己管理ダッシュボード", layout="wide")
st.title("🕒 24時間自己管理ダッシュボード")
st.caption("一日の時間の使い方を棒グラフで可視化し、無駄な時間を減らす自己管理ツール")

# ---------- セッション管理 ----------
if "weekly_logs" not in st.session_state:
    st.session_state.weekly_logs = {}
if "user_profile" not in st.session_state:
    st.session_state.user_profile = {
        "name": "",
        "target_sleep": 7,
        "target_study": 3
    }

# ---------- サイドバー ----------
st.sidebar.header("👤 ユーザー情報")
profile = st.session_state.user_profile
profile["name"] = st.sidebar.text_input("名前", value=profile["name"])
profile["target_sleep"] = st.sidebar.slider("目標睡眠時間 (h)", 4, 10, profile["target_sleep"])
profile["target_study"] = st.sidebar.slider("目標勉強時間 (h)", 1, 8, profile["target_study"])

# APIキーを secrets から取得し設定
api_key = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-2.0-flash-lite")

# ---------- カテゴリ ----------
categories = [
    "大学", "勉強", "バイト", "移動", "支度・準備", "遊び",
    "睡眠", "食事", "お風呂", "休憩", "スマホ", "覚えていない", "その他"
]
color_map = {
    "大学": "#B6D3FF", "勉強": "#ADD8E6", "バイト": "#90EE90", "移動": "#FFFFE0",
    "支度・準備": "#FFC0CB", "遊び": "#E6E6FA", "睡眠": "#CFB6B6",
    "食事": "#FFE4B5", "お風呂": "#A6E3E3", "休憩": "#F5DEB3",
    "スマホ": "#F08080", "覚えていない": "#D8BFD8", "その他": "#D7FBFB", "未入力": "#E1E1E1"
}

# ---------- タブ ----------
tab1, tab2, tab3 = st.tabs(["📝 入力", "📊 1日の流れ", "💡 AIアドバイス"])

# ==========================================================
# 📝 タブ1: 入力・編集・削除
# ==========================================================
with tab1:
    st.subheader("活動入力")
    selected_date = st.date_input("日付を選択", datetime.now().date())
    date_str = str(selected_date)

    if date_str not in st.session_state.weekly_logs:
        st.session_state.weekly_logs[date_str] = []

    with st.form("time_input_form"):
        category = st.selectbox("カテゴリ", categories)
        time_range = st.slider(
            "活動時間帯を選択 (0時~24時)", 0.0, 24.0, (8.0, 9.0), step=0.5
        )
        note = st.text_input("メモ（任意）")
        submitted = st.form_submit_button("記録する")
        if submitted:
            start_hour, end_hour = time_range
            if end_hour <= start_hour:
                st.warning("終了時間は開始時間より後にしてください。")
            else:
                st.session_state.weekly_logs[date_str].append({
                    "category": category,
                    "start_float": start_hour,
                    "end_float": end_hour,
                    "duration": end_hour - start_hour,
                    "note": note
                })
                st.success("記録しました！")
                st.rerun()

    # 編集・削除
    if st.session_state.weekly_logs[date_str]:
        st.subheader("📋 記録一覧")
        df_today = pd.DataFrame(st.session_state.weekly_logs[date_str]).sort_values("start_float").reset_index(drop=True)

        for idx, row in df_today.iterrows():
            with st.expander(f"{row['category']} | {row['start_float']:.1f} - {row['end_float']:.1f} 時"):
                new_category = st.selectbox(
                    f"カテゴリ (記録{idx+1})", categories, index=categories.index(row["category"]), key=f"cat_{idx}"
                )
                new_time_range = st.slider(
                    f"時間帯 (記録{idx+1})", 0.0, 24.0, (row["start_float"], row["end_float"]), step=0.5, key=f"time_{idx}"
                )
                new_note = st.text_input(f"メモ (記録{idx+1})", value=row["note"], key=f"note_{idx}")

                col1, col2 = st.columns(2)
                if col1.button("✅ 更新", key=f"update_{idx}"):
                    st.session_state.weekly_logs[date_str][idx] = {
                        "category": new_category,
                        "start_float": new_time_range[0],
                        "end_float": new_time_range[1],
                        "duration": new_time_range[1] - new_time_range[0],
                        "note": new_note
                    }
                    st.success("更新しました！")
                    st.rerun()
                if col2.button("🗑️ 削除", key=f"delete_{idx}"):
                    st.session_state.weekly_logs[date_str].pop(idx)
                    st.warning("削除しました！")
                    st.rerun()

# ==========================================================
# 📊 タブ2: 1週間の24時間タイムライン可視化
# ==========================================================
with tab2:
    st.subheader("🗓️ 過去1週間の24時間タイムライン一覧")

    today = datetime.now().date()
    dates_to_show = [str(today - timedelta(days=i)) for i in range(7)][::-1]

    data_exist = any(date in st.session_state.weekly_logs and st.session_state.weekly_logs[date] for date in dates_to_show)

    if data_exist:
        for date_str in dates_to_show:
            if date_str in st.session_state.weekly_logs and st.session_state.weekly_logs[date_str]:
                logs = sorted(st.session_state.weekly_logs[date_str], key=lambda x: x["start_float"])
                timeline = []
                current_time = 0.0

                for log in logs:
                    if log["start_float"] > current_time:
                        timeline.append({
                            "category": "未入力",
                            "start": current_time,
                            "end": log["start_float"],
                            "duration": log["start_float"] - current_time
                        })
                    timeline.append({
                        "category": log["category"],
                        "start": log["start_float"],
                        "end": log["end_float"],
                        "duration": log["end_float"] - log["start_float"]
                    })
                    current_time = log["end_float"]

                if current_time < 24.0:
                    timeline.append({
                        "category": "未入力",
                        "start": current_time,
                        "end": 24.0,
                        "duration": 24.0 - current_time
                    })

                timeline_df = pd.DataFrame(timeline)

                st.markdown(f"### {date_str}")

                fig = go.Figure()
                for _, row in timeline_df.iterrows():
                    fig.add_trace(go.Bar(
                        x=[row['duration']],
                        y=[''],
                        base=row['start'],
                        orientation='h',
                        name=row['category'],
                        marker_color=color_map.get(row['category'], '#cccccc'),
                        hovertemplate=f"{row['category']}<br>開始: {row['start']}h<br>終了: {row['end']}h<br>時間: {row['duration']}h<extra></extra>"
                    ))
                fig.update_traces(marker_line_width=0, width=500)
                fig.update_layout(
                    barmode='stack',
                    xaxis=dict(range=[0, 24], tickvals=list(range(0, 25, 2))),
                    yaxis=dict(showticklabels=False),
                    height=300,
                    showlegend=True,
                    title=f"{date_str} の24時間タイムライン"
                )
                st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("まだ記録がありません。タブ1から入力してください。")

# ==========================================================
# 💡 タブ3: AIアドバイス
# ==========================================================
with tab3:
    st.subheader("💡 AIによるアドバイス")

    if st.session_state.weekly_logs:
        total_sleep = total_study = total_unknown = total_smartphone = 0

        for logs in st.session_state.weekly_logs.values():
            for item in logs:
                if "睡眠" in item["category"]:
                    total_sleep += item["duration"]
                if "大学" in item["category"] or "勉強" in item["category"]:
                    total_study += item["duration"]
                if "スマホ" in item["category"]:
                    total_smartphone += item["duration"]
                if "覚えていない" in item["category"]:
                    total_unknown += item["duration"]

        days_logged = len(st.session_state.weekly_logs)
        avg_sleep = total_sleep / days_logged
        avg_study = total_study / days_logged
        avg_smartphone = total_smartphone / days_logged
        avg_unknown = total_unknown / days_logged

        st.write(f"📌 平均睡眠時間: {avg_sleep:.1f} 時間/日 (目標: {profile['target_sleep']} 時間)")
        st.write(f"📌 平均勉強時間: {avg_study:.1f} 時間/日 (目標: {profile['target_study']} 時間)")

        st.markdown("### ✏️ アドバイス")

        if api_key:
            if st.button("AIアドバイスを取得する"):
                prompt = f"""
{profile['name']}さんへ

以下はあなたの1週間の平均データです。
・平均睡眠時間: {avg_sleep:.1f} 時間/日
・平均勉強時間: {avg_study:.1f} 時間/日
・スマホ使用時間: {avg_smartphone:.1f} 時間/日
・覚えていない時間: {avg_unknown:.1f} 時間/日

目標を達成できているか確認し、フィードバックをしてください。
特に「スマホ」と「覚えていない時間」は無駄に過ごしている可能性が高いため、改善方法を含めて具体的な提案を優しく短く出してください。
"""
                response = model.generate_content(prompt)
                st.success("✅ AIアドバイスが生成されました！")
                st.markdown(response.text)
    else:
        st.info("記録がまだありません。")
