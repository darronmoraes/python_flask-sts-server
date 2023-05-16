from flask import Blueprint, jsonify, request, session
from datetime import datetime
import json

from db import db

from models.ticket import Ticket
from models.bus_schedules import BusSchedules
from models.halts import Halts
from models.passenger import Passenger
from models.route_info import RouteInfo
from models.route import Route
from models.pass_model import Pass


bp = Blueprint("booking", __name__, url_prefix="/booking")


@bp.route("/instant", methods=["POST"])
def book_instant():
    booked_at = request.json.get("booked-at")
    total_fare_amount = request.json.get("total-fare-amount")
    distance_travelled = request.json.get("distance-travelled")
    passenger_count = request.json.get("passenger-count")
    source_id = request.json.get("source-id")
    destination_id = request.json.get("destination-id")
    passenger_id = request.json.get("passenger-id")
    bus_schedule_id = request.json.get("bus-schedule-id")

    if not booked_at and passenger_count and passenger_id and bus_schedule_id:
         return jsonify({
            'success': False,
            'message': 'booking date, passenger count and passenger-id required to proceed with booking',
            'status': 400}), 400
    

    existing_booking = Ticket.query.filter_by(passenger_id=passenger_id, bus_schedule_id=bus_schedule_id, booked_at=booked_at).first()
    if existing_booking:
         return jsonify({
            'success': False,
            'message': 'There is already an existing booking for this passenger on this bus schedule.',
            'status': 400}), 400
    

    # add bus details if not existing
    new_instant_booking = Ticket(booked_at=booked_at, total_fare_amount=total_fare_amount, distance_travelled=distance_travelled,\
                                  passenger_count=passenger_count, source_id=source_id, destination_id=destination_id,\
                                    passenger_id=passenger_id, bus_schedule_id=bus_schedule_id)
    db.session.add(new_instant_booking)

    # update bus schedule available seats
    bus_schedule = BusSchedules.query.get(bus_schedule_id)
    bus_schedule.available_seats -= passenger_count
    # commit ticket booking and seat_availabilty update
    db.session.commit()


    # get source and destination stands name
    source_stand = new_instant_booking.bus_schedule.schedule.route.source_stand
    destination_stand = new_instant_booking.bus_schedule.schedule.route.destination_stand

    # return registration success
    return jsonify({
        'success': True,
        'message': 'booking successfully',
        'result': {
             'ticket': {
                'id': new_instant_booking.id,
                'fare-amount': new_instant_booking.total_fare_amount,
                'passenger-count': new_instant_booking.passenger_count,
                'source': new_instant_booking.source.name,
                'destination': new_instant_booking.destination.name,
                'booked-at': new_instant_booking.booked_at  
             },
             'bus': {
                'id': new_instant_booking.bus_schedule.bus.id,
                'bus-type': new_instant_booking.bus_schedule.bus.type,
                'reg-no': new_instant_booking.bus_schedule.bus.reg_no
             },
             'schedule-info': {
                'id': new_instant_booking.bus_schedule.id,
                'schedule': {
                    'id': new_instant_booking.bus_schedule.schedule.id,
                    'departure': new_instant_booking.bus_schedule.schedule.departure_at.strftime('%H:%M'),
                    'departure-stand': source_stand,
                    'arrival': new_instant_booking.bus_schedule.schedule.arrival_at.strftime('%H:%M'),
                    'arrival-stand': destination_stand,
                    'duration': new_instant_booking.bus_schedule.schedule.duration,
                },
                'date': new_instant_booking.bus_schedule.date.strftime('%Y-%m-%d'),
                'seats-available': new_instant_booking.bus_schedule.available_seats
             }
        },
        'status': 200}), 200



