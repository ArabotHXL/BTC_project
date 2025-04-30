"""
This file is a placeholder so the workflow can start
"""

from flask import Flask

app = Flask(__name__)

@app.route('/')
def index():
    return "All files have been deleted as requested."

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)