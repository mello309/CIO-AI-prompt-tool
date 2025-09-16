from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from config import Config
import google.generativeai as genai
import json
import os
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
import pickle
import uuid

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config.from_object(Config)

# Initialize Gemini with error handling
api_key = app.config['GEMINI_API_KEY']
if not api_key:
    raise ValueError("GEMINI_API_KEY not found in environment variables. Please check your .env file.")
genai.configure(api_key=api_key)

# Initialize upload folder
Config.init_app(app)

# Store uploaded files info
uploaded_files = {}

# Memory storage files
MEMORY_FILE = 'app_memory.pkl'
CONVERSATION_FILE = 'conversations.pkl'

# Initialize memory storage
def load_memory():
    try:
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, 'rb') as f:
                return pickle.load(f)
    except:
        pass
    return {
        'user_preferences': {},
        'prompt_improvements': {},
        'feedback_history': [],
        'conversation_patterns': {}
    }

def save_memory(memory_data):
    try:
        with open(MEMORY_FILE, 'wb') as f:
            pickle.dump(memory_data, f)
    except Exception as e:
        print(f"Error saving memory: {e}")

def load_conversations():
    try:
        if os.path.exists(CONVERSATION_FILE):
            with open(CONVERSATION_FILE, 'rb') as f:
                return pickle.load(f)
    except:
        pass
    return {}

def save_conversations(conversations):
    try:
        with open(CONVERSATION_FILE, 'wb') as f:
            pickle.dump(conversations, f)
    except Exception as e:
        print(f"Error saving conversations: {e}")

# Load existing memory
app_memory = load_memory()
conversations = load_conversations()

# Memory enhancement functions
def enhance_prompt_with_memory(prompt_template, prompt_type, user_input, session_id):
    """Enhance the prompt with memory context"""
    enhanced_prompt = prompt_template
    
    # Add session context if available
    if session_id in conversations and len(conversations[session_id]) > 0:
        recent_conversations = conversations[session_id][-3:]  # Last 3 conversations
        context = "\n\nPrevious context from this session:\n"
        for conv in recent_conversations:
            context += f"- {conv['prompt_type']}: {conv['user_input'][:100]}...\n"
        enhanced_prompt += context
    
    # Add learned preferences
    if prompt_type in app_memory.get('prompt_improvements', {}):
        improvements = app_memory['prompt_improvements'][prompt_type]
        if improvements:
            enhanced_prompt += f"\n\nBased on previous interactions, please focus on: {improvements}"
    
    return enhanced_prompt

def learn_from_feedback(prompt_type, feedback_score, feedback_text=""):
    """Learn from user feedback to improve future responses"""
    if prompt_type not in app_memory['prompt_improvements']:
        app_memory['prompt_improvements'][prompt_type] = ""
    
    # Store feedback
    feedback_entry = {
        'timestamp': datetime.now().isoformat(),
        'prompt_type': prompt_type,
        'score': feedback_score,
        'text': feedback_text
    }
    app_memory['feedback_history'].append(feedback_entry)
    
    # Learn from negative feedback
    if feedback_score < 3 and feedback_text:
        # Extract improvement suggestions from feedback
        if len(feedback_text) > 10:  # Only learn from substantial feedback
            current_improvements = app_memory['prompt_improvements'][prompt_type]
            if not current_improvements:
                app_memory['prompt_improvements'][prompt_type] = f"Focus on: {feedback_text[:200]}"
            else:
                app_memory['prompt_improvements'][prompt_type] += f"; Also consider: {feedback_text[:100]}"
    
    save_memory(app_memory)

