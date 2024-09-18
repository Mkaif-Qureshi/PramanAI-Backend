from flask import Flask, jsonify
from flask_pymongo import PyMongo
from dotenv import load_dotenv
from flask_cors import CORS

mongo = PyMongo()

def create_app():
    app = Flask(__name__)

    load_dotenv()

    app.config.from_object('app.config.Config')

    mongo.init_app(app)  # Initialize MongoDB
    CORS(app)

    from app.routes import main_bp
    app.register_blueprint(main_bp)

    @app.errorhandler(404)
    def not_found_error(error):
        return jsonify({'message': 'Not found'}), 404

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'message': 'Internal server error'}), 500

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
