function getCookie(cname) {
    var name = cname + "=";
    var decodedCookie = decodeURIComponent(document.cookie);
    var ca = decodedCookie.split(';');
    for(var i = 0; i <ca.length; i++) {
        var c = ca[i];
        while (c.charAt(0) == ' ') {
            c = c.substring(1);
        }
        if (c.indexOf(name) == 0) {
            return c.substring(name.length, c.length);
        }
    }
    return "";
}

function login(){
    $.ajax({
        method: 'POST',
        url: 'http://localhost:5000/login',
        beforeSend: function(req) {
            req.setRequestHeader("Content-Type", "application/json");
        },
        data : JSON.stringify({
            "email": document.getElementById('email').value,
            "password": document.getElementById('password').value
    
        }),
        success: function(res){
            document.cookie = `token=${res}`
            window.location = "/dashBoard.html"
        },
        error: function(err) {
            console.log(err)


        }
    })
}

function logout(){
    document.cookie = 'token=; expires=Sun 4 Jan 1920 00:00:00 UTC;';
    window.location ='/index.html';
}

function authRequester(){
    $.ajax({
        method: 'GET',
        url : 'http://localhost:5000/authorizationRequester',
        beforeSend: function (req) {
            req.setRequestHeader("Content-Type", "application/json")
            req.setRequestHeader("Authorization", getCookie('token'))
        },
        success: function(res){
            alert("Access Granted, Hi Requester!")
            window.location = '/createPo.html'
            
        },
        error: function(err){
            console.error(err)
            alert("Access Denied: your account is not registered as Requester")
        }
    })
     
}

function checkSession() {
    $.ajax({
        method: 'GET',
        url: 'http://localhost:5000/sessionCheck',
        beforeSend: function (req) {
            req.setRequestHeader("Content-Type", "application/json")
            req.setRequestHeader("Authorization", getCookie('token'))
        },
        success: function(res){
            
        },
        error: function(err){
            alert("Please login first")
            window.location = '/index.html'
        }
    })
}