@bp.route("/passenger-off", methods=["POST"])
def passenger_off():
    ticket_id = request.json.get("ticket-id")
    halt_id = request.json.get("halt-id")
    
    if not ticket_id or not halt_id:
        return jsonify({
            'success': False,
            'message': 'Ticket ID and halt ID are required to proceed.',
            'status': 400}), 400
    
    ticket = Ticket.query.filter_by(id=ticket_id).first()
    
    if not ticket:
        return jsonify({
            'success': False,
            'message': 'Ticket not found.',
            'status': 400}), 400
    
    if ticket.status == "completed":
        return jsonify({
            'success': False,
            'message': 'Passenger has already been dropped off.',
            'status': 400}), 400
    
    # update the seat availability for the bus schedule
    bus_schedule = BusSchedules.query.filter_by(id=ticket.bus_schedule_id).first()
    halt = Halts.query.filter_by(id=halt_id).first()
    
    if bus_schedule and halt:
        # calculate the number of seats to add back
        num_seats = ticket.passenger_count
        
        # update the available seats for the bus schedule
        bus_schedule.available_seats += num_seats
        
        # update the status of the ticket to completed
        ticket.status = "completed"
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{num_seats} seats have been made available for the bus schedule.',
            'status': 200}), 200
    
    return jsonify({
        'success': False,
        'message': 'Invalid bus schedule or halt ID.',
        'status': 400}), 400


# @bp.route('/passenger-instant-booking', methods=['GET'])
# def passengers_instant_booking():
#     passenger = request.args.get('passenger-id')

#     if not passenger:
#         return jsonify({
#             'success': False,
#             'message': f'Passenger with id {passenger} does not exist',
#             'status': 404}), 404
    
#     passenger_bookings = Ticket.query.filter_by(passenger_id=passenger).all()
#     if not passenger_bookings:
#         return jsonify({
#             'success': False,
#             'message': f'No bookings found for passenger with id {passenger}',
#             'status': 404}), 404
    
#     bookings_data = []
#     for booking in passenger_bookings:
#         booking_data = {
#             'id': booking.id,
#             'booked_at': booking.booked_at,
#             'total_fare_amount': booking.total_fare_amount,
#             'distance_travelled': booking.distance_travelled,
#             'passenger_count': booking.passenger_count,
#             'source_id': booking.source_id,
#             'destination_id': booking.destination_id,
#             'bus_schedule_id': booking.bus_schedule_id,
#             'status': booking.status
#         }
#         bookings_data.append(booking_data)

    
#     return jsonify({
#             'success': True,
#             'passenger-id': passenger,
#             'bookings': bookings_data,
#             'status': 200}), 200



@bp.route('/passenger-ticket-bookings/<int:passenger_id>', methods=['GET'])
def passenger_ticket_bookings(passenger_id):
    passenger = Passenger.query.get(passenger_id)
    if not passenger:
        return jsonify({
            'success': False,
            'message': f'Passenger with id {passenger_id} does not exist',
            'status': 404}), 404

    passenger_tickets = Ticket.query.filter_by(passenger_id=passenger_id).all()
    if not passenger_tickets:
        return jsonify({
            'success': False,
            'message': f'No bookings found for passenger with id {passenger_id}',
            'status': 404}), 404

    tickets_data = []
    for ticket in passenger_tickets:
        source_stop = Halts.query.filter_by(id=ticket.source_id).first()
        destination_stop = Halts.query.filter_by(id=ticket.destination_id).first()
        bus_schedule_info = BusSchedules.query.filter_by(id=ticket.bus_schedule_id).first()

        ticket_data = {
            'ticket': {
                'id': ticket.id,
                'booked-at': ticket.booked_at,
                'total-fare-amount': ticket.total_fare_amount,
                'distance-travelled': ticket.distance_travelled,
                'passenger-count': ticket.passenger_count,
                'status': ticket.status,
                'source': source_stop.name,
                'destination': destination_stop.name,
            },
            'schedule-info': {
                'id': ticket.bus_schedule_id,
                'date': bus_schedule_info.date.strftime('%Y-%m-%d')
            }, 
            'bus': {
                'id': bus_schedule_info.bus.id,
                'reg-no': bus_schedule_info.bus.reg_no,
                'type': bus_schedule_info.bus.type
            },
        }
        tickets_data.append(ticket_data)

    return jsonify({
        'success': True,
        'passenger_id': passenger_id,
        'bookings': tickets_data,
        'status': 200}), 200



