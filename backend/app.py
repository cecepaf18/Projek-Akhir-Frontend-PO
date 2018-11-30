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


class Costcenter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    costcenter_name = db.Column(db.String)
    description = db.Column(db.String)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String())
    payroll_number = db.Column(db.Integer())
    photoprofile = db.Column(db.String())
    email = db.Column(db.String())
    password = db.Column(db.String())
    token = db.Column(db.String())
    position_id = db.Column(db.Integer, db.ForeignKey('roles.id'))


class Contract(db.Model):
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
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    currency = db.Column(db.String())
    plant = db.Column(db.String())

class Items(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String())
    type = db.Column(db.String())
    description = db.Column(db.String())
    storage_location = db.Column(db.String())
    quantity = db.Column(db.Integer())
    price = db.Column(db.Integer())
    note = db.Column(db.String())
    contract_id = db.Column(db.Integer, db.ForeignKey('contract.id'))

class Header(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    representative = db.Column(db.String())
    to_provide = db.Column(db.String())
    location = db.Column(db.String())
    note = db.Column(db.String())
    budget_source = db.Column(db.String())
    service_charge_type = db.Column(db.String())
    contract_id = db.Column(db.Integer, db.ForeignKey('contract.id'))


class Approval(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    scm_approval = db.Column(db.Integer())
    manager_approval = db.Column(db.Integer())
    contract_owner_approval = db.Column(db.Integer())
    contract_id = db.Column(db.Integer, db.ForeignKey('contract.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

#########################
####### NEXTFLOW ########
#########################

@app.route('/createRecord', methods=['POST'])
# inisiasi nextflow atau create record

def create_record():
    print(os.getenv('DEFINITION_ID'))
    if request.method == 'POST':
        decoded = jwt.decode(request.headers["Authorization"], jwtSecretKey, algorithms=['HS256'])
        request_data = request.get_json()
        req_username = decoded["username"]
                

        userDB = User.query.filter_by(user_name=req_username).first()
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

            # masukkin data ke database
            data_db = submit_to_database(record_id, submit_result["data"]["process_id"],req_username)
            print(submit_result["data"]["process_id"])

            # return berupa id dan statusnya
            return "data_db", 200
        else:
            return "Token not found", 404



def submit_record(record_id, user_token):
    # data template untuk submit record
    decoded = jwt.decode(request.headers["Authorization"], jwtSecretKey, algorithms=['HS256'])
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
    print(result)
    return result

# fungsi untuk submit data ke db
def submit_to_database(record_id, process_id,username):
    request_data = request.get_json()
    req_sap_contract_number = request_data['sap contract number']
    userDB = User.query.filter_by(user_name=username).first()
    data_db = Contract.query.filter_by(SAP_contract_number = req_sap_contract_number).first()
   
    data_db.record_id = record_id
    data_db.process_id = process_id
    data_db.user_id = userDB.id

    db.session.commit()
   
    return "Record berhasil dibuat"


@app.route('/submitToSCM', methods=['POST'])
# fungsi untuk gerakin flow dari requester ke manager
def submit_to_scm():
    decoded = jwt.decode(request.headers["Authorization"], jwtSecretKey, algorithm=['HS256'])
    request_data = request.get_json()
    req_comment = request_data['comment']
    req_SAP_contract_number = request_data['SAP contract number']
    req_username = decoded["username"]
    
    contract_doc = Contract.query.filter_by(SAP_contract_number = req_SAP_contract_number).first()
    process_id = contract_doc.process_id
    userDB = User.query.filter_by(user_name=req_username).first()    
    user_token = userDB.token
    print(process_id)
       
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


@app.route('/scmDecision', methods=['POST'])
# fungsi keputusan dari SCM
def scm_decision():
    if request.method == "POST":
        decoded = jwt.decode(request.headers["Authorization"], jwtSecretKey, algorithm=['HS256'])
        request_data = request.get_json()
        print(decoded['username'])
        req_username = decoded["username"]
        req_SAP_contract_number = request_data['SAP contract number']
        req_comment = request_data['comment']
        req_decision = request_data['decision']

        userDB = User.query.filter_by(user_name=req_username).first()
        contract_doc = Contract.query.filter_by(SAP_contract_number = req_SAP_contract_number).first()
        process_id = contract_doc.process_id
        print(process_id)
        

        def recursive():
            if userDB is not None:
                user_token = userDB.token
                query = "folder=app:task:all&page[number]=1&page[size]=10&filter[name]=SCM Reviewer&filter[state]=active&filter[process_id]=%s&filter[definition_id]=%s" % (process_id,os.getenv("DEFINITION_ID"))
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
        submitApproval(req_username,contract_doc.id)
        return "flow sudah sampai manager"


@app.route('/managerApproved', methods=['POST'])
# fungsi keputusan dari SCM
def managerApproved():
    if request.method == "POST":
        decoded = jwt.decode(request.headers["Authorization"], jwtSecretKey, algorithm=['HS256'])
        request_data = request.get_json()

        req_username = decoded["username"]
        req_SAP_contract_number = request_data['SAP contract number']
        req_comment = request_data['comment']
        
        userDB = User.query.filter_by(user_name=req_username).first()
        contract_doc = Contract.query.filter_by(SAP_contract_number = req_SAP_contract_number).first()
        process_id = contract_doc.process_id
        # contractDB = Contract.query.filter_by()

        def recursive():
            if userDB is not None:
                user_token = userDB.token
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
        submitApproval(req_username,contract_doc.id)
        return "flow sudah sampai CO"


@app.route('/ownerApproved', methods=['POST'])
# fungsi keputusan dari SCM
def ownerApproved():
    if request.method == "POST":
        decoded = jwt.decode(request.headers["Authorization"], jwtSecretKey, algorithm=['HS256'])
        request_data = request.get_json()

        req_username = decoded['username']
        req_SAP_contract_number = request_data['SAP contract number']
        req_comment = request_data['comment']
        
        userDB = User.query.filter_by(user_name=req_username).first()
        contract_doc = Contract.query.filter_by(SAP_contract_number = req_SAP_contract_number).first()
        process_id = contract_doc.process_id
        
        def recursive():
            if userDB is not None:
                user_token = userDB.token
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
        submitApproval(req_username,contract_doc.id)
        return "Release PO"
        

def submitApproval(username, contract_id):
    data_db = Approval.query.filter_by(contract_id = contract_id).first()
    dbUser = User.query.filter_by(user_name=username).first()
    role_id = dbUser.role

    if role_id == 2:
        data_db.scm_approval = 1
    elif role_id == 3:
        data_db.manager_approval = 1
    elif role_id == 4:
        data_db.contract_owner_approval =1

    db.commit()
    return "approved by ",str(dbUser.user_name)



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
        userDB = User.query.filter_by(email=email, password=password).first()

        if userDB:
            payload = {
                "email" : userDB.email,
                "username" : userDB.user_name                
            }
#    bikin token jwt
            encoded = jwt.encode(payload, jwtSecretKey, algorithm='HS256')
            return encoded, 201
        else:
            return "user does not exist",405
    else:
        return "Method not allowed", 405

# untuk memeriksa apakah sudah login
@app.route('/sessionCheck')
def checkSession():
    decoded = jwt.decode(request.headers["Authorization"], jwtSecretKey, algorithms=['HS256'])
    email = decoded['email']
    if email:
        return "bisa",200
    else:
        return "gagal",405

# routing to get user profile
@app.route('/userProfile')
def userProfile():
    decoded = jwt.decode(request.headers["Authorization"], jwtSecretKey, algorithms=['HS256'])
    email = decoded["email"]

    userDB = User.query.filter_by(email = email).first()
    userRole = Roles.query.filter_by(id = userDB.position_id).first()

    json_format = {
        "id" : userDB.id,
        "username" : userDB.user_name,
        "payroll number" : userDB.payroll_number,
        "photoprofile" : userDB.photoprofile,
        "email" :userDB.email,
        "position" : userRole.role
    }

    user_json = json.dumps(json_format)
    return user_json, 201

@app.route('/authorizationRequester')
def authRequester(): #buat ngebatesin selain requester
    
    decoded = jwt.decode(request.headers["Authorization"], jwtSecretKey, algorithms=['HS256'])
    email = decoded['email']

    userDB = User.query.filter_by(email=email).first()
    role = userDB.position_id
    if role == 1:
        return "Access Granted", 200
    else:
        return "Access Denied", 401

def authApprover():
    data = request.get_json()

    username = data.get('username')
    userDB = User.query.filter_by(user_name = username)
    role = userDB.role
    if role != 1:
        return "Access Granted", 200
    else:
        return "Access Denied", 401

# get all data for summary form
@app.route('/getsummary', methods=['GET'])
def getSummary():
    decoded = jwt.decode(request.headers["Authorization"], jwtSecretKey, algorithms=['HS256'])
    email = decoded["email"]

    data = request.get_json()
    contract_number = data['sap contract number']
    contract_doc = Contract.query.filter_by(SAP_contract_number = contract_number).first()
    contract_id = contract_doc.id

    userDB = User.query.filter_by(email = email, id = contract_doc.user_id).first()
    userRole = Roles.query.filter_by(id = userDB.position_id).first()
    headerDB = Header.query.filter_by(contract_id = contract_id).first()
    itemDB = Items.query.filter_by(contract_id = contract_id).all()

    summary = []

    item_json = {
        "item_name" : fields.String,
        "type" : fields.String,
        "description" : fields.String,
        "storage_location" : fields.String,
        "quantity" : fields.Integer,
        "price" : fields.Integer,
        "note" : fields.String,
        "contract_id" : fields.Integer
    }
    item_all = marshal(itemDB, item_json)

    json_format = {
        "requester name" : userDB.user_name,
        "payroll number" : userDB.payroll_number,
        "requester_position" : userRole.role,
        "process id" : contract_doc.process_id,
        "po start date" : contract_doc.po_start,
        "po completion date" : contract_doc.po_end,
        "bpm sr number" : contract_doc.BPM_SR_number,
        "bpm contract number" : contract_doc.BPM_contract_number,
        "bpm po number" : contract_doc.BPM_PO_number,
        "sap sr number" : contract_doc.SAP_SR_number,
        "sap contract number" : contract_doc.SAP_contract_number,
        "currency" : contract_doc.currency,
        "vendor name" : contract_doc.vendor_name,
        "plant" : contract_doc.plant,
        "representative" : headerDB.representative,
        "to provide" : headerDB.to_provide,
        "location" : headerDB.location,
        "note" : headerDB.note,
        "service charge type" : headerDB.service_charge_type       
    }

    summary.append(json_format)
    summary.append(item_all)
    summary_json = json.dumps(summary)

    return summary_json,200
    
# routing untuk menampilkan po approved oleh scm, manager, dan contract owner
@app.route('/completedPOList')
def completed_po():
    decoded = jwt.decode(request.headers["Authorization"], jwtSecretKey, algorithm=['HS256'])
    email = decoded["email"]
    approvalDB = Approval.query.all()
    completed_po = []

    for approval in approvalDB:
        if (approval.scm_approval + approval.manager_approval + approval.contract_owner_approval == 3):
            userDB = User.query.filter_by(id = approval.user_id, email = email).first()
            contractDB = Contract.query.filter_by(id = approval.contract_id).first()

            format_json = {
                "scm approval" : approval.scm_approval,
                "manager approval" : approval.manager_approval,
                "contract owner approval" : approval.contract_owner_approval,
                "requester name" : userDB.user_name,
                "sap conntract number" : contractDB.SAP_contract_number,
                "vendor name" : contractDB.vendor_name
            }

            completed_po.append(format_json)

    return json.dumps(completed_po)

# routing untuk menampilkan po yang belum selesai di approve
@app.route('/uncompletedPOList')
def uncompleted_po():
    decoded = jwt.decode(request.headers["Authorization"], jwtSecretKey, algorithm=['HS256'])
    email = decoded["email"]
    approvalDB = Approval.query.all()
    uncompleted_po = []

    for approval in approvalDB:
        if (approval.scm_approval + approval.manager_approval + approval.contract_owner_approval != 3):
            userDB = User.query.filter_by(id = approval.user_id, email = email).first()
            contractDB = Contract.query.filter_by(id = approval.contract_id).first()

            format_json = {
                "scm approval" : approval.scm_approval,
                "manager approval" : approval.manager_approval,
                "contract owner approval" : approval.contract_owner_approval,
                "requester name" : userDB.user_name,
                "sap conntract number" : contractDB.SAP_contract_number,
                "vendor name" : contractDB.vendor_name
            }

            uncompleted_po.append(format_json)

    return json.dumps(uncompleted_po)

# fungsi untuk menampilkan jumlah dokumen yang perlu di revisi oleh requester
@app.route('/totalRevise')
def get_revise():
    decoded = jwt.decode(request.headers["Authorization"], jwtSecretKey, algorithm=['HS256'])
    email = decoded["email"]
    userDB = User.query.filter_by(email = email).first()
    user_token = userDB.token

    query = "folder=app:task:all&filter[name]=Requester&filter[state]=active&filter[definition_id]=%s" % (
            os.getenv("DEFINITION_ID"))
        
    url = os.getenv("BASE_URL_TASK")+"?"+quote(query, safe="&=")
    r_get = requests.get(url, headers={"Content-Type": "Application/json", "Authorization": "Bearer %s" % user_token})
    result = json.loads(r_get.text)

    return str(len(result['data']))

# fungsi untuk menampilkan list po yang perlu di revisi
@app.route('/reviseList')
def reviset_list():
    decoded = jwt.decode(request.headers["Authorization"], jwtSecretKey, algorithm=['HS256'])
    email = decoded["email"]
    userDB = User.query.filter_by(email = email).first()
    user_token = userDB.token

    query = "folder=app:task:all&filter[name]=Requester&filter[state]=active&filter[definition_id]=%s" % (
            os.getenv("DEFINITION_ID"))
        
    url = os.getenv("BASE_URL_TASK")+"?"+quote(query, safe="&=")
    r_get = requests.get(url, headers={"Content-Type": "Application/json", "Authorization": "Bearer %s" % user_token})
    result = json.loads(r_get.text)

    to_revise = []
    for po in result['data']:
        process_id = po['process_id']
        contractDB = Contract.query.filter_by(process_id = process_id).first()
        userDB = User.query.filter_by(id = contractDB.user_id).first()
        json_format = {
            "sap contract number" : contractDB.SAP_contract_number,
            "requester" : userDB.user_name,
            "vendor name" : contractDB.vendor_name
        }
        to_revise.append(json_format)
    
    return json.dumps(to_revise)



@app.route('/getContract')
def getContract():
    decoded = jwt.decode(request.headers["Authorization"], jwtSecretKey, algorithm=['HS256'])

    email = decoded["email"]
    data = User.query.filter_by(email=email).first()
    dataUser = Contract.query.filter_by(user_id=data.id).all()
    
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


if __name__ == '__main__':
    app.run(debug=os.getenv("DEBUG"), host=os.getenv(
        "HOST"), port=os.getenv("PORT"))
