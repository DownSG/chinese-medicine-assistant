from flask import Flask, render_template, request, session, jsonify
import openai
from models import db, ChatHistory, TCMKnowledge
import uuid
import os
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy

# 创建Flask应用
app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = os.environ.get('SECRET_KEY', 'chinese_medicine_assistant_secret_key_2024')

# 配置数据库
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///:memory:')
if app.config['SQLALCHEMY_DATABASE_URI'].startswith("postgres://"):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 60
}

# 禁用实例文件夹
app.config['INSTANCE_FOLDER'] = None

# 初始化数据库
db = SQLAlchemy()
db.init_app(app)

# 加载环境变量
load_dotenv()

# 获取环境变量
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    raise ValueError("未设置 OPENAI_API_KEY 环境变量")

# 初始化 OpenAI 客户端
client = openai.OpenAI(
    api_key=OPENAI_API_KEY,
    base_url='https://spark-api-open.xf-yun.com/v1',
    timeout=30.0
)

def init_db():
    with app.app_context():
        try:
            db.create_all()
            # 添加一些示例中医知识
            if not TCMKnowledge.query.first():
                sample_knowledge = [
                    TCMKnowledge(
                        term="阴阳",
                        definition="中医基本理论的核心概念，描述宇宙万物对立统一的两个方面",
                        category="基础理论"
                    ),
                    TCMKnowledge(
                        term="气血",
                        definition="人体生命活动的基本物质，气主推动运行，血主营养濡润",
                        category="基础理论"
                    ),
                ]
                for knowledge in sample_knowledge:
                    db.session.add(knowledge)
                db.session.commit()
        except Exception as e:
            print(f"数据库初始化错误: {str(e)}")

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/chat')
def index():
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    try:
        chat_history = ChatHistory.query.filter_by(session_id=session['session_id']).order_by(ChatHistory.timestamp).all()
    except Exception as e:
        print(f"数据库查询错误: {str(e)}")
        chat_history = []
    return render_template('index.html', generated_text='', error_message='', chat_history=chat_history)

@app.route('/generate', methods=['POST'])
def generate_text():
    prompt = request.form['prompt']
    
    try:
        # 检查输入是否包含中医术语
        tcm_terms = TCMKnowledge.query.all()
        relevant_terms = []
        for term in tcm_terms:
            if term.term in prompt:
                relevant_terms.append(term)
    except Exception as e:
        print(f"数据库查询错误: {str(e)}")
        relevant_terms = []
    
    # 构建提示词，包含相关术语解释
    internal_prompt = "请使用中医药的专业知识来回答这个问题。"
    if relevant_terms:
        internal_prompt += "\n相关术语解释："
        for term in relevant_terms:
            internal_prompt += f"\n{term.term}：{term.definition}"
    
    full_prompt = f"{internal_prompt}\n\n用户问题：{prompt}"

    try:
        completion = client.chat.completions.create(
            model='generalv3',
            messages=[{
                "role": "user",
                "content": full_prompt
            }]
        )
        
        generated_text = completion.choices[0].message.content
        
        # 保存到数据库
        try:
            chat_record = ChatHistory(
                user_input=prompt,
                assistant_response=generated_text,
                session_id=session['session_id']
            )
            db.session.add(chat_record)
            db.session.commit()
        except Exception as e:
            print(f"数据库保存错误: {str(e)}")
        
        try:
            chat_history = ChatHistory.query.filter_by(session_id=session['session_id']).order_by(ChatHistory.timestamp).all()
        except Exception as e:
            print(f"数据库查询错误: {str(e)}")
            chat_history = []
            
        return render_template('index.html', 
                             generated_text=generated_text, 
                             error_message='', 
                             chat_history=chat_history,
                             relevant_terms=relevant_terms)
    except Exception as e:
        error_message = f"API Error: {str(e)}"
        try:
            chat_history = ChatHistory.query.filter_by(session_id=session['session_id']).all()
        except Exception as e:
            print(f"数据库查询错误: {str(e)}")
            chat_history = []
        return render_template('index.html', 
                             generated_text='', 
                             error_message=error_message, 
                             chat_history=chat_history)

@app.route('/history')
def history():
    try:
        chat_history = ChatHistory.query.filter_by(session_id=session['session_id']).order_by(ChatHistory.timestamp).all()
    except Exception as e:
        print(f"数据库查询错误: {str(e)}")
        chat_history = []
    return jsonify([{
        'user': chat.user_input,
        'assistant': chat.assistant_response,
        'timestamp': chat.timestamp.isoformat()
    } for chat in chat_history])

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
else:
    # 为Vercel提供应用实例
    application = app