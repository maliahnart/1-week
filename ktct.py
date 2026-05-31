import streamlit as st
import docx
import re
import random
import time

# Cấu hình trang Streamlit
st.set_page_config(
    page_title="Quizizz Web Simulator",
    page_icon="⚡",
    layout="centered"
)

# ==========================================
# 1. PARSER - ĐỌC FILE WORD (.DOCX)
# ==========================================
def is_red_run(run) -> bool:
    try:
        color = run.font.color
        if color is None or color.type is None:
            return False
        rgb = color.rgb
        return rgb[0] >= 180 and rgb[1] < 100 and rgb[2] < 100
    except Exception:
        return False

def parse_docx(file_buffer) -> list:
    doc = docx.Document(file_buffer)
    questions = []
    current_week = "Chưa phân loại"
    current_q = None

    week_pat = re.compile(r"^tuần\s*\d+", re.IGNORECASE)
    q_pat    = re.compile(r"^câu\s*\d+\s*[;:.,\-]?\s*(.*)", re.IGNORECASE)
    
    # ĐÃ SỬA LỖI: Đổi [A-D] thành [A-Z] để nhận diện các đáp án E, F, G, H...
    option_pattern = re.compile(r"^([^a-zA-Z0-9]*)\s*([A-Z])\s*[\.\s)]\s*(.*)", re.IGNORECASE)

    def flush(q):
        if not q or len(q["answers"]) == 0:
            return
        q["is_multi"] = len(q["correct"]) > 1
        q.pop("_has_opts", None)
        questions.append(q)

    def make_q(week, text):
        return {
            "week":      week,
            "question":  text,
            "answers":   [],
            "correct":   [],
            "is_multi":  False,
            "points":    500,
            "timeLimit": 30,
            "_has_opts": False,
        }

    def build_char_colors(para):
        result = []
        for run in para.runs:
            red = is_red_run(run)
            for ch in run.text:
                result.append((ch, red))
        return result

    def line_is_red(line_text: str, full_text: str, char_colors: list) -> bool:
        pos = full_text.find(line_text)
        if pos < 0:
            return False
        red_count = total = 0
        for i in range(pos, min(pos + len(line_text), len(char_colors))):
            ch, is_red = char_colors[i]
            if ch.strip():
                total += 1
                if is_red:
                    red_count += 1
        return total > 0 and (red_count / total) >= 0.3

    for para in doc.paragraphs:
        raw_full = para.text.replace('\xa0', ' ')
        stripped = raw_full.strip()
        if not stripped:
            continue

        if week_pat.match(stripped):
            flush(current_q)
            current_q = None
            current_week = stripped
            continue

        lines = [l.strip() for l in raw_full.split('\n') if l.strip()]
        if not lines:
            continue

        q_match = q_pat.match(lines[0])
        if q_match:
            flush(current_q)
            current_q = make_q(current_week, q_match.group(1).strip())
            lines = lines[1:]

        if current_q is None:
            continue

        char_colors = build_char_colors(para)

        for line in lines:
            opt_match = option_pattern.match(line)
            if opt_match:
                current_q["_has_opts"] = True
                prefix = opt_match.group(1).strip()
                option_letter = opt_match.group(2).upper()
                option_text = opt_match.group(3).strip()

                current_q["answers"].append(f"{option_letter}. {option_text}")
                idx = len(current_q["answers"]) - 1

                if len(prefix) > 0 or line_is_red(line, raw_full, char_colors) or any(c in line for c in ['√', '✓', '✔']):
                    current_q["correct"].append(idx)
            else:
                if not current_q["_has_opts"]:
                    current_q["question"] += "\n" + line

    flush(current_q)
    return questions

# ==========================================
# 2. ĐỔI THEME VÀ CẤU HÌNH CSS ĐỘNG (HỖ TRỢ ĐẾN 8 MÀU ĐÁP ÁN)
# ==========================================
with st.sidebar:
    st.markdown("### 🎨 Tùy chỉnh giao diện")
    theme_choice = st.radio(
        "Chọn chế độ hiển thị:",
        options=["Sáng rực rỡ (Light Gamification)", "Tối huyền bí (Dark Gamification)"],
        index=0
    )

