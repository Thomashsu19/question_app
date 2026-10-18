import os
import pandas as pd
import random
import datetime 
from flask import Flask, session, redirect, url_for, request, render_template_string

# Flask secret key for session management
app = Flask(__name__)
# 使用固定的 secret_key 確保本地端測試穩定
app.secret_key = 'my_super_secret_key_for_local_quiz' 

print("Libraries loaded and Flask app initialized.")

# Load the combined CSV data
try:
    combined_df = pd.read_csv('combined_tables.csv')
    print("Combined CSV loaded successfully.")
    
    # Basic data cleaning: drop rows where '試題' or '答案' are missing
    combined_df.dropna(subset=['試題', '答案', '章節'], inplace=True)
    combined_df['答案'] = combined_df['答案'].astype(str) 
    
    # --- 新增：選項換行處理 ---
    combined_df['試題'] = combined_df['試題'].astype(str)
    # 使用正則表達式，找出半形的 (1)~(4) 或全形的 （1）~（4），並在前面加上換行符號 \n
    combined_df['試題'] = combined_df['試題'].str.replace(r'(\([1-4]\))', r'\n\1', regex=True)
    combined_df['試題'] = combined_df['試題'].str.replace(r'(（[1-4]）)', r'\n\1', regex=True)
    # 把可能產生超過兩個以上的連續換行，縮減為單一換行，確保版面乾淨
    combined_df['試題'] = combined_df['試題'].str.replace(r'\n\s*\n', '\n', regex=True) 
    
    print(f"Total valid questions after cleaning: {len(combined_df)}")
    
except FileNotFoundError:
    print("Error: combined_tables.csv not found. Please ensure the previous step to merge CSVs was successful.")
    combined_df = pd.DataFrame()
except Exception as e:
    print(f"Error loading combined_tables.csv: {e}")
    combined_df = pd.DataFrame()


# --- Question Selection Logic ---
QUIZ_QUESTION_COUNT = 50
quiz_questions = []

if not combined_df.empty:
    total_available_questions = len(combined_df)

    if total_available_questions == 0:
        print("No valid questions to create a quiz.")
    elif total_available_questions <= QUIZ_QUESTION_COUNT:
        quiz_questions = combined_df.to_dict(orient='records')
        print(f"Selected all {len(quiz_questions)} available questions for the quiz.")
    else:
        chapter_counts = combined_df['章節'].value_counts()
        total_chapters = len(chapter_counts)

        questions_per_chapter = (chapter_counts / total_available_questions) * QUIZ_QUESTION_COUNT
        questions_per_chapter = questions_per_chapter.round().astype(int) 

        current_total_selected = questions_per_chapter.sum()
        difference = QUIZ_QUESTION_COUNT - current_total_selected

        if difference != 0:
            sorted_chapters = questions_per_chapter.sort_values(ascending=(difference < 0)).index.tolist()
            for _ in range(abs(difference)):
                if sorted_chapters:
                    chapter_to_adjust = sorted_chapters.pop(0)
                    questions_per_chapter[chapter_to_adjust] += (1 if difference > 0 else -1)

        for chapter, count in questions_per_chapter.items():
            actual_count = chapter_counts[chapter]
            questions_per_chapter[chapter] = min(count, actual_count)

        for chapter, count in questions_per_chapter.items():
            chapter_df = combined_df[combined_df['章節'] == chapter]
            if len(chapter_df) > 0:
                selected = chapter_df.sample(n=min(count, len(chapter_df)), random_state=42)
                quiz_questions.extend(selected.to_dict(orient='records'))

        random.shuffle(quiz_questions) 
        print(f"Selected {len(quiz_questions)} questions proportionally for the quiz.")
else:
    print("No questions available after loading or cleaning data.")


