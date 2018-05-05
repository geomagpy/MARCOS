// TODO make a class out of it , use jquery...
// plot magpy data coming over websocket from collector

    var serveraddr= location.host.split(':')[0];
    console.log(serveraddr);
    var wsconnection = new WebSocket('ws://' +serveraddr+ ':5000/');
    var signals = {};
    var table;
    
    console.log("plotws.js started");

// "import" smoothiechart javascripts
//    var importsmoothie = document.createElement('script');
//    importsmoothie.src = 'smoothie.js';
//    document.head.appendChild(importsmoothie);
//    var importsmoothiesettings = document.createElement('script');
//    importsmoothiesettings.src = 'smoothiesettings.js';
//    document.head.appendChild(importsmoothiesettings);

// Modidied import by leon May 2018
// https://stackoverflow.com/questions/950087/how-do-i-include-a-javascript-file-in-another-javascript-file

    function loadSmoothie(name, callback) {
        var importsmoothie = document.createElement('script');
        importsmoothie.src = name;
        // bind the event to callback
        importsmoothie.onreadystatechange = callback;
        importsmoothie.onload = callback;
        // Fire loading
        document.head.appendChild(importsmoothie);
    }

    var getsettings = function () {
        var importsmoothiesettings = document.createElement('script');
        importsmoothiesettings.src = 'smoothiesettings.js';
        document.head.appendChild(importsmoothiesettings);
    }

    loadSmoothie('smoothie.js', getsettings);

    function getCanvas(signalid) {
        try {
            canvas = makeCanvas(signalid);
            row = null;
        }
        catch (e) {
            canvas = null;
        }
        // default is table in maindiv, or we get a canvas from somewhere else
        if (canvas == null) {
            var row = document.createElement('tr');
            table.appendChild(row);
            var cell = document.createElement('td');
            row.appendChild(cell);
            var canvas = document.createElement('canvas');
            // TODO replace arbitrary number by settings or derive from screen width etc.
            canvas.width = "1000";
            cell.appendChild(canvas);
        }
        return [canvas,row];
    }

    function getDescrField(signalid,row) {
        try {
            descrField = makeDescrField(signalid,signals);
        }
        catch (e) {
            // only if canvas was created by default
            if (row) {
                // a new cell in the table
                var descrField = document.createElement('td');
                row.appendChild(descrField);
                iH = signals[signalid];
                descrField.innerHTML = iH.sensorid +'<BR>'+ iH.key +' : '+ iH.elem +' ['+ signals[signalid].unit +']';
            }
        }
        return descrField;
    }


    function addChart(signalid) {
        var [canvas,row] = getCanvas(signalid);
        // if there is a non default selection, other signals are not shown
        if (canvas) {
            var descrField = getDescrField(signalid,row);
            var chart = {};
            chart.smoothie = new SmoothieChart(smoothiesettings);
            chart.timeSeries = new TimeSeries();
            chart.smoothie.addTimeSeries(chart.timeSeries,timeseriessettings);
            chart.smoothie.streamTo(canvas,streamtosettings.Delay);
            return chart;
        }
    };
        

    wsconnection.onmessage = function (e) {
        if (e.data[0] == '#') {
            // header
            // # json
            var data = e.data.split('# ')[1];
            var head = JSON.parse(data);
            signalid = head.sensorid + '#' + head.nr;
            if (signals[signalid] == null) {
                // new header
                signals[signalid] = head;
                signals[signalid].chart = addChart(signalid);
                // result might look like:
                // { sensorid: "AD7714_0001_0001", nr: 0, unit: "mV", elem: "U", key: "var1", chart: Object }
                console.log('new header: sensor ' + signals[signalid].sensorid);
                //debug.innerHTML = 'new header: sensor ' + signals[signalid].sensorid;
            }
        } else {
            // data
            // sensorid: timestamp,data0,data1...
            var data = e.data.split(': ');
            var sensor = data[0];
            if (signals[sensor+'#0'] == null) {
                // no header yet
            } else {
                var data_arr = data[1].split(',');
                for (i=0; i < data_arr.length-1; i++) {
                    var signalid = sensor +'#'+ i.toString();
                    // catch not selected signals in non default mode
                    try {
                        signals[signalid].chart.timeSeries.append((data_arr[0]),Number(data_arr[i+1]));
                    }
                    catch (e) {}
                    //debug.innerHTML = data_arr[i+1];
                }
            }
        }
        // console.log('data from collector: ' + e.data);
    };
    wsconnection.onopen = function (){
        console.log('websocket connection open');
    };
    wsconnection.onerror = function (error){
        console.log('error: ' + error);
        connection.close();
    };

window.onload = function() {

    var maindiv = document.getElementById('maindiv');
    // TODO no need for a table, when no default
    table = document.createElement('table'); 
    maindiv.appendChild(table);

    debug1 = document.getElementById('debug');
}
