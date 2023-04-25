from db import db

class Destination(db.Model):
    __tablename__ = 'destination'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(45), nullable=False)
    longitutde = db.Column(db.String(50), nullable=False)
    latitude = db.Column(db.String(50), nullable=False)