# --- Flask Web Application HTML Templates ---
HOME_TEMPLATE = """
<!doctype html>
<html lang="zh-TW">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
    <title>考試測驗</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f4f4f4; }
        .container { background-color: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,.1); max-width: 800px; margin: auto; }
        .question { margin-bottom: 20px; border: 1px solid #ddd; padding: 15px; border-radius: 5px; background-color: #e9ecef; }
        .question p { font-size: 1.1em; font-weight: bold; margin-bottom: 15px; white-space: pre-wrap; line-height: 1.6; }
        
        .options-container { margin-top: 15px; }
        .option-label { 
            display: block; 
            padding: 12px; 
            margin-bottom: 10px; 
            background-color: #f8f9fa; 
            border: 1px solid #ced4da; 
            border-radius: 5px; 
            cursor: pointer; 
            font-size: 1.1em;
            transition: background-color 0.2s;
        }
        .option-label:hover { background-color: #e2e6ea; }
        .option-label input[type="radio"] { margin-right: 15px; transform: scale(1.2); }
        
        .submit-btn { background-color: #007bff; color: white; padding: 12px 20px; border: none; border-radius: 5px; cursor: pointer; font-size: 1.1em; margin-top: 10px; }
        .submit-btn:hover { background-color: #0056b3; }
        .score { text-align: center; margin-top: 20px; font-size: 1.2em; }
        .note { font-size: 0.9em; color: #666; margin-top: 20px; border-top: 1px solid #eee; padding-top: 10px; }
        .download-notice { margin-top: 20px; padding: 15px; background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; border-radius: 5px;}
    </style>
</head>
<body>
    <div class="container">
        <h1>本地測驗系統</h1>
        {% if not quiz_started %}
            <p>點擊開始按鈕，開始 {{ num_questions }} 題測驗！</p>
            <form action="/start_quiz" method="post">
                <button class="submit-btn" type="submit">開始測驗</button>
            </form>
        {% else %}
            {% if question %}
                <p>題目 {{ current_question_num }} / {{ total_questions }}</p>
                <div class="question">
                    <p>{{ question['試題'] }}</p>
                </div>
                <form action="/answer" method="post">
                    <p>請點選您認為正確的選項：</p>
                    <div class="options-container">
                        <label class="option-label">
                            <input type="radio" name="user_answer" value="1" required> 選項 1
                        </label>
                        <label class="option-label">
                            <input type="radio" name="user_answer" value="2"> 選項 2
                        </label>
                        <label class="option-label">
                            <input type="radio" name="user_answer" value="3"> 選項 3
                        </label>
                        <label class="option-label">
                            <input type="radio" name="user_answer" value="4"> 選項 4
                        </label>
                    </div>
                    <button class="submit-btn" type="submit">提交答案</button>
                </form>
                <div class="note">章節: {{ question['章節'] }} | 題號: {{ question['題號'] }}</div>
            {% else %}
                <div class="score">
                    <h2>測驗結束！</h2>
                    <p>您的得分： {{ session.get('score', 0) }} / {{ session.get('total_questions', 0) }}</p>
                    
                    {% if csv_filename %}
                    <div class="download-notice">
                        <strong>錯題已匯出！</strong><br>檔案名稱：{{ csv_filename }}<br>已儲存至程式執行的資料夾中。
                    </div>
                    {% elif session.get('score', 0) == session.get('total_questions', 0) and session.get('total_questions', 0) > 0 %}
                    <div class="download-notice">
                        <strong>太厲害了！全對！沒有產生錯題紀錄。</strong>
                    </div>
                    {% endif %}
                    
                    <p>點擊 <a href="/restart">這裡</a> 重新開始。</p>
                </div>
            {% endif %}
        {% endif %}
    </div>
</body>
</html>
"""

RESULT_TEMPLATE = """
<!doctype html>
<html lang="zh-TW">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
    <title>測驗結果</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f4f4f4; }
        .container { background-color: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,.1); max-width: 800px; margin: auto; }
        .feedback { margin-top: 20px; padding: 15px; border-radius: 5px; }
        .correct { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .incorrect { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .original-question { margin-top: 15px; padding: 15px; background-color: #f0f0f0; border-radius: 5px; white-space: pre-wrap; line-height: 1.6;}
        .next-btn { display: block; width: fit-content; margin: 20px auto 0; background-color: #007bff; color: white; padding: 12px 24px; border: none; border-radius: 5px; cursor: pointer; font-size: 1.1em; text-decoration: none; }
        .next-btn:hover { background-color: #0056b3; }
    </style>
</head>
<body>
    <div class="container">
        <h1>測驗結果</h1>
        <div class="original-question">
            <h3>原題目:</h3>
            <p>{{ question['試題'] }}</p>
            <p>您的答案: <strong>{{ user_answer }}</strong></p>
            <p>正確答案: <strong>{{ correct_answer }}</strong></p>
        </div>

        {% if is_correct %}
            <div class="feedback correct">
                <p><strong>正確！</strong> 太棒了！</p>
            </div>
        {% else %}
            <div class="feedback incorrect">
                <p><strong>錯誤。</strong> (已記錄至錯題本)</p>
            </div>
        {% endif %}
        <a href="/" class="next-btn">下一題 / 返回首頁</a>
    </div>
</body>
</html>
"""

