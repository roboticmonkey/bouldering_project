""" Server File """
from jinja2 import StrictUndefined
from flask import Flask, render_template, request, redirect, session, flash, jsonify
from datetime import datetime
from flask_debugtoolbar import DebugToolbarExtension
from model import connect_to_db, db, User, Location, Sub_location, Boulder, Route
from model import Boulder_comment, Route_comment, Boulder_rating, Route_rating
from sqlalchemy import desc
import hashing 

from helper import convert_sublocations_dict, convert_boulders_dict
from helper import convert_locations_dict, convert_location_dict, convert_route_dict
from helper import convert_sublocation_dict, convert_boulder_dict, convert_routes_dict

app = Flask(__name__)

app.secret_key = "something-secret"

app.jinja_env.undefined = StrictUndefined


#############
#The routes

@app.route('/')
def index():
    """Homepage"""
    # session['user_id'] = None 
    return render_template('homepage.html')


@app.route('/register', methods=['GET'])
def register_form():
    """displays the user register"""
    
    #renders a user sign up form
    return render_template('register.html')

@app.route('/register', methods=['POST'])
def register_process():
    """handles the user register form"""
    
    #get form variables
    email = request.form.get('email')
    password = request.form.get('pwd')
    username = request.form.get('username')

    hashed_password = hashing.hash_password(password)
    


    #check if username in db
    user = User.query.filter( (User.username == username) | (User.email == email) ).first()

    # if user is empty add user to db
    if not user:
        #add user to db
        new_user = User(email=email, username=username, password=hashed_password)
        flash("Welcome %s."  % (username))
        db.session.add(new_user)
        db.session.commit()

        created_user = User.query.filter_by(username=username).first()

        #create the key value pair in the session(= magic dictionary)
        #(flask's session)
        session['user_id'] = created_user.user_id
        session['username'] = created_user.username
        
        # renders a user page
        return render_template('user_page.html')
    else:
        if user.email == email:
            flash("%s email already has an account."  % (email))
            return redirect("/")
        else:
            flash("%s username is already taken. Choose something else." % (username)) 
            return redirect("/")

    

@app.route('/login', methods=['POST'])
def login_user():
    """Handles user login"""

    # get username and password from form
    password = request.form.get('pwd')
    username = request.form.get('username')

    # find matching username in db
    user = User.query.filter_by(username=username).first()

    # no username match, got back to homepage
    if not user:
        flash("No username registered with the name %s" % (username))
        return redirect('/')

    # if user object is there get hashed pwd compare w/ entered pwd
    else:
        if hashing.check_password(user.password, password):
            #if a match send to user page
            flash("Sucessfully logged in.")
            
            #create the key value pair in the session(= magic dictionary)
            #(flask's session)
            session['user_id'] = user.user_id
            session['username'] = user.username

            return redirect('/user_page')
        # no match got back to homepage, Do Not Collect 200.
        else:
            flash("Incorrect password entered")
            return redirect('/')

@app.route('/user_page')
def view_user_page():
    """shows the user's page"""

    #gets user id from the session variable
    user_id = session['user_id']

    if user_id:
        # find matching username in db
        user = User.query.filter_by(user_id=user_id).first()
        climbed_list = []
        #find all the routes the user has rated
        rated_routes = Route_rating.query.filter(Route_rating.user_id==user.user_id).all()
        for rated in rated_routes:
          
            climbed = {}
            climbed['route_name'] = rated.route.route_name
            climbed['route_id'] = rated.route.route_id
            climbed['rating'] = rated.route.difficulty_rate
            climbed['star_rating'] = rated.route_rating
            climbed['boulder_name'] = rated.route.boulder.boulder_name
            climbed['boulder_id'] = rated.route.boulder.boulder_id
            climbed_list.append(climbed)
        if climbed_list == []:
            climbed_list = None
        return render_template('user_page.html', climbed_list=climbed_list)
    else:
        flash("Please login to see the user page.")
        redirect('/')   

@app.route('/logout')
def logout_user():
    """Logs out user and flashes a logout message"""

    # deletes the key and value in the session dictionary
    del session['user_id']
    del session['route_id']
    del session['boulder_id']
    del session['username']
    del session['boulder_route']
    flash("You have been logged out.")

    return redirect('/')

