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
    document.cookie = 'username=; expires=Sat 25 Aug 2018 00:00:00 UTC;'
}