# --- Flask Routes ---
@app.route('/')
def index():
    if not quiz_questions:
        return render_template_string(HOME_TEMPLATE, quiz_started=False, num_questions=0)

    if 'quiz_started' not in session or not session['quiz_started']:
        return render_template_string(HOME_TEMPLATE, quiz_started=False, num_questions=len(quiz_questions))

    question_idx = session.get('question_idx', 0)
    if question_idx < len(quiz_questions):
        question = quiz_questions[question_idx]
        return render_template_string(HOME_TEMPLATE,
                                      quiz_started=True,
                                      question=question,
                                      current_question_num=question_idx + 1,
                                      total_questions=len(quiz_questions))
    else:
        csv_filename = session.get('csv_filename', None)
        return render_template_string(HOME_TEMPLATE, quiz_started=True, question=None, csv_filename=csv_filename)

@app.route('/start_quiz', methods=['POST'])
def start_quiz():
    if not quiz_questions:
        return "No questions loaded for the quiz."
    
    random.shuffle(quiz_questions)

    session['quiz_started'] = True
    session['question_idx'] = 0
    session['score'] = 0
    session['total_questions'] = len(quiz_questions)
    
    session['wrong_answers'] = [] 
    session.pop('csv_filename', None)
    
    return redirect(url_for('index'))

@app.route('/answer', methods=['POST'])
def answer():
    question_idx = session.get('question_idx', 0)
    if question_idx >= len(quiz_questions):
        return redirect(url_for('index'))

    question = quiz_questions[question_idx]
    user_answer = request.form['user_answer'].strip()
    correct_answer = str(question['答案']).strip()

    is_correct = (user_answer == correct_answer)

    if is_correct:
        session['score'] += 1
    else:
        wrong_list = session.get('wrong_answers', [])
        wrong_list.append({'idx': question_idx, 'user_answer': user_answer})
        session['wrong_answers'] = wrong_list

    session['question_idx'] = question_idx + 1

    # --- 產生 CSV 錯題表 ---
    if session['question_idx'] >= len(quiz_questions):
        wrong_list = session.get('wrong_answers', [])
        if wrong_list:
            now = datetime.datetime.now()
            file_time_str = now.strftime("%Y%m%d_%H%M%S")
            display_time_str = now.strftime("%Y-%m-%d %H:%M:%S")
            num_wrong = len(wrong_list)
            
            filename = f"錯題紀錄_{file_time_str}_錯{num_wrong}題.csv"
            
            export_data = []
            for item in wrong_list:
                q = quiz_questions[item['idx']]
                export_data.append({
                    '測驗時間': display_time_str,
                    '本次總錯題數': num_wrong,
                    '章節': q.get('章節', ''),
                    '題號': q.get('題號', ''),
                    '試題': q.get('試題', ''),
                    '正確答案': str(q.get('答案', '')),
                    '您的錯誤答案': item['user_answer']
                })
            
            pd.DataFrame(export_data).to_csv(filename, index=False, encoding='utf-8-sig')
            session['csv_filename'] = filename 

    return render_template_string(RESULT_TEMPLATE,
                                  question=question,
                                  user_answer=user_answer,
                                  correct_answer=correct_answer,
                                  is_correct=is_correct)

@app.route('/restart')
def restart():
    session.clear() 
    return redirect(url_for('index'))

if __name__ == '__main__':
    if quiz_questions:
        print(f"Starting quiz server on http://127.0.0.1:5000/")
        app.run(host='127.0.0.1', port=5000, debug=True)
    else:
        print("Cannot start quiz server: No questions available.")