#REMOVE THIS ROUTE>>>> NOT NEEDED
@app.route('/locations')
def display_location():
    """Display location list page"""

    #lists the location's routes as links
    locations = Location.query.order_by('location_name').all()
    return render_template("location.html", locations=locations)

@app.route("/locations/<int:location_id>", methods=['GET'])
def location_detail(location_id):
    """Show info about a location."""

    #get the location object
    location = Location.query.get(location_id)
    #find all sublocations that have the location as a parent
    sub_locations = Sub_location.query.filter_by(location_id=location_id).all()

    #find boulders that match the location_id, but dont have a
    #assoicated sub_location_id
    boulders = Boulder.query.filter((Boulder.location_id==location_id) & 
                                    (Boulder.sub_location_id==None)).all()
        
    return render_template("location_detail.html", location=location,
                                                 sub_locations=sub_locations,
                                                 boulders=boulders )

@app.route("/sub_locations/<int:sub_location_id>", methods=['GET'])
def sub_location_detail(sub_location_id):
    """Shows a sub location details page"""
    #find the sublocation object
    sub = Sub_location.query.get(sub_location_id)
    #find the boulders that have the sublocation as a parent
    boulders = Boulder.query.filter_by(sub_location_id=sub_location_id).all()
    location = Location.query.filter(Location.location_id==sub.location_id).first()
    print sub
    return render_template("sub_location.html", sub_location=sub,
                                                boulders=boulders,
                                                location=location)
    
 


@app.route("/boulders/<int:boulder_id>", methods=['GET'])
def boulder_detail(boulder_id):
    #find the Boulder object
    boulder = Boulder.query.get(boulder_id)
    #find all routes connected to that boulder
    routes = Route.query.filter_by(boulder_id=boulder_id).all()
    
    num_of_routes = len(routes)

    session['boulder_id'] = boulder.boulder_id
    session['boulder_route'] = 'boulder'
    # set avg variable and user_score variable
    avg = 0
    user_id = session.get("user_id")
    if user_id is not None:
        user_rate = Boulder_rating.query.filter( (Boulder_rating.boulder_id==boulder_id) & 
                                                (Boulder_rating.user_id==user_id)).first()
        if user_rate:
            user_score = user_rate.boulder_rating
        else:
            user_score = 0
    else:
        user_score = 0

    comments = Boulder_comment.query.filter(Boulder_comment.boulder_id==boulder.boulder_id).order_by(desc(Boulder_comment.boulder_datetime)).all()

    rating_objs = Boulder_rating.query.filter(Boulder_rating.boulder_id==boulder.boulder_id).all()
    ratings = [rating.boulder_rating for rating in rating_objs]
    
    if ratings:
        avg = round(float(sum(ratings))/ len(ratings), 0)
        
    return render_template("boulders.html", boulder=boulder,
                                            routes=routes,
                                            comments=comments,
                                            avg=avg,
                                            user_score=user_score)

@app.route('/get_chart_info.json', methods=['GET'])
def create_chart_data():
    # get the boulder_id from the ajax call
    boulder_id = request.args.get('boulder_id')
    
    # find all routes connected to the boulder_id
    routes = Route.query.filter_by(boulder_id=boulder_id).all()

    # get route difficulty breakdown from routes
    THE_LIST =['V0', 'V1', 'V2', 'V3', 'V4', 'V5', 'V6', 'V7', 'V8', 'V9', 'V10','V11', 'V12']
    # numbers list will hold the number of routes at the corresponding index
    # that match the diffficulty rating. ie. 'V1' is at index 1 in THE_LIST
    # if there are 3 V1's on a boulder the numbers list will show 3 at index 1
    numbers=[0,0,0,0,0,0,0,0,0,0,0,0,0]
    for route in routes:
        diff = route.difficulty_rate[:3]
        
        if diff:
            if diff[-1] == "-" or diff[-1] == "+":
                diff = diff[:2]

            numbers[int(diff[1:])] = numbers[int(diff[1:])] + 1

    chart_data = {}
    chart_data['chart_labels'] = THE_LIST
    chart_data['data'] = numbers

    return jsonify(chart_data)

