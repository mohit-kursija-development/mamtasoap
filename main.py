from flask import Flask, render_template, request, jsonify
import smtplib

# Initialize the Flask application
app = Flask(__name__)

SMTP_SERVER = 'smtp.gmail.com'  # Example for Gmail
SMTP_PORT = 587
EMAIL_ADDRESS = 'your_email@gmail.com'  # Replace with your email
EMAIL_PASSWORD = 'your_password'  # Replace with your email password

# Define a route for the home page
@app.route('/')
def home():
    cards = []
    cards = [
        {
            "image": "images/1----5X7.jpg",
            "title": "RK Washing Soap",
            "items": ["Weight: 200gms per pc", "Box: 50pcs"]
        },
        {
            "image": "images/3----5X7.jpg",
            "title": "RK Washing Soap",
            "items": ["Weight: 90gms per pc", "Box: 60pcs"]
        },
        {
            "image": "images/6----5X7.jpg",
            "title": "Ramesh Washing Soap",
            "items": ["Weight: 850gms packet", "Box: 10 packets"]
        },
        {
            "image": "images/31----5X7.jpg",
            "title": "RK Dishwash Gel",
            "items": ["Weight: 1ltr per pc", "Box: 6pcs"]
        },
        
        {
            "image": "images/10----5X7.jpg",
            "title": "RK Dishwash Gel",
            "items": ["Weight: 500ml per pc", "Box: 12pcs"]
        },
        {
            "image": "images/29----5X7.jpg",
            "title": "RK Dishwash Gel",
            "items": ["Weight: 250ml per pc", "Box: 24pcs"]
        },
        {
            "image": "images/12----5X7.jpg",
            "title": "RK Fabric Cleaner",
            "items": ["Weight: 1ltr per pc", "Box: 6pcs"]
        },
        {
            "image": "images/14----5X7.jpg",
            "title": "RK Fabric Cleaner",
            "items": ["Weight: 500ml per pc", "Box: 6pcs"]
        },
        {
            "image": "images/16----5X7.jpg",
            "title": "RK Fabric Cleaner",
            "items": ["Weight: 5ltr per pc", "Box: 2pcs"]
        },
        {
            "image": "images/38----5X7.jpg",
            "title": "R.K. Multipurpose Gel",
            "items": ["Weight: 5ltr per pc", "Box: 2pcs"]
        },
        {
            "image": "images/17----5X7.jpg",
            "title": "RK Multipurpose Gel",
            "items": ["Weight: 1ltr per pc", "Box: 12pcs"]
        },
        {
            "image": "images/20----5X7.jpg",
            "title": "RK Dishwash Gel",
            "items": ["Weight: 5ltr per pc", "Box: 2pcs"]
        },
        {
            "image": "images/8----5X7.jpg",
            "title": "RK Soap",
            "items": ["Weight: 750gms packet", "Box: 8 packets"]
        },
        
    ]
    for i in cards:
        print(i)
    return render_template("index.html", cards=cards)

@app.route('/api/submit-form', methods=['POST'])
def api_submit_form():
    data = request.get_json()  # Get JSON data from the request
    name = data.get('name')
    phone = data.get('phone')
    query = data.get('query')

    if not name or not phone or not query:
        return jsonify({"message": "Name phone,query are required!"}), 400

    # Email Content
    subject = "Callback Request"
    body = f"Name: {name}\nPhone: {phone} \n Query: {query}"
    message = f"Subject: {subject}\n\n{body}"

    # Send email
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()  # Secure connection
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, EMAIL_ADDRESS, message)
        return jsonify({"message": "Email sent successfully!"}), 200
    except Exception as e:
        return jsonify({"message": "Some server Error Occured"}), 500
        # return jsonify({"message": str(e)}), 500 Only on for debugging

# Run the app
if __name__ == '__main__':
    app.run(debug=True)