# route to get halts for matching source geo locations
@bp.route('/bus-stops', methods=['GET'])
def get_bus_stops():
    halts = Halts.query.all()
    halts_list = []
    for halt in halts:
        halts_list.append({'id': halt.id, 'name': halt.name, 'long': halt.longitude, 'lat': halt.latitude})
    return jsonify({
        'success': True,
        'result': halts_list,
        'status': 200
    }), 200


# seat-available route
@bp.route('/seat-available', methods=['POST'])
def check_availability():
    bus_id = request.args.get('bus-id')
    schedule_info_id = request.args.get('schedule-info-id')
    schedule_id = request.args.get('schedule-id')
    passenger_count = int(request.args.get('passenger-count'))
    date_str = request.args.get('date')

    # convert date
    date = datetime.strptime(date_str, '%Y-%m-%d').date()

    if not bus_id and not schedule_info_id and not schedule_id and not passenger_count and not date:
        return jsonify({
            'success': False,
            'message': 'No schedule and passenger count provided.',
            'status': 400}), 400
    
    bus_schedule = BusSchedules.query.filter_by(id=schedule_info_id, bus_id=bus_id, schedule_id=schedule_id, date=date).first()

    if not bus_schedule:
        return jsonify({
            'success': False,
            'message': 'No buses available for the specified date',
            'status': 400}), 400
    
    available_seats = bus_schedule.available_seats

    if available_seats < passenger_count:
        return jsonify({
            'success': False,
            'message': 'Not enough seats available for the specified number of passengers',
            'status': 400}), 400
    
    return jsonify({
            'success': True,
            'available-seats': available_seats,
            'status': 200}), 200



@bp.route("/search", methods=["GET"])
def bus_available_search():
    source_id = request.args.get('source')
    destination_id = request.args.get('destination')
    date_str = request.args.get('date')

    # convert date
    date = datetime.strptime(date_str, '%Y-%m-%d').date()

    # query route-info model to find the route between source and destination
    route_query = db.session.query(Halts, RouteInfo).\
        join(RouteInfo, RouteInfo.source_id == Halts.id).\
        filter(RouteInfo.source_id == source_id, RouteInfo.destination_id == destination_id)

    route_info = route_query.first()

    # query bus-schedule model to find the available date
    bus_schedules = BusSchedules.query.filter(BusSchedules.date == date).all()

    if not bus_schedules:
        return jsonify({
            'success': False,
            'message': 'no buses available on this route for the specific date',
            'status': 400
        }), 400

    available_buses = []

    for bus_schedule in bus_schedules:
        # get the route information from the schedule
        route_stand = bus_schedule.schedule.route
        # get the source and destination stands from the route info
        source_stand = route_stand.source_stand
        destination_stand = route_stand.destination_stand

        # query halts table to get source and destination names
        source_halt = Halts.query.get(source_id)
        destination_halt = Halts.query.get(destination_id)

        available_bus_result = {
            'schedule-info': {
                'id': bus_schedule.id,
                'date': bus_schedule.date.strftime('%Y-%m-%d'),
                'seats-available': bus_schedule.available_seats,
                'schedule' : {
                    'id' : bus_schedule.schedule.id,
                    'departure': bus_schedule.schedule.departure_at.strftime('%H:%M'),
                    'arrival': bus_schedule.schedule.arrival_at.strftime('%H:%M'),
                    'duration': bus_schedule.schedule.duration,
                    'departure-stand': source_stand,
                    'arrival-stand': destination_stand
                }
            },
            'bus': {
                'id': bus_schedule.bus.id,
                'reg-no': bus_schedule.bus.reg_no,
                'type': bus_schedule.bus.type
            },
            'route-info': {
                'source': source_halt.name,
                'source-id': source_halt.id,
                'destination': destination_halt.name,
                'destination-id': destination_halt.id,
                'distance': route_info.RouteInfo.distance,
                'fare': route_info.RouteInfo.fare
            }
        }
        available_buses.append(available_bus_result)

    return jsonify({
        'success': True,
        'status': 200,
        'results': available_buses
    }), 200