if theme_choice == "Sáng rực rỡ (Light Gamification)":
    st.markdown("""
    <style>
        .stApp {
            background-color: #F4F2F7 !important;
            color: #1F0833 !important;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }
        h1, h2, h3, h4, h5, h6, p, span, label { color: #1F0833 !important; }
        
        .q-box {
            background-color: #FFFFFF !important;
            padding: 35px;
            border-radius: 20px;
            border: 2px solid #E6E1EC !important;
            text-align: center;
            margin-bottom: 25px;
            box-shadow: 0 10px 30px rgba(31, 8, 51, 0.06) !important;
        }
        .q-text { font-size: 21px !important; font-weight: 700 !important; color: #1F0833 !important; line-height: 1.5; }
        
        div[data-testid="stButton"] > button {
            font-size: 18px !important; 
            font-weight: bold !important; 
            border-radius: 14px !important;
            padding: 20px !important; 
            transition: all 0.15s ease !important; 
            height: auto !important; 
            min-height: 90px !important;
            color: #FFFFFF !important; 
            box-shadow: 0 6px 16px rgba(0, 0, 0, 0.05) !important;
        }
        div[data-testid="stButton"] > button:hover { 
            transform: translateY(-3px) !important; 
            box-shadow: 0 10px 24px rgba(0,0,0,0.12) !important; 
        }
        
        /* Bảng màu phân biệt sắc nét cho 8 đáp án (Light Mode) */
        div.ans-0 div[data-testid="stButton"] > button { background-color: #8CA300 !important; border: 2px solid #738700 !important; } /* A */
        div.ans-1 div[data-testid="stButton"] > button { background-color: #7A3BFF !important; border: 2px solid #5F23E0 !important; } /* B */
        div.ans-2 div[data-testid="stButton"] > button { background-color: #FF6B00 !important; border: 2px solid #E05300 !important; } /* C */
        div.ans-3 div[data-testid="stButton"] > button { background-color: #00B0A1 !important; border: 2px solid #009487 !important; } /* D */
        div.ans-4 div[data-testid="stButton"] > button { background-color: #D81B60 !important; border: 2px solid #AD1457 !important; } /* E */
        div.ans-5 div[data-testid="stButton"] > button { background-color: #3F51B5 !important; border: 2px solid #303F9F !important; } /* F */
        div.ans-6 div[data-testid="stButton"] > button { background-color: #9C27B0 !important; border: 2px solid #7B1FA2 !important; } /* G */
        div.ans-7 div[data-testid="stButton"] > button { background-color: #E64A19 !important; border: 2px solid #D84315 !important; } /* H */
        div.ans-alt div[data-testid="stButton"] > button { background-color: #607D8B !important; border: 2px solid #455A64 !important; } /* Dự phòng */

        /* Kiểu dáng Checkbox Card dành cho câu chọn nhiều đáp án (Light Mode) */
        .checkbox-card {
            border-radius: 14px !important;
            padding: 15px 20px !important;
            margin-bottom: 12px !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05) !important;
            display: flex;
            align-items: center;
        }
        .checkbox-card label p {
            color: #FFFFFF !important;
            font-weight: bold !important;
            font-size: 17px !important;
        }
        div.ans-0.checkbox-card { background-color: #8CA300 !important; }
        div.ans-1.checkbox-card { background-color: #7A3BFF !important; }
        div.ans-2.checkbox-card { background-color: #FF6B00 !important; }
        div.ans-3.checkbox-card { background-color: #00B0A1 !important; }
        div.ans-4.checkbox-card { background-color: #D81B60 !important; }
        div.ans-5.checkbox-card { background-color: #3F51B5 !important; }
        div.ans-6.checkbox-card { background-color: #9C27B0 !important; }
        div.ans-7.checkbox-card { background-color: #E64A19 !important; }
        div.ans-alt.checkbox-card { background-color: #607D8B !important; }
    </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <style>
        .stApp {
            background-color: #2D1442 !important;
            color: #FFFFFF !important;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }
        h1, h2, h3, h4, h5, h6, p, span, label { color: #FFFFFF !important; }
        
        .q-box {
            background-color: #1F0833 !important;
            padding: 35px;
            border-radius: 16px;
            border: 1px solid #4A286D !important;
            text-align: center;
            margin-bottom: 25px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.2) !important;
        }
        .q-text { font-size: 21px !important; font-weight: 700 !important; color: #FFFFFF !important; line-height: 1.5; }
        
        div[data-testid="stButton"] > button {
            font-size: 18px !important; 
            font-weight: bold !important; 
            border-radius: 12px !important;
            padding: 20px !important; 
            transition: all 0.15s ease !important; 
            height: auto !important; 
            min-height: 100px !important;
            color: #FFFFFF !important; 
            box-shadow: 0 6px 16px rgba(0, 0, 0, 0.2) !important;
        }
        div[data-testid="stButton"] > button:hover { 
            transform: scale(1.02) !important; 
            box-shadow: 0 8px 20px rgba(0,0,0,0.3) !important; 
        }
        
        /* Bảng màu phân biệt sắc nét cho 8 đáp án (Dark Mode) */
        div.ans-0 div[data-testid="stButton"] > button { background-color: #A3B917 !important; border: 1px solid #C0D625 !important; }
        div.ans-1 div[data-testid="stButton"] > button { background-color: #8C52FF !important; border: 1px solid #A375FF !important; }
        div.ans-2 div[data-testid="stButton"] > button { background-color: #FF7A00 !important; border: 1px solid #FF9433 !important; }
        div.ans-3 div[data-testid="stButton"] > button { background-color: #14C3B4 !important; border: 1px solid #33D6C8 !important; }
        div.ans-4 div[data-testid="stButton"] > button { background-color: #E91E63 !important; border: 1px solid #F06292 !important; }
        div.ans-5 div[data-testid="stButton"] > button { background-color: #3F51B5 !important; border: 1px solid #5C6BC0 !important; }
        div.ans-6 div[data-testid="stButton"] > button { background-color: #9C27B0 !important; border: 1px solid #BA68C8 !important; }
        div.ans-7 div[data-testid="stButton"] > button { background-color: #FF5722 !important; border: 1px solid #FF7043 !important; }
        div.ans-alt div[data-testid="stButton"] > button { background-color: #607D8B !important; border: 1px solid #78909C !important; }

        /* Kiểu dáng Checkbox Card dành cho câu chọn nhiều đáp án (Dark Mode) */
        .checkbox-card {
            border-radius: 12px !important;
            padding: 15px 20px !important;
            margin-bottom: 12px !important;
            box-shadow: 0 6px 16px rgba(0,0,0,0.2) !important;
            display: flex;
            align-items: center;
        }
        .checkbox-card label p {
            color: #FFFFFF !important;
            font-weight: bold !important;
            font-size: 17px !important;
        }
        div.ans-0.checkbox-card { background-color: #A3B917 !important; }
        div.ans-1.checkbox-card { background-color: #8C52FF !important; }
        div.ans-2.checkbox-card { background-color: #FF7A00 !important; }
        div.ans-3.checkbox-card { background-color: #14C3B4 !important; }
        div.ans-4.checkbox-card { background-color: #E91E63 !important; }
        div.ans-5.checkbox-card { background-color: #3F51B5 !important; }
        div.ans-6.checkbox-card { background-color: #9C27B0 !important; }
        div.ans-7.checkbox-card { background-color: #FF5722 !important; }
        div.ans-alt.checkbox-card { background-color: #607D8B !important; }
    </style>
    """, unsafe_allow_html=True)


