$(document).ready(function(){
    $('#loading').hide();

})

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
            $('#loading').show();
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
            $('#description').text('Failed');
            window.location = "/index.html"
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

// function addItem(){
//     type = document.getElementById("typePo").value;
//     nameItem = document.getElementById("nameItem").value;
//     description = document.getElementById("description").value;
//     storageLocation = document.getElementById("storageLocation").value;
//     quantity = document.getElementById("quantity").value;
//     price = document.getElementById("price").value;
//     note = document.getElementById("Note2").value;

//     document.getElementById("theItem").reset()

//     let totalPrice = Number(quantity) * Number(price);
//     console.log(totalPrice);
    

    
// }


// FUNGSI BIKINAN NAUFAL
function getAllDataItem() {
  
    // //////////////////////////////// Request ////////////////////////////////////////
    // autoComplete
    // var obj = new Object(),
    //     autoComplete = $('#poItemDropdown select').get()
    //     input = $('#addPoItem input').get()
    //     textarea = $('#addPoItem2 textarea').get()
    //     // autoComplete = document.querySelectorAll('.parent .child1');
    // for (let i = 0; i < autoComplete.length; i++) {
    //     var id = $(autoComplete).eq(i).attr("id"),
    //         val = $(autoComplete).eq(i).val()
    //     console.log(val)
    //     obj[`${id}`] = val
    // }

    // for (let i = 0; i < input.length; i++) {
    //     var id = $(input).eq(i).attr("id"),
    //         val = $(input).eq(i).val()
    //     console.log(val)
    //     obj[`${id}`] = val
    // }

    // for (let i = 0; i < textarea.length; i++) {
    //     var id = $(textarea).eq(i).attr("id"),
    //         val = $(textarea).eq(i).val()
    //     console.log(val)
    //     obj[`${id}`] = val
    // }

    
    // input (date)
    
    // var nameItem = $('#nameItem').val()
    // obj['nameItem'] = nameItem
    // // justification
    // var just = $('#justification').val()
    // obj['justification'] = just
    
    
    // //////////////////////////////// Item ////////////////////////////////////////
    var array = new Array(),
    rows = $('table.table tbody tr').get()
    rows.forEach(row => {
        
        var tds = $(row).find('td').get(),
        item_obj = new Object()
        tds.forEach(td => {
            var id = $(td).attr("id"),
            text = $(td).text()
            item_obj[`${id}`] = text
        })
        array.push(item_obj)
    })  
    document.getElementById("theItem").reset()

    console.log(array)
    
    // ///////////////////////////////// Data to send to Backend ///////////////////////////////////////
    // var obj_data = new Object()
    // obj_data["request_data"] = obj
    // obj_data["array_item"] = array
  
    // /////////////////////////////// Kirim pake Ajax //////////////////////////////////////
    // $.ajax({
    //   method: 'POST',
    //   url: 'http://localhost:9000/sendRequest',
    //   beforeSend : function(req){
    //     req.('Content-Type', 'application/json')
    //     req.setRequestHeader('Authorization', getCookie('token'))
    //   },
    //   data : obj_data,
    //   success: function(res){
    //     alert('berhasil')
    //   },
    //   error: function(res){
    //     alert('gagal')
    //   }
    // })
  }



  function addItemToTabel() {
    var item_name = $('#itemname').val()
    var item_type = $('#typePo').val()
    var description = $('#description').val()
    var storageLocation = $('#storageLocation').val()
    var quantity = $('#quantity').val()
    var price = $('#price').val()
    var note = $('#noteItem').val()

  
    // jQuery
    var table = $('table.table tbody'),
      row = table.find('tr')
    table.append(`<tr>
    <th id="noTablePo"scope="row">${row.length + 1}</th>
    <td id="itemDetail">
        ${item_name}
    </td>
    <td id="type">${item_type}</td>
    <td id="description2">${description}</td>
    <td id="storageLocation2">${storageLocation}</td>
    <td id="quantity2">${quantity}</td>
    <td id="price2">${price}</td>
    <td id="note2">${note}</td>
    <td id="action">
        <button type="submit" class="btn btn-primary btn-custom" id="actionChange">
            <i class="fas fa-fw fa-edit"></i> Change</button>
        <button type="submit" class="btn btn-danger btn-custom" id="actionDelete">
            <i class="fas fa-fw fa-trash-alt"></i> Delete</button>
    </td>


    
    </tr>`)
    document.getElementById("theItem").reset()
    sum = 0
    price = 0
    total_price = 0
    rows = $('table.table tbody tr').get()
      rows.forEach(row => {
        var tds = $(row).find('#quantity2').html(),
        sum = Number(tds)
        // console.log(sum)
        var tds2 = $(row).find('#price2').html(),
        price = Number(tds2)
        
        total_price += sum * price
        
        console.log(total_price)
        
        display = document.getElementById('totalAmount')
        display.value = total_price   
    })
  }

 