"""
Pass Booking Api's requests
Get a list of all pass bookings

"""
# route to get pass **not required**
@bp.route('/pass', methods=['GET'])
def get_pass():
    passes = Pass.query.all()
    pass_list = []
    for p in passes:
        pass_list.append({
            'id': p.id, 
            'valid_from': p.valid_from, 
            'valid_to': p.valid_to, 
            'status': p.status, 
            'price': p.price, 
            'source': p.source.name,
            'destination': p.destination.name})
        

    return jsonify({
        'success': True,
        'result': pass_list,
        'status': 200
    }), 200


# route to create a new pass for passenger
@bp.route('/passenger/<passenger_id>/passes', methods=['POST'])
def create_passenger_pass(passenger_id):
    # Retrieve the passenger using the passenger_id
    passenger = Passenger.query.get(passenger_id)

    # check if passenger exists
    if not passenger:
        return jsonify({
            'success': False,
            'message': 'Passenger not found',
            'status': 400
        }), 400

    # request pass data
    valid_from = request.json.get('valid-from')
    valid_to = request.json.get('valid-to')
    source_id = request.json.get('source-id')
    destination_id = request.json.get('destination-id')
    price = request.json.get('price')

    # query for existing pass
    existing_pass = Pass.query.filter(
        Pass.passenger_id == passenger_id, 
        Pass.valid_from <= valid_to, 
        Pass.valid_to >= valid_from, 
        Pass.source_id == source_id, 
        Pass.destination_id == destination_id
    ).first()
    if existing_pass:
        return jsonify({
            'success': False,
            'message': 'Already created pass having same dates, source & destination',
            'status': 401
        }), 401

    # create pass
    new_pass = Pass(
        valid_from = valid_from,
        valid_to = valid_to,
        status = 'active',
        price = price,
        passenger_id = passenger_id,
        source_id = source_id,
        destination_id = destination_id,
    )

    # insert pass to db
    db.session.add(new_pass)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Pass created successfully',
        'pass_id': new_pass.id,
        # 'payment_id': payment.id,
        'status': 200
    }), 200
    


# route to get pass **passenger specific**
@bp.route("/passenger/<passenger_id>/passes", methods=['GET'])
def get_user_passes(passenger_id):
    # Retrieve the passenger using the passenger_id
    passenger = Passenger.query.get(passenger_id)

    # check if passenger exists
    if not passenger:
        return jsonify({
        'success': False,
        'message': 'passenger not found',
        'status': 400}), 400
    
    # Query Pass model to get passes on passenger-id
    passes = Pass.query.filter_by(passenger_id=passenger_id).all()

    # Store the list of passes in pass_data array-list
    pass_data = []
    for p in passes:
        valid_from = p.valid_from.strftime('%Y-%m-%d')
        valid_to = p.valid_to.strftime('%Y-%m-%d')
        pass_data.append({
            'id': p.id,
            'source': p.source.name,
            'destination': p.destination.name,
            'status': p.status,
            'valid-from': valid_from,
            'valid-to': valid_to,
            'price': p.price,
        })

    return jsonify({
        'success': True,
        'result': pass_data,
        'status': 200
    }), 200


# validate pass for onboarding
@bp.route("/passenger/<passenger_id>/passes/<pass_id>/validate-pass", methods=['POST'])
def validate_pass_onboarding(passenger_id, pass_id):
    passenger = Passenger.query.get(passenger_id)
    if not passenger:
        return jsonify({
        'success': False,
        'message': 'Passenger not found',
        'status': 401}), 401
    

    # Retrieve pass given passenger-id and pass-id
    pass_model = Pass.query.filter_by(id=pass_id, passenger_id=passenger_id).first()

    if not pass_model:
        return jsonify({
        'success': False,
        'message': 'Pass not found',
        'status': 402}), 402
    

    # Get travel time for validation
    travel_date_str = request.json.get('travel-date')
    travel_date = datetime.strptime(travel_date_str, '%Y-%m-%d').date()


    if pass_model.valid_from <= travel_date <= pass_model.valid_to:
        if pass_model.usage_counter < 2:
            pass_model.usage_counter += 1
            db.session.commit()
            return jsonify({
                'success': False,
                'message': 'Pass is valid for travel today and counter incremented by 1',
                'status': 200}), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Pass has already been used twice today',
                'status': 400}), 400
    else:
        return jsonify({
            'success': False,
            'message': 'Pass is not valid for specified travel date',
            'status': 400}), 400