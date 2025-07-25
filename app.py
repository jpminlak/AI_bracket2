from flask import Flask, render_template, request, redirect, url_for,jsonify
from db import Database
from weatherAPI import WeatherAPIClient
import atexit

app = Flask(__name__) 
db = Database()

atexit.register(db.close)

@app.route('/')
def start():
    return render_template('main.html')

@app.route("/search")
def weather():
    city=request.args.get('city')
    result=db.get_region(city)
    nx=result['nx']
    ny=result['ny']
    tem=WeatherAPIClient.get_weather(nx,ny)
    clothe=db.clothes(tem)      
    return jsonify({
        "tem":tem,
        "clothe":clothe
    })















if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)