@app.route('/route/<int:route_id>', methods=['GET'])
def display_route(route_id):
    """Display route details page"""
    #get the route object
    route = Route.query.get(route_id)
    #find other routes that are on the same boulder
    near_routes = Route.query.filter((Route.boulder_id==route.boulder_id) & 
                                    (Route.route_name != route.route_name)).all()
    #find near_by boulders
    boulder = Boulder.query.filter_by(boulder_id=route.boulder_id).first()
    
    session['route_id'] = route.route_id
    session['boulder_route'] = 'route'

    
    # set avg variable and user_score variable
    avg = 0
    user_id = session.get("user_id")
    if user_id is not None:
        user_rate = Route_rating.query.filter( (Route_rating.route_id==route_id) & 
                                                (Route_rating.user_id==user_id)).first()
        
        if user_rate:
            user_score = user_rate.route_rating
            
        else: 
            user_score = 0
    else:
        user_score = 0
    
    if boulder.sub_location_id:
        boulders = Boulder.query.filter_by(sub_location_id=boulder.sub_location_id).all()
    else:
        boulders = Boulder.query.filter_by(location_id=boulder.location_id).all()

    comments = Route_comment.query.filter(Route_comment.route_id==route.route_id).order_by(desc(Route_comment.route_datetime)).all()

    num_dict = {}
    for boulder in boulders:
        #find all routes connected to that boulder
        boulder_id = boulder.boulder_id
        routes = Route.query.filter_by(boulder_id=boulder.boulder_id).all()
        
        print boulder_id

        num_of_routes = len(routes)
        num_dict[boulder_id] = num_of_routes

    print num_dict

    
    rating_objs = Route_rating.query.filter(Route_rating.route_id==route.route_id).all()
    
    ratings = [rating.route_rating for rating in rating_objs]

    
    if ratings:
        avg = round(float(sum(ratings))/ len(ratings), 0)
        

    return render_template("route.html", route=route,
                                        near_routes=near_routes,
                                        boulders=boulders,
                                        comments=comments,
                                        avg=avg,
                                        user_score=user_score,
                                        num_dict=num_dict)

@app.route('/location.json', methods=['GET'])
def find_location_kids():
    """returns a location's children"""
    search_term = request.args.get('term')


    #QUERIES TO FIND LOCATION INFORMATION
    location = Location.query.filter(Location.location_id == search_term).first()
    sub_locations = Sub_location.query.filter(Sub_location.location_id == search_term).all()
    boulders = Boulder.query.filter(Boulder.location_id == search_term).all()

    #TO HOLD ALL THE LOCATIONS THAT HAVE BEEN FOUND
    results = []
     
    location_dict = convert_location_dict(location)
    
    results.append(location_dict)
    
    if sub_locations: 
        sub_dict = convert_sublocations_dict(sub_locations)
        
        results.extend(sub_dict)

    if boulders:
        boulder_dict = convert_boulders_dict(boulders)
        results.extend(boulder_dict)


    return jsonify({'data':results})

@app.route('/sub_location.json', methods=['GET'])
def find_sub_location_kids():
    """returns a sub.location's children"""
    search_term = request.args.get('term')

    sub_location = Sub_location.query.filter(Sub_location.sub_location_id == search_term).first()
    boulders = Boulder.query.filter(Boulder.sub_location_id == search_term).all()

    results = []

    sub_dict = convert_sublocation_dict(sub_location)
    results.append(sub_dict)


    boulder_dict = convert_boulders_dict(boulders)
    results.extend(boulder_dict)
    
    return jsonify({'data':results})


