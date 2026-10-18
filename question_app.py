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

# Define the directory for correctly answered questions
correct_dir = '正確'
if not os.path.exists(correct_dir):
    os.makedirs(correct_dir)
    print(f"Created directory: {correct_dir} for correct answers.")

# Load the combined CSV data
try:
    combined_df = pd.read_csv('combined_tables.csv')
    print("Combined CSV loaded successfully.")

    # Basic data cleaning: drop rows where '試題' or '答案' are missing
    combined_df['答案'] = combined_df['答案'].astype(str)
    combined_df['試題'] = combined_df['試題'].astype(str).str.replace(r'\s+', '', regex=True)
    combined_df['答案'] = combined_df['答案'].str.replace(r'\s+', '', regex=True)

    # 使用正則表達式，找出半形的 (1)~(4) 或全形的 （1）~（4），並在前面加上換行符號 \n
    combined_df['試題'] = combined_df['試題'].str.replace(r'(\([1-4]\))', r'\n\1', regex=True)
    combined_df['試題'] = combined_df['試題'].str.replace(r'(（[1-4]）)', r'\n\1', regex=True)
    # 把可能產生超過兩個以上的連續換行，縮減為單一換行，確保版面乾淨
    combined_df['試題'] = combined_df['試題'].str.replace(r'\n\s*\n', '\n', regex=True)

    print(f"Total valid questions after cleaning: {len(combined_df)}")

    # --- Load previously correctly answered questions and filter them out ---
    correct_csv_files = [os.path.join(correct_dir, f) for f in os.listdir(correct_dir) if f.endswith('.csv')]
    if correct_csv_files:
        all_correct_dfs = []
        for f in correct_csv_files:
            try:
                all_correct_dfs.append(pd.read_csv(f))
            except Exception as e:
                print(f"Error loading previous correct answers from {f}: {e}")
        
        if all_correct_dfs:
            previously_correct_df = pd.concat(all_correct_dfs, ignore_index=True)
            # Use '題號' to identify unique questions
            previously_correct_unique = previously_correct_df[['題號']].drop_duplicates()
            
            # Filter combined_df to exclude questions already answered correctly
            merged = combined_df.merge(
                previously_correct_unique,
                on=['題號'],
                how='left',
                indicator=True
            )
            combined_df = merged[merged['_merge'] == 'left_only'].drop(columns=['_merge'])
            print(f"Removed {len(merged) - len(combined_df)} previously correct questions. Remaining: {len(combined_df)}")

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
    else:
        # Directly sample 50 questions randomly
        num_to_select = min(QUIZ_QUESTION_COUNT, total_available_questions)
        quiz_questions = combined_df.sample(n=num_to_select).to_dict(orient='records')
        print(f"Selected {len(quiz_questions)} questions randomly for the quiz.")
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

                    {% if wrong_csv_filename %}
                    <div class="download-notice">
                        <strong>錯題已匯出！</strong><br>檔案名稱：{{ wrong_csv_filename }}<br>已儲存至程式執行的資料夾中。
                    </div>
                    {% endif %}

                    {% if correct_csv_filename %}
                    <div class="download-notice">
                        <strong>答對題目已匯出！</strong><br>檔案名稱：{{ correct_csv_filename }}<br>已儲存至程式執行的資料夾中。
                    </div>
                    {% elif session.get('score', 0) == session.get('total_questions', 0) and session.get('total_questions', 0) > 0 %}
                    <div class="download-notice">
                        <strong>太厲害了！全對！所有題目皆已記錄為答對。</strong>
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
        .correct { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }.
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
        wrong_csv_filename = session.get('wrong_csv_filename', None)
        correct_csv_filename = session.get('correct_csv_filename', None)
        return render_template_string(HOME_TEMPLATE, quiz_started=True, question=None, wrong_csv_filename=wrong_csv_filename, correct_csv_filename=correct_csv_filename)

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
    session['correct_answers'] = [] # Initialize list for correct answers
    session.pop('wrong_csv_filename', None)
    session.pop('correct_csv_filename', None)

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
        # Record correct answer
        correct_list = session.get('correct_answers', [])
        correct_list.append({'idx': question_idx})
        session['correct_answers'] = correct_list
    else:
        # Record wrong answer
        wrong_list = session.get('wrong_answers', [])
        wrong_list.append({'idx': question_idx, 'user_answer': user_answer})
        session['wrong_answers'] = wrong_list

    session['question_idx'] = question_idx + 1

    # --- 產生 CSV 錯題表與答對題目表 ---
    if session['question_idx'] >= len(quiz_questions):
        now = datetime.datetime.now()
        file_time_str = now.strftime("%Y%m%d_%H%M%S")
        display_time_str = now.strftime("%Y-%m-%d %H:%M:%S")

        # Export wrong answers
        wrong_list = session.get('wrong_answers', [])
        if wrong_list:
            num_wrong = len(wrong_list)
            wrong_filename = os.path.join('錯題', f"錯題紀錄_{file_time_str}_錯{num_wrong}題.csv") # Changed output path to extracted_tables for consistency
            
            export_wrong_data = []
            for item in wrong_list:
                q = quiz_questions[item['idx']]
                export_wrong_data.append({
                    '測驗時間': display_time_str,
                    '本次總錯題數': num_wrong,
                    '章節': q.get('章節', ''),
                    '題號': q.get('題號', ''),
                    '試題': q.get('試題', ''),
                    '正確答案': str(q.get('答案', '')),
                    '您的錯誤答案': item['user_answer']
                })

            pd.DataFrame(export_wrong_data).to_csv(wrong_filename, index=False, encoding='utf-8-sig')
            session['wrong_csv_filename'] = wrong_filename

        # Export correct answers
        correct_list = session.get('correct_answers', [])
        if correct_list:
            num_correct = len(correct_list)
            correct_filename = os.path.join('正確', f"正確紀錄_{file_time_str}_對{num_correct}題.csv")
            
            export_correct_data = []
            for item in correct_list:
                q = quiz_questions[item['idx']]
                export_correct_data.append({
                    '測驗時間': display_time_str,
                    '本次總答對題數': num_correct,
                    '章節': q.get('章節', ''),
                    '題號': q.get('題號', ''),
                    '試題': q.get('試題', ''),
                    '正確答案': str(q.get('答案', '')),
                    '您的回答': str(q.get('答案', '')) # For correct answers, user's answer is the correct one
                })
            pd.DataFrame(export_correct_data).to_csv(correct_filename, index=False, encoding='utf-8-sig')
            session['correct_csv_filename'] = correct_filename

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
