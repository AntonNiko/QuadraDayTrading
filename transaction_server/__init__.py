#!/usr/bin/env python3
from flask import Flask, jsonify
import os
from transaction_server import commands

# Create and configure app
app = Flask(__name__, instance_relative_config=True)
app.config.from_mapping(
    SECRET_KEY='dev'
)

# Ensure instance folder exists
try:
    os.makedirs(app.instance_path)
except OSError:
    pass

# Ping server
@app.route('/')
def ping():
    return jsonify({'status': 'success', 'message': 'Transaction server is alive!'})

app.register_blueprint(commands.bp)