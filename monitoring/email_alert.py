from flask_mail import Message

mail = None

def init_mail(app, mail_instance):
    global mail
    mail = mail_instance

def send_alert(subject, recipient, body):
    msg = Message(
        subject=subject,
        recipients=[recipient],
        body=body
    )

    mail.send(msg)