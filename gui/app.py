# -*- coding: utf-8 -*-

from flask import Flask
app = Flask(__name__)

@app.route('/<var>')
def hello_world(var):
    return 'Hello, World! %s' % var