# ==========================================
# 3. QUẢN LÝ TRẠNG THÁI (SESSION STATE)
# ==========================================
if "phase" not in st.session_state:
    st.session_state.phase = "welcome"
    st.session_state.all_questions = []
    st.session_state.quiz_questions = []
    st.session_state.current_index = 0
    st.session_state.score = 0
    st.session_state.streak = 0
    st.session_state.correct_count = 0
    st.session_state.incorrect_count = 0
    st.session_state.start_time = 0
    st.session_state.show_feedback = False
    st.session_state.feedback_data = {}

# ==========================================
# 4. ĐIỀU HƯỚNG MÀN HÌNH
# ==========================================

# --- MÀN HÌNH 1: CẤU HÌNH BÀI THI & CHỌN TUẦN ---
if st.session_state.phase == "welcome":
    st.write("")
    header_color = "#1F0833" if theme_choice.startswith("Sáng") else "#8C52FF"
    sub_color = "#7D7495" if theme_choice.startswith("Sáng") else "#E2DDE8"
    
    st.markdown(f"<h1 style='text-align: center; color: {header_color};'>QUIZIZZ LIVE ENGINE</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; color: {sub_color}; font-weight: bold;'>Trình mô phỏng phòng thi trắc nghiệm tương tác cao</p>", unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader("Kéo thả file Word đề thi (.docx) vào đây để bắt đầu:", type=["docx"])
    
    if uploaded_file is not None:
        try:
            questions = parse_docx(uploaded_file)
            if questions:
                st.session_state.all_questions = questions
                st.success(f"✓ Đã nạp thành công {len(questions)} câu hỏi.")
                
                # KHÔI PHỤC LẠI CHỨC NĂNG CHỌN ÔN TẬP THEO TUẦN
                weeks = sorted(list(set(q["week"] for q in questions)))
                selected_week = st.selectbox("Chọn nội dung tuần học ôn tập:", ["Tất cả các tuần"] + weeks)
                
                if st.button("🚀 BẮT ĐẦU CHƠI", use_container_width=True):
                    if selected_week == "Tất cả các tuần":
                        st.session_state.quiz_questions = questions.copy()
                    else:
                        st.session_state.quiz_questions = [q for q in questions if q["week"] == selected_week]
                    
                    random.shuffle(st.session_state.quiz_questions)
                    st.session_state.current_index = 0
                    st.session_state.score = 0
                    st.session_state.streak = 0
                    st.session_state.correct_count = 0
                    st.session_state.incorrect_count = 0
                    st.session_state.phase = "quiz"
                    st.session_state.start_time = time.time()
                    st.rerun()
            else:
                st.error("Không tìm thấy cấu trúc câu hỏi thích hợp trong tệp tin.")
        except Exception as e:
            st.error(f"Lỗi: {e}")

# --- MÀN HÌNH 2: TRÌNH DIỄN CÂU HỎI ---
elif st.session_state.phase == "quiz":
    idx = st.session_state.current_index
    questions = st.session_state.quiz_questions
    
    if idx >= len(questions):
        st.session_state.phase = "result"
        st.rerun()
        
    q = questions[idx]
    
    col_score1, col_score2, col_score3 = st.columns([1, 1, 1])
    label_color = "#7D7495" if theme_choice.startswith("Sáng") else "#E2DDE8"
    score_color = "#2E7D32" if theme_choice.startswith("Sáng") else "#A3B917"
    
    with col_score1:
        st.markdown(f"<h4 style='color: {label_color};'>Câu hỏi: {idx + 1}/{len(questions)}</h4>", unsafe_allow_html=True)
    with col_score2:
        st.markdown("<h4 style='color: #FF7A00; text-align: center;'>🔥 Streak: {}</h4>".format(st.session_state.streak), unsafe_allow_html=True)
    with col_score3:
        st.markdown(f"<h4 style='color: {score_color}; text-align: right;'>⭐ {st.session_state.score}</h4>", unsafe_allow_html=True)
        
    # Thẻ câu hỏi
    badge_bg = "#E6E1EC" if theme_choice.startswith("Sáng") else "#4A286D"
    badge_txt = "#1F0833" if theme_choice.startswith("Sáng") else "#FFFFFF"
    
    st.markdown(f"""
    <div class="q-box">
        <span style="background-color: {badge_bg}; padding: 5px 15px; border-radius: 20px; font-size: 11px; font-weight: bold; color: {badge_txt};">KẾT QUẢ ĐỌC CHUẨN</span>
        <p class="q-text" style="margin-top: 15px;">{q["question"]}</p>
    </div>
    """, unsafe_allow_html=True)
    
    answers = q["answers"]
    cols_layout = st.columns(2) if len(answers) > 1 else [st.container()]
    
    # Xử lý điều hướng luồng chọn đáp án (Đơn hay Nhiều đáp án)
    if q["is_multi"]:
        st.info("💡 Câu hỏi này có NHIỀU ĐÁP ÁN ĐÚNG. Hãy tích chọn các ô và nhấn nút Xác Nhận bên dưới!")
        selected_indices = []
        
        for i, ans in enumerate(answers):
            col_index = i % 2 if len(answers) > 1 else 0
            # Định vị ID class CSS rực rỡ lên đến 8 câu
            class_color = f"ans-{i}" if i < 8 else "ans-alt"
            
            with cols_layout[col_index]:
                st.markdown(f"<div class='{class_color} checkbox-card'>", unsafe_allow_html=True)
                checked = st.checkbox(f"{ans}", key=f"chk_{i}")
                if checked:
                    selected_indices.append(i)
                st.markdown("</div>", unsafe_allow_html=True)
                
        st.write("")
        # Nút xác nhận cho câu chọn nhiều đáp án
        if st.button("✔ XÁC NHẬN ĐÁP ÁN", use_container_width=True, type="primary"):
            selected_answer_list = selected_indices
            
            elapsed_time = time.time() - st.session_state.start_time
            time_limit = q["timeLimit"]
            correct_list = q["correct"]
            
            # So sánh khớp mảng đáp án
            is_correct = sorted(selected_answer_list) == sorted(correct_list)
            
            earned = 0
            if is_correct:
                st.session_state.correct_count += 1
                st.session_state.streak += 1
                remaining_seconds = max(0, int(time_limit - elapsed_time))
                time_bonus = remaining_seconds * 10
                earned = q["points"] + time_bonus
                st.session_state.score += earned
                feedback_text = f"✓ CHÍNH XÁC! Bạn đã chọn đúng tất cả các đáp án đúng và nhận +{earned} điểm!"
                feedback_color = "success"
            else:
                st.session_state.incorrect_count += 1
                st.session_state.streak = 0
                correct_letters = ", ".join([chr(65 + c) for c in correct_list])
                feedback_text = f"✗ CHƯA CHÍNH XÁC! Các đáp án đúng là: {correct_letters}"
                feedback_color = "error"
                
            st.session_state.feedback_data = {
                "text": feedback_text,
                "color": feedback_color,
                "correct_ans": correct_list
            }
            st.session_state.phase = "feedback"
            st.rerun()
    else:
        # Xử lý cho câu đơn đáp án
        selected_answer = None
        for i, ans in enumerate(answers):
            col_index = i % 2 if len(answers) > 1 else 0
            class_color = f"ans-{i}" if i < 8 else "ans-alt"
            
            with cols_layout[col_index]:
                st.markdown(f"<div class='{class_color}'>", unsafe_allow_html=True)
                if st.button(f"{ans}", key=f"ans_{i}", use_container_width=True):
                    selected_answer = i
                st.markdown("</div>", unsafe_allow_html=True)
                
        if selected_answer is not None:
            elapsed_time = time.time() - st.session_state.start_time
            time_limit = q["timeLimit"]
            correct_list = q["correct"]
            
            is_correct = selected_answer in correct_list
            
            earned = 0
            if is_correct:
                st.session_state.correct_count += 1
                st.session_state.streak += 1
                remaining_seconds = max(0, int(time_limit - elapsed_time))
                time_bonus = remaining_seconds * 10
                earned = q["points"] + time_bonus
                st.session_state.score += earned
                feedback_text = f"✓ CHÍNH XÁC! Bạn đã trả lời đúng và nhận +{earned} điểm!"
                feedback_color = "success"
            else:
                st.session_state.incorrect_count += 1
                st.session_state.streak = 0
                correct_letters = ", ".join([chr(65 + c) for c in correct_list])
                feedback_text = f"✗ CHƯA CHÍNH XÁC! Đáp án đúng là: {correct_letters}"
                feedback_color = "error"
                
            st.session_state.feedback_data = {
                "text": feedback_text,
                "color": feedback_color,
                "correct_ans": correct_list
            }
            st.session_state.phase = "feedback"
            st.rerun()

    st.write("")
    
    # Nút thoát sớm hoạt động song song ở cả hai chế độ
    col_end1, col_end2, col_end3 = st.columns([1, 2, 1])
    with col_end2:
        if st.button("🏳️ Kết thúc bài thi & Xem điểm ngay", use_container_width=True, type="secondary"):
            st.session_state.phase = "result"
            st.rerun()

# --- MÀN HÌNH 3: PHẢN HỒI ĐÚNG/SAI ---
elif st.session_state.phase == "feedback":
    data = st.session_state.feedback_data
    
    st.write("")
    if data["color"] == "success":
        st.success(data["text"])
    else:
        st.error(data["text"])
        
    st.write("")
    if st.button("TIẾP THEO ➔", use_container_width=True, type="primary"):
        st.session_state.current_index += 1
        st.session_state.phase = "quiz"
        st.session_state.start_time = time.time()
        st.rerun()

# --- MÀN HÌNH 4: KẾT QUẢ VÀ THỐNG KÊ CHI TIẾT ---
elif st.session_state.phase == "result":
    st.markdown("<h2 style='text-align: center;'>TỔNG KẾT BÀI LÀM</h2>", unsafe_allow_html=True)
    
    total_played = st.session_state.correct_count + st.session_state.incorrect_count
    accuracy = (st.session_state.correct_count / total_played * 100) if total_played > 0 else 0
    
    box_bg = "#FFFFFF" if theme_choice.startswith("Sáng") else "#1F0833"
    box_border = "#E2DDE8" if theme_choice.startswith("Sáng") else "#4A286D"
    text_main = "#2D1442" if theme_choice.startswith("Sáng") else "#FFFFFF"
    score_display = "#2E7D32" if theme_choice.startswith("Sáng") else "#A3B917"
    
    st.markdown(f"""
    <div style="background-color: {box_bg}; padding: 30px; border-radius: 16px; text-align: center; border: 1px solid {box_border}; box-shadow: 0 4px 15px rgba(0,0,0,0.03);">
        <p style="font-size: 14px; color: #7D7495; margin: 0; font-weight: bold;">TỔNG ĐIỂM HOÀN THÀNH</p>
        <h1 style="font-size: 52px; color: {score_display}; margin: 10px 0;">{st.session_state.score} pts</h1>
        <p style="color: {text_main}; font-size: 16px;">Tỷ lệ chính xác chung cuộc: <b>{accuracy:.1f}%</b></p>
    </div>
    """, unsafe_allow_html=True)
    
    st.write("")
    
    col_stat1, col_stat2 = st.columns(2)
    with col_stat1:
        st.info(f"🟢 Số câu trả lời đúng: {st.session_state.correct_count}")
    with col_stat2:
        st.error(f"🔴 Số câu trả lời sai: {st.session_state.incorrect_count}")
        
    st.write("")
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🔄 Làm lại bài ôn tập", use_container_width=True):
            random.shuffle(st.session_state.quiz_questions)
            st.session_state.current_index = 0
            st.session_state.score = 0
            st.session_state.streak = 0
            st.session_state.correct_count = 0
            st.session_state.incorrect_count = 0
            st.session_state.phase = "quiz"
            st.session_state.start_time = time.time()
            st.rerun()
            
    with col_btn2:
        if st.button("🏠 Trở lại trang chủ", use_container_width=True):
            st.session_state.phase = "welcome"
            st.rerun()