@app.route('/search.json', methods=['GET'])
def search():
    """searching for locations"""
    search_term = request.args.get('term')

    locations = Location.query.filter(Location.location_name.ilike('%'+search_term+'%')).all()
    sub_locations = Sub_location.query.filter(Sub_location.sub_location_name.ilike('%'+search_term+'%')).all()
    boulders = Boulder.query.filter(Boulder.boulder_name.ilike('%'+search_term+'%')).all()
    routes = Route.query.filter(Route.route_name.ilike('%'+search_term+'%')).all()

    results = []

    if locations:
        location_dict = convert_locations_dict(locations)
        results.extend(location_dict)
    
    if sub_locations:
        sub_dict = convert_sublocations_dict(sub_locations)
        results.extend(sub_dict)
    
    if boulders:
        boulder_dict = convert_boulders_dict(boulders)
        results.extend(boulder_dict)

    if routes:
        route_dict = convert_routes_dict(routes)
        results.extend(route_dict)
    

    return jsonify({'data':results})

@app.route('/add-b-comment.json', methods=["POST"])
def add_boulder_comment():
    """Adds a comment to a boulder"""
    

    comment = request.form.get("comment")
    boulder_id = session.get('boulder_id')
    user_id = session.get('user_id')
    
    timestamp = datetime.now()

    new_comment = Boulder_comment(boulder_comment=comment, 
                                boulder_id=boulder_id,
                                boulder_datetime=timestamp,
                                user_id=user_id)
    db.session.add(new_comment)
    db.session.commit()
    user = User.query.filter_by(user_id=user_id).first()
    username = user.username

    comment_dict= {}

    comment_dict['username'] = username
    comment_dict['comment'] = new_comment.boulder_comment
    comment_dict['date'] = new_comment.boulder_datetime.strftime('%d %B %Y')


    return jsonify(comment_dict)


@app.route('/add-r-comment.json', methods=["POST"])
def add_route_comment():
    """Adds a comment to a route"""

    comment = request.form.get("comment")
    route_id = session.get('route_id')
    user_id = session.get('user_id')
    
    timestamp = datetime.now()

    new_comment = Route_comment(route_comment=comment, 
                                route_id=route_id,
                                route_datetime=timestamp,
                                user_id=user_id)
    db.session.add(new_comment)
    db.session.commit()

    user = User.query.filter_by(user_id=user_id).first()
    username = user.username

    comment_dict= {}

    comment_dict['username'] = username
    comment_dict['comment'] = new_comment.route_comment
    comment_dict['date'] = new_comment.route_datetime.strftime('%d %B %Y')


    return jsonify(comment_dict)

@app.route('/rate-boulder', methods=["POST"])
def add_rate_boulder():
    """add rating for boulder """
    
    #gets the rate from the form
    rate = request.form.get('rate')
    
    user_id = request.form.get('user')
    boulder_id = request.form.get('boulder')
    
    # checks to see if the user has already rated the boulder
    rating = Boulder_rating.query.filter((Boulder_rating.boulder_id== boulder_id) &
                                        (Boulder_rating.user_id==user_id)).first()
    
    # if the user already has a rating, update the db
    if rating:
        rating.boulder_rating = rate
        
        db.session.add(rating)
    
    # if the user has not rated the boulder before make a new rating
    else:
        new_rating = Boulder_rating(boulder_id=boulder_id,
                                user_id=user_id,
                                boulder_rating=rate)
        # add to db
        db.session.add(new_rating)
    
    # save db
    db.session.commit()

    # return render_template("rate.html", rating=rate)
    return "success"


@app.route('/rate-route', methods=["POST"])
def add_rate_route():
    """Add rating to db for route"""

    # gets rating from form
    rate = request.form.get("rate")

    user_id = request.form.get('user')
    route_id = request.form.get('route')
    

    # looks for a rating for the route by the user in db
    rating = Route_rating.query.filter((Route_rating.route_id== route_id) &
                                        (Route_rating.user_id==user_id)).first()
    # If found update the db
    if rating:
        rating.route_rating = rate
        #add to the db
        db.session.add(rating)
    # not found make a new rating
    else:

        new_rating = Route_rating(route_id=route_id,
                                user_id=user_id,
                                route_rating=rate)
        # add to db
        db.session.add(new_rating)
    # save the db
    db.session.commit()

    return "success"



if __name__ == "__main__":
    # We have to set debug=True here, since it has to be True at the point
    # that we invoke the DebugToolbarExtension
    # app.debug = True
    app.debug = False

    connect_to_db(app)

    # Use the DebugToolbar
    # DebugToolbarExtension(app)

    app.run()
