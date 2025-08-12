# server.py (Versão Corrigida para Render)
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
from datetime import datetime, timedelta

app = Flask(__name__)
# O Render usa uma base de dados num local específico
db_path = os.path.join('/var/data', 'database.db')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Licenca(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(100), unique=True, nullable=False)
    machine_id = db.Column(db.String(200), unique=True, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)

# Cria a base de dados e a tabela antes do primeiro pedido
with app.app_context():
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    db.create_all()

@app.route('/validate', methods=['POST'])
def validate_token():
    data = request.get_json()
    if not data or 'token' not in data or 'machine_id' not in data:
        return jsonify({'valid': False, 'message': 'Dados inválidos'}), 400

    token_str = data['token']
    machine_id_str = data['machine_id']
    licenca = Licenca.query.filter_by(token=token_str).first()

    if not licenca or not licenca.is_active:
        return jsonify({'valid': False, 'message': 'Token inválido ou desativado'})

    if licenca.machine_id:
        if licenca.machine_id == machine_id_str:
            licenca.last_seen = datetime.utcnow()
            db.session.commit()
            return jsonify({'valid': True, 'message': 'Licença validada com sucesso'})
        else:
            return jsonify({'valid': False, 'message': 'Token já em uso noutra máquina'})
    else:
        licenca.machine_id = machine_id_str
        licenca.last_seen = datetime.utcnow()
        db.session.commit()
        return jsonify({'valid': True, 'message': 'Token ativado com sucesso para esta máquina'})

@app.route('/heartbeat', methods=['POST'])
def heartbeat():
    data = request.get_json()
    token_str = data.get('token')
    licenca = Licenca.query.filter_by(token=token_str).first()
    if licenca:
        licenca.last_seen = datetime.utcnow()
        db.session.commit()
        return jsonify({'status': 'ok'}), 200
    return jsonify({'status': 'token_not_found'}), 404

@app.route('/dashboard', methods=['GET'])
def dashboard():
    total_users = Licenca.query.count()
    five_minutes_ago = datetime.utcnow() - timedelta(minutes=5)
    online_users = Licenca.query.filter(Licenca.last_seen > five_minutes_ago).count()
    return jsonify({
        'total_de_utilizadores_registados': total_users,
        'utilizadores_online_agora': online_users
    })

@app.route('/add_token', methods=['GET'])
def add_token():
    secret_key = "mudar_para_uma_senha_muito_segura"
    token_to_add = request.args.get('token')
    provided_secret = request.args.get('secret')

    if provided_secret != secret_key:
        return "Acesso negado.", 403
    if not token_to_add:
        return "Por favor, forneça um token.", 400
    if Licenca.query.filter_by(token=token_to_add).first():
        return f"O token '{token_to_add}' já existe.", 400

    nova_licenca = Licenca(token=token_to_add)
    db.session.add(nova_licenca)
    db.session.commit()
    return f"Token '{token_to_add}' adicionado com sucesso!", 200