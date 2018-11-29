from flask import Flask, request, json, session, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS, cross_origin
from flask_restful import marshal, fields
from requests.utils import quote
import requests
import datetime
import os
import jwt


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:abahaos38@localhost:5432/purchase_order'
app.config['SECRET_KEY'] = os.urandom(24)
CORS(app, support_credentials=True)
db = SQLAlchemy(app)
jwtSecretKey = "companysecret"


##############################
########## DATABASE ##########
##############################

class Roles(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String())


class costcenter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    costcenter_name = db.Column(db.String)
    description = db.Column(db.String)


class user(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String())
    payroll_number = db.Column(db.Integer())
    photoprofile = db.Column(db.String())
    email = db.Column(db.String())
    password = db.Column(db.String())
    token = db.Column(db.String())
    position_id = db.Column(db.Integer, db.ForeignKey('roles.id'))


class contract(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    po_start = db.Column(db.String())
    po_end = db.Column(db.String())
    vendor_name = db.Column(db.String())
    scope_of_work = db.Column(db.String())
    total_price = db.Column(db.Integer())
    SAP_contract_number = db.Column(db.String())
    SAP_SR_number = db.Column(db.String())
    BPM_contract_number = db.Column(db.String())
    BPM_SR_number = db.Column(db.String())
    BPM_PO_number = db.Column(db.String())
    cost_center_id = db.Column(db.Integer, db.ForeignKey('costcenter.id'))
    record_id = db.Column(db.Integer())
    process_id = db.Column(db.Integer())


class items(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String())
    type = db.Column(db.String())
    description = db.Column(db.String())
    storage_location = db.Column(db.String())
    quantity = db.Column(db.Integer())
    price = db.Column(db.Integer())
    note = db.Column(db.String())
    contract_id = db.Column(db.Integer, db.ForeignKey('contract.id'))


class approval(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    scm_approval = db.Column(db.Integer())
    manager_approval = db.Column(db.Integer())
    contract_owner_approval = db.Column(db.Integer())
    contract_id = db.Column(db.Integer, db.ForeignKey('contract.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


#########################
####### NEXTFLOW ########
#########################

@app.route('/submitToSCM', methods=['POST'])
# inisiasi nextflow atau create record

def create_record():
    if request.method == 'POST':
        request_data = request.get_json()
        req_email = request_data['email']
        req_comment = request_data['comment']

        userDB = user.query.filter_by(email=req_email).first()
        if userDB is not None:
            user_token = userDB.token
            print(user_token)
            # data template untuk create record
            record_instance = {
                "data": {
                    "definition": {
                        "id": os.getenv('DEFINITION_ID')
                    }
                }
            }

            # submit ke nextflow
            r = requests.post(os.getenv("BASE_URL_RECORD"), data=json.dumps(record_instance), headers={
                "Content-Type": "application/json", "Authorization": "Bearer %s" % user_token})

            # result from create record
            result = json.loads(r.text)
            record_id = result["data"]["id"]

            # sumbit flow menggunakan record_id dan token
            submit_result = submit_record(record_id, user_token)

            # gerakin flow darri requester ke manager
            submit_to_scm(
                req_comment, user_token, submit_result['data']['process_id'])

            # masukkin data ke database
            data_db = submit_to_database(
                record_id, submit_result['data']['process_id'])

            # return berupa id dan statusnya
            return "data_db", 200
        else:
            return "Token not found", 404

# fungsi untuk sumbit record dan gerakin flow ke requester


def submit_record(record_id, user_token):
    # data template untuk submit record
    record_instance = {
        "data": {
            "form_data": {
                "pVRequester": "riki_requester_po@makersinstitute.com",
                "pVSCM": "cecep_scm_po@makersinstitute.com",
                "pVManager" : "adinda_manager_po@makersinstitute.com",
                "pVOwner" : "naufal_co_po@makersinstitute.com"
            },
            "comment": "Initiated"
        }
    }
    request_data = json.dumps(record_instance)

    # submit ke nextflow untuk dapat process_id tiap pesanan masuk/flow
    r = requests.post(os.getenv("BASE_URL_RECORD") + "/" + record_id + "/submit", data=request_data, headers={
        "Content-Type": "application/json", "Authorization": "Bearer %s" % user_token})

    result = json.loads(r.text)
    # print("submit record", result)
    return result

# fungsi untuk gerakin flow dari requester ke manager


def submit_to_scm(req_comment, user_token, process_id):
    print("ini process id", process_id)
    # get task id and pVManager name

    def recursive():
        query = "folder=app:task:all&filter[name]=Requester&filter[state]=active&filter[definition_id]=%s&filter[process_id]=%s" % (
            os.getenv("DEFINITION_ID"), process_id)

        url = os.getenv("BASE_URL_TASK")+"?"+quote(query, safe="&=")
        r_get = requests.get(url, headers={
                             "Content-Type": "Application/json", "Authorization": "Bearer %s" % user_token})
        result = json.loads(r_get.text)
        print("loading")
        if result['data'] is None or len(result['data']) == 0:
            recursive()
        else:
            # get scm email and task id
            SCM_email = result['data'][0]['form_data']['pVSCM']
            task_id = result['data'][0]['id']
            print(SCM_email)
            # gerakin flow ke scm dari requester
            submit_data = {
                "data": {
                    "form_data": {
                        "pVSCM": SCM_email

                    },
                    "comment": req_comment
                }
            }

            r_post = requests.post(os.getenv("BASE_URL_TASK") + "/" + task_id + "/submit", data=json.dumps(submit_data), headers={
                "Content-Type": "application/json", "Authorization": "Bearer %s" % user_token})
            result = json.loads(r_post.text)
            print(result)
            return r_get.text

    recursive()
    return "result"


# fungsi untuk submit data ke db
def submit_to_database(record_id, process_id):
    # request_data = request.get_json()
    # req_cost_center_id = request_data['data']['contract']['cost center id']

    data_db = Contract.query.filter_by(SAP_contract_number="MDC-1234-VII")

    data_db.record_id = record_id
    data_db.process_id = process_id

    db.session.commit()
    db.session.flush()
    
    if data_db.id is not None:
        return str(data_db.id)
    else:
        return None


@app.route('/scmDecision', methods=['POST'])
# fungsi keputusan dari SCM
def scm_decision():
    if request.method == "POST":
        request_data = request.get_json()
        req_email = request_data['email']
        req_comment = request_data['comment']
        req_decision = request_data['decision']
        userDB = user.query.filter_by(email=req_email).first()
        # contractDB = Contract.query.filter_by()

        def recursive():
            if userDB is not None:
                user_token = userDB.token
                print(user_token)
                process_id = "instances:bpmn:a119dc5a-702d-43a4-a1b4-b2593f9da21f" 
                query = "folder=app:task:all&page[number]=1&page[size]=10&filter[name]=SCM Reviewer&filter[state]=active&filter[process_id]=%s&filter[definition_id]=%s" % (process_id,os.getenv("DEFINITION_ID"))
                url = os.getenv("BASE_URL_TASK")+"?"+quote(query, safe="&=")

                r_get = requests.get(url, headers={
                    "Content-Type": "Application/json", "Authorization": "Bearer %s" % user_token
                })
                result = json.loads(r_get.text)
                print("loading")
                print(result)
                if result['data'] is None or len(result['data']) == 0:
                    recursive()
                else:
                    # get manager email and task id
                    manager_email = result['data'][0]['form_data']['pVManager']
                    task_id = result['data'][0]['id']
                    print(manager_email)
                    # gerakin flow ke manager dari SCM
                    submit_data = {
                        "data": {
                            "form_data": {
                                "pVManager": manager_email,
                                "pVAction": req_decision

                            },
                            "comment": req_comment
                        }
                    }
                    
                    r_post = requests.post(os.getenv("BASE_URL_TASK") + "/" + task_id + "/submit", data=json.dumps(submit_data), headers={
                        "Content-Type": "application/json", "Authorization": "Bearer %s" % user_token})
                    result = json.loads(r_post.text)
                    print(result)
                    return r_get.text

        recursive()
        return "flow sudah sampai manager"


@app.route('/managerApproved', methods=['POST'])
# fungsi keputusan dari SCM
def managerApproved():
    if request.method == "POST":
        request_data = request.get_json()
        req_email = request_data['email']
        req_comment = request_data['comment']
        
        userDB = user.query.filter_by(email=req_email).first()
        # contractDB = Contract.query.filter_by()

        def recursive():
            if userDB is not None:
                user_token = userDB.token
                process_id = "instances:bpmn:a119dc5a-702d-43a4-a1b4-b2593f9da21f" 
                query = "folder=app:task:all&page[number]=1&page[size]=10&filter[name]=Manager Approval&filter[state]=active&filter[process_id]=%s&filter[definition_id]=%s" % (process_id,os.getenv("DEFINITION_ID"))
                url = os.getenv("BASE_URL_TASK")+"?"+quote(query, safe="&=")

                r_get = requests.get(url, headers={
                    "Content-Type": "Application/json", "Authorization": "Bearer %s" % user_token
                })
                result = json.loads(r_get.text)
                print("loading")
                
                if result['data'] is None or len(result['data']) == 0:
                    recursive()
                else:
                    # get manager email and task id
                    owner_email = result['data'][0]['form_data']['pVOwner']
                    task_id = result['data'][0]['id']
                    print(owner_email)
                    # gerakin flow ke manager dari SCM
                    submit_data = {
                        "data": {
                            "form_data": {
                                "pVOwner": owner_email
                                
                            },
                            "comment": req_comment
                        }
                    }
                    
                    r_post = requests.post(os.getenv("BASE_URL_TASK") + "/" + task_id + "/submit", data=json.dumps(submit_data), headers={
                        "Content-Type": "application/json", "Authorization": "Bearer %s" % user_token})
                    result = json.loads(r_post.text)
                    print(result)
                    return r_get.text

        recursive()
        return "flow sudah sampai CO"


@app.route('/ownerApproved', methods=['POST'])
# fungsi keputusan dari SCM
def ownerApproved():
    if request.method == "POST":
        request_data = request.get_json()
        req_email = request_data['email']
        req_comment = request_data['comment']
        
        userDB = user.query.filter_by(email=req_email).first()
        # contractDB = Contract.query.filter_by()

        def recursive():
            if userDB is not None:
                user_token = userDB.token
                process_id = "instances:bpmn:a119dc5a-702d-43a4-a1b4-b2593f9da21f" 
                query = "folder=app:task:all&page[number]=1&page[size]=10&filter[name]=Contract Owner Approval&filter[state]=active&filter[process_id]=%s&filter[definition_id]=%s" % (process_id,os.getenv("DEFINITION_ID"))
                url = os.getenv("BASE_URL_TASK")+"?"+quote(query, safe="&=")

                r_get = requests.get(url, headers={
                    "Content-Type": "Application/json", "Authorization": "Bearer %s" % user_token
                })
                result = json.loads(r_get.text)
                print("loading")
                
                if result['data'] is None or len(result['data']) == 0:
                    recursive()
                else:
                    # get task id
                    task_id = result['data'][0]['id']
                    
                    # gerakin flow ke manager dari SCM
                    submit_data = {
                        "data": {
                            "form_data": {
                                
                                
                            },
                            "comment": req_comment
                        }
                    }
                    
                    r_post = requests.post(os.getenv("BASE_URL_TASK") + "/" + task_id + "/submit", data=json.dumps(submit_data), headers={
                        "Content-Type": "application/json", "Authorization": "Bearer %s" % user_token})
                    result = json.loads(r_post.text)
                    print(result)
                    return r_get.text

        recursive()
        return "Release PO"
        

        




########################
####### BACKEND ########
########################

# routing login
@app.route('/login', methods=['POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()

        email = data.get('email')
        password = data.get('password')
        # print(username, password)
        userDB = user.query.filter_by(email=email, password=password).first()

        if userDB:
            payload = {
                "email" : userDB.email
            }
#    bikin token jwt
            encoded = jwt.encode(payload, jwtSecretKey, algorithm='HS256')
            return encoded, 201
        else:
            return "user does not exist",405
    else:
        return "Method not allowed", 405


# # get all data for summary form
# @app.route('/getsummary', methods=['GET'])
# def getSummary():
#     request_data = request.get_json()
#     contract_id = request_data('contract_id')

#     approval = Approval.query.filter_by(contract_id = contract_id)
#     comment = Comment.query.filter_by(contract_id = contract_id)
#     contract = Contract.query.filter_by(id = contract_id)
#     costcenter = Costcenter.query.filter_by(id= Contract.cost_center_id)
#     items = Items.query.filter_by(contract_id = contract_id)
#     user = user.query.filter_by(id = approval.user_id)

#     item_json = {
#         "item_name" : fields.String,
#         "type" : fields.String,
#         "description" : fields.String,
#         "storage_location" : fields.String,
#         "quantity" : fields.Integer,
#         "price" : fields.Integer,
#         "note" : fields.String,
#         "contract_id" : fields.Integer
#     }


#     return (json.dumps(marshal(po_items, item_json)))

# Authorization
# buat ngebatesin cuma requester yang bisa create PO
@app.route('/authorizationRequester')
def authRequester(): #buat ngebatesin selain requester
    
    decoded = jwt.decode(request.headers["Authorization"], jwtSecretKey, algorithms=['HS256'])
    email = decoded['email']

    userDB = user.query.filter_by(email=email).first()
    role = userDB.position_id
    if role == 1:
        return "Access Granted", 200
    else:
        return "Access Denied", 401

# def authApprover():
#     data = request.get_json()

#     username = data.get('username')
#     userDB = user.query.filter_by(user_name = username)
#     role = userDB.role
#     if role != 1:
#         return "Access Granted", 200
#     else:
#         return "Access Denied", 401

@app.route('/getContract')
def getContract():
    decoded = jwt.decode(request.headers["Authorization"], jwtSecretKey, algorithm=['HS256'])

    email = decoded["email"]
    data = user.query.filter_by(email=email).first()
    dataUser = contract.query.filter_by(user_id=data.id).all()
    
    if dataUser:
        contractDetail = {
            "po_start" : fields.String,
            "po_end" : fields.String,
            "vendor_name" : fields.String,
            "scope_of_work" : fields.String,
            "total_price" : fields.Integer,
            "SAP_contract_number" : fields.String,
            "SAP_SR_number" : fields.String,
            "BPM_contract_number" : fields.String,
            "BPM_SR_number" : fields.String,
            "BPM_PO_number" : fields.String,
            "cost_center_id" : fields.Integer

        }

        return (json.dumps(marshal(dataUser, contractDetail))) 

# buat nambahin ke database table item
@app.route('/addItem', methods=['POST'])
def addItem():
    data = request.get_json()

@app.route('/sessionCheck')
def checkSession():
    decoded = jwt.decode(request.headers["Authorization"], jwtSecretKey, algorithms=['HS256'])
    email = decoded['email']
    if email:
        return "bisa",200
    else:
        return "gagal",405




if __name__ == '__main__':
    app.run(debug=os.getenv("DEBUG"), host=os.getenv("HOST"), port=os.getenv("PORT"))