# Sample premade prompts - in a real app, these would be stored in a database
PREMADE_PROMPTS = {
    'code_review': {
        'name': 'Code Review Assistant',
        'description': 'Analyzes code for bugs, best practices, and improvements',
        'prompt': 'Please review the following code and provide feedback on:\n1. Potential bugs or issues\n2. Code quality and best practices\n3. Performance optimizations\n4. Security concerns\n\nCode:\n{user_input}'
    },
    'documentation': {
        'name': 'Documentation Generator',
        'description': 'Generates comprehensive documentation for code',
        'prompt': 'Generate detailed documentation for the following code including:\n1. Function/class descriptions\n2. Parameter explanations\n3. Return value descriptions\n4. Usage examples\n\nCode:\n{user_input}'
    },
    'bug_fix': {
        'name': 'Bug Fix Assistant',
        'description': 'Helps identify and fix bugs in code',
        'prompt': 'Help me fix the following bug. Please:\n1. Identify the root cause\n2. Explain why the bug occurs\n3. Provide a corrected version\n4. Suggest prevention strategies\n\nBuggy code:\n{user_input}'
    },
    'refactor': {
        'name': 'Code Refactoring',
        'description': 'Suggests improvements and refactoring for code',
        'prompt': 'Refactor the following code to improve:\n1. Readability and maintainability\n2. Performance\n3. Code organization\n4. Following best practices\n\nOriginal code:\n{user_input}'
    },
    'explain': {
        'name': 'Code Explainer',
        'description': 'Explains complex code in simple terms',
        'prompt': 'Explain the following code in simple terms:\n1. What does it do?\n2. How does it work?\n3. Key concepts involved\n4. Potential use cases\n\nCode:\n{user_input}'
    },
    'csv_analysis': {
        'name': 'CSV Data Analysis',
        'description': 'Analyzes CSV data and provides insights',
        'prompt': 'Analyze the following CSV data and provide:\n1. Data overview and structure\n2. Key statistics and patterns\n3. Potential insights and trends\n4. Recommendations for further analysis\n\nCSV Data:\n{user_input}'
    },
    'csv_clean': {
        'name': 'CSV Data Cleaning',
        'description': 'Helps clean and prepare CSV data',
        'prompt': 'Help clean the following CSV data by:\n1. Identifying data quality issues\n2. Suggesting cleaning strategies\n3. Providing cleaned data recommendations\n4. Highlighting potential problems\n\nCSV Data:\n{user_input}'
    }
}

@app.route('/')
def index():
    return render_template('index.html', prompts=PREMADE_PROMPTS, uploaded_files=uploaded_files)

@app.route('/run_prompt', methods=['POST'])
def run_prompt():
    try:
        data = request.get_json()
        prompt_type = data.get('prompt_type')
        user_input = data.get('user_input', '')
        
        if prompt_type not in PREMADE_PROMPTS:
            return jsonify({'error': 'Invalid prompt type'}), 400
        
        if not user_input.strip():
            return jsonify({'error': 'Please provide input'}), 400
        
        # Initialize session if not exists
        if 'session_id' not in session:
            session['session_id'] = str(uuid.uuid4())
            session['conversation_history'] = []
        
        session_id = session['session_id']
        
        # Get the premade prompt template
        prompt_template = PREMADE_PROMPTS[prompt_type]['prompt']
        
        # Enhance prompt with memory context
        enhanced_prompt = enhance_prompt_with_memory(prompt_template, prompt_type, user_input, session_id)
        
        # Replace placeholder with user input
        full_prompt = enhanced_prompt.format(user_input=user_input)
        
        # Generate response using Gemini
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(full_prompt)
        except Exception as e:
            return jsonify({'error': f'Gemini API error: {str(e)}'}), 500
        
        # Store conversation in memory
        conversation_entry = {
            'timestamp': datetime.now().isoformat(),
            'prompt_type': prompt_type,
            'user_input': user_input[:500],  # Store first 500 chars
            'response': response.text[:1000],  # Store first 1000 chars
            'session_id': session_id
        }
        
        # Update session conversation history
        if 'conversation_history' not in session:
            session['conversation_history'] = []
        session['conversation_history'].append(conversation_entry)
        
        # Store in persistent conversations
        if session_id not in conversations:
            conversations[session_id] = []
        conversations[session_id].append(conversation_entry)
        save_conversations(conversations)
        
        return jsonify({
            'success': True,
            'response': response.text,
            'prompt_name': PREMADE_PROMPTS[prompt_type]['name'],
            'session_id': session_id,
            'conversation_count': len(session.get('conversation_history', []))
        })
        
    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

