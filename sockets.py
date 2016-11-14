#!/usr/bin/env python
# coding: utf-8
# Copyright (c) 2013-2014 Abram Hindle
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import flask
from flask import Flask, request
from flask_sockets import Sockets
import gevent
from gevent import queue
import time
import json
import os

app = Flask(__name__)
sockets = Sockets(app)
app.debug = True

class World:
    def __init__(self):
        self.clear()
        self.listeners = list()
        
    def add_set_listener(self, listener):
        self.listeners.append( listener )

    def update(self, entity, key, value):
        entry = self.space.get(entity,dict())
        entry[key] = value
        self.space[entity] = entry
        self.update_listeners( entity )

    def set(self, entity, data):
        self.space[entity] = data
        self.update_listeners( entity )

    def update_listeners(self, entity):
        for listener in self.listeners:
            listener(entity, self.get(entity))

    def clear(self):
        self.space = dict()

    def get(self, entity):
        return self.space.get(entity,dict())
    
    def world(self):
        return self.space
    
#Taken from Abram Hindle's notes.
def send_all(msg):
    for client in clients:
        client.put( msg )

#Taken from Abram Hindle's notes.
def send_all_json(obj):
    send_all( json.dumps(obj) )

#Taken from Abram Hindle's notes.
class Client:
    def __init__(self):
        self.queue = queue.Queue()

    def put(self, v):
        self.queue.put_nowait(v)

    def get(self):
        return self.queue.get()

myWorld = World()
clients = list()

#Taken from Abram Hindle's notes.
def set_listener( entity, data ):
    msg = dict()
    msg[entity] = data
    send_all_json(msg)

myWorld.add_set_listener( set_listener )
        
@app.route('/')
def hello():
    return app.send_static_file('index.html')

# Taken from Abram Hindle's notes.
def read_ws(ws,client):
    try:
        while True:
            msg = ws.receive()
            print "WS RECV: %s" % msg
            if (msg is not None):
                packet = json.loads(msg)
                send_all_json( packet )
            else:
                break
    except:
        '''Done'''

# Taken from Abram Hindle's notes.
@sockets.route('/subscribe')
def subscribe_socket(ws):
    client = Client()
    clients.append(client)
    g = gevent.spawn( read_ws, ws, client )    
    try:
        while True:
            msg = client.get()
            ws.send(msg)
    except Exception as e:
        print "WS Error %s" % e
    finally:
        clients.remove(client)
        gevent.kill(g)

def flask_post_json():
    if (request.json != None):
        return request.json
    elif (request.data != None and request.data != ''):
        return json.loads(request.data)
    else:
        return json.loads(request.form.keys()[0])

@app.route("/entity/<entity>", methods=['POST','PUT'])
def update(entity):
    i = 0;
    while i < len(flask_post_json()):
        myWorld.update(entity, flask_post_json().keys()[i], flask_post_json().values()[i])
        i += 1
    return json.dumps(myWorld.get(entity))

@app.route("/world", methods=['POST','GET'])
def world():
    return json.dumps(myWorld.world())

@app.route("/entity/<entity>")
def get_entity(entity):
    return json.dumps(myWorld.get(entity))

@app.route("/clear", methods=['POST','GET'])
def clear():
    myWorld.clear()
    return json.dumps(myWorld.world())

if __name__ == "__main__":
    ''' This doesn't work well anymore:
        pip install gunicorn
        and run
        gunicorn -k flask_sockets.worker sockets:app
    '''    
    app.run()