@app.route('/add_prompt', methods=['POST'])
def add_prompt():
    try:
        data = request.get_json()
        prompt_id = data.get('id')
        name = data.get('name')
        description = data.get('description')
        prompt_template = data.get('prompt')
        
        if not all([prompt_id, name, description, prompt_template]):
            return jsonify({'error': 'All fields are required'}), 400
        
        # Add to premade prompts (in a real app, save to database)
        PREMADE_PROMPTS[prompt_id] = {
            'name': name,
            'description': description,
            'prompt': prompt_template
        }
        
        return jsonify({'success': True, 'message': 'Prompt added successfully'})
        
    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

@app.route('/manage')
def manage():
    return render_template('manage.html', prompts=PREMADE_PROMPTS)

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if file and file.filename.lower().endswith('.csv'):
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_filename = f"{timestamp}_{filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(filepath)
            
            # Read CSV and store info
            try:
                df = pd.read_csv(filepath)
                uploaded_files[unique_filename] = {
                    'original_name': filename,
                    'filepath': filepath,
                    'rows': len(df),
                    'columns': list(df.columns),
                    'upload_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'preview': df.head(5).to_html(classes='table table-sm', table_id='csv-preview')
                }
                
                return jsonify({
                    'success': True,
                    'message': f'File uploaded successfully: {filename}',
                    'filename': unique_filename,
                    'rows': len(df),
                    'columns': list(df.columns)
                })
            except Exception as e:
                os.remove(filepath)  # Clean up if CSV is invalid
                return jsonify({'error': f'Invalid CSV file: {str(e)}'}), 400
        else:
            return jsonify({'error': 'Please upload a CSV file'}), 400
            
    except Exception as e:
        return jsonify({'error': f'Upload error: {str(e)}'}), 500

@app.route('/files')
def list_files():
    return jsonify(uploaded_files)

@app.route('/file/<filename>')
def get_file_data(filename):
    if filename not in uploaded_files:
        return jsonify({'error': 'File not found'}), 404
    
    try:
        df = pd.read_csv(uploaded_files[filename]['filepath'])
        return jsonify({
            'success': True,
            'data': df.to_csv(index=False),
            'columns': list(df.columns),
            'rows': len(df)
        })
    except Exception as e:
        return jsonify({'error': f'Error reading file: {str(e)}'}), 500

@app.route('/feedback', methods=['POST'])
def submit_feedback():
    try:
        data = request.get_json()
        prompt_type = data.get('prompt_type')
        score = data.get('score')  # 1-5 rating
        feedback_text = data.get('feedback_text', '')
        
        if not prompt_type or not score:
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Learn from feedback
        learn_from_feedback(prompt_type, score, feedback_text)
        
        return jsonify({'success': True, 'message': 'Feedback recorded successfully'})
        
    except Exception as e:
        return jsonify({'error': f'Error recording feedback: {str(e)}'}), 500

@app.route('/conversation_history')
def get_conversation_history():
    session_id = session.get('session_id')
    if not session_id:
        return jsonify({'conversations': []})
    
    user_conversations = conversations.get(session_id, [])
    return jsonify({'conversations': user_conversations})

@app.route('/memory_stats')
def get_memory_stats():
    return jsonify({
        'total_conversations': sum(len(conv) for conv in conversations.values()),
        'total_sessions': len(conversations),
        'feedback_count': len(app_memory.get('feedback_history', [])),
        'improved_prompts': len([k for k, v in app_memory.get('prompt_improvements', {}).items() if v])
    })

if __name__ == '__main__':
    app.run(debug=True)
