/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: MIT-0
 */
AWS.config.update({
    region: awsConfigOptions.identity_pool_id.split(':')[0],
    credentials: new AWS.CognitoIdentityCredentials({
        IdentityPoolId: awsConfigOptions.identity_pool_id
    })
});

let myInput = document.getElementById('myFileInput');
let myFileUploadLabel = document.getElementById('myFileUploadLabel');
let submissionUUID = ''
function showPic() {
    if (myInput.files && myInput.files[0]) {
        let reader = new FileReader();

        reader.onload = function (e) {
            $('#upload-placeholder').css("display", "none");
            $('#upload-preview-container').removeClass("d-none");
            $('#upload-preview').attr('src', e.target.result);
        };
        reader.readAsDataURL(myInput.files[0]);
    }
}
function sendPic() {
    $("#upload-placeholder").unbind('click');
    $("#upload-preview-container").unbind('click');
    let file = myInput.files[0];
    submissionUUID = uuidv4()
    let s3 = new AWS.S3({
        apiVersion: "2006-03-01",
    });
    let upload = new AWS.S3.ManagedUpload({
        service: s3,
        params: {
            Body: file,
            Bucket: 'dl-suggest-blog-uploaded-images-' + awsConfigOptions.unique_suffix,
            Key: `maint-img/${submissionUUID}`,
        },
    });
    $('#upload-progress-bar').css("display", "flex");
    $('#upload-selector').slideUp()
    upload.on('httpUploadProgress', (event) => {
        let pct = Math.floor(event.loaded * 100 / event.total)
        $('#upload-progress-bar .progress-bar').css('width', pct+'%').attr('aria-valuenow', pct);
        if (pct > 30) {
            $('#upload-progress-bar .progress-bar').text('Uploading');
        }
    });
    upload.send(function (err, data) {
        if (err) {
            console.log("Error", err.code, err.message);
            alert("There was an error uploading the file, please try again");
        } else {
            $('#upload-progress-bar .progress-bar').text('Processing');
            $('#upload-progress-bar .progress-bar').addClass('progress-bar-striped').addClass('progress-bar-animated');
            window.pollLimit = 100
            getSubmissionLongPoll(submissionUUID)
        }
    });
}
myInput.addEventListener('change', showPic, false);
myFileUploadLabel.addEventListener('click', sendPic, false);

function displayProcessedImage(submission_data) {
    let relevantCount = 0
    let newHTMLRelevant = '<h3>Looks like you\'re reporting...</h3>'
    let sortedArray = Object.keys(submission_data['relevant_reports']).map(function(key) {
        return [key, submission_data['relevant_reports'][key]];
    });
    sortedArray.sort(function(first, second) { return second[1] - first[1]; });
    for (const item of sortedArray) {
        newHTMLRelevant += `<input type="checkbox" class="btn-check" id="btn_${item[0]}" autocomplete="off">`
        newHTMLRelevant += `<label class="btn btn-outline-primary mx-1 mb-3" for="btn_${item[0]}">${window.reports[item[0]]['name']}</label>`
        relevantCount++;
    }
    let otherCount = 0
    const relevantReportIds = Object.keys(submission_data['relevant_reports']);
    let newHTMLRest = ''
    if (relevantCount > 0) {
        newHTMLRest += '<h3>Something else?</h3>'
    } else {
        newHTMLRest += '<h3>What are you reporting?</h3>'
    }
    for (const [reportId, reportObj] of Object.entries(window.reports)) {
        if (!relevantReportIds.includes(reportId)) {
            newHTMLRest += `<input type="checkbox" class="btn-check" id="btn_${reportId}" autocomplete="off">`
            newHTMLRest += `<label class="btn btn-outline-primary mx-1 mb-3" for="btn_${reportId}">${window.reports[reportId]['name']}</label>`
            otherCount++;
        }
    }
    $('#upload-progress-bar').slideUp();
    if (relevantCount > 0) {
        $("#reports-suggested").html(newHTMLRelevant);
        $("#reports-suggested").show();
    }
    if (otherCount > 0) {
        $("#reports-other").html(newHTMLRest);
        $("#reports-suggested").show();
    }
    $("#reports").show();
}

async function getSubmissionLongPoll(subUUID) {
    const submission_data = await getSubmission(subUUID);

    if (submission_data) {
        displayProcessedImage(submission_data);
    } else if (window.pollLimit == 0) {
        console.log("Submission Polling Timeout")
    } else {
        setTimeout(() => {
            getSubmissionLongPoll(subUUID);
        }, 500);
    }
}
  
async function getSubmission(subUUID) {
    let response = $.ajax({
        type: "GET",
        url: `${awsConfigOptions.api_base_url}/submission/${subUUID}`,
        headers: {
            "X-API-Key": awsConfigOptions.api_key
        },
        async: false
    });
    window.pollLimit -= 1
    if (response.status == 200) {
        return JSON.parse(response.responseText)
    } else {
        return false
    }
}

function uuidv4() {
    return ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c =>
        (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
    );
}

$(document).ready(function() {
    let request = new XMLHttpRequest();
    request.open("GET", `${awsConfigOptions.api_base_url}/reports`, true);
    request.setRequestHeader("X-API-Key", awsConfigOptions.api_key);
    request.onload = function (e) {
        if (request.readyState === 4) {
            if (request.status === 200) {
                window.reports = JSON.parse(request.responseText);
            } else {
                console.error(request.statusText);
            }
        }
    };
    request.onerror = function (e) {
        console.error(request.statusText);
    };
    request.send(null);
});

function getLocation() {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(showPosition);
    } else {
        x.innerHTML = "Geolocation is not supported by this browser.";
    }
}

function submitReport(coordLat, coordLon) {
    let payload = {
        'action': 'submit',
        'selected_reports': [],
        'coords': {
            'latitude': coordLat,
            'longitude': coordLon
        }
    }
    $('#reports .btn-check:checked').each(function(index) {
        payload['selected_reports'].push($(this).attr('id').replace('btn_report', 'report'))
    });
    $.ajax({
        type: 'PATCH',
        url: `${awsConfigOptions.api_base_url}/submission/${submissionUUID}`,
        headers: {
            "X-API-Key": awsConfigOptions.api_key
        },
        data: JSON.stringify(payload),
        success: function(result) {
            console.log(result)
            const subDate = new Date(result['timestamp_submitted'])
            $('#submission-confirmation').text('Received!');
            $('#submission-timestamp').text(subDate.toLocaleDateString("en-US") + ' @ ' + subDate.toLocaleTimeString("en-US"));
            $('#submission-id').text(result['pk'].replace('submission_', ''));
        },
        error: function(result) {
            console.log(result)
            $('#submission-confirmation').text('Error! See Console Log');
        }
    });
}


$("#reports-submit").click(function(e) {
    e.preventDefault();
    $('#getting-location').show()
    $('#reports').slideUp()
    navigator.geolocation.getCurrentPosition(function onSuccess(position) {
        const {
            latitude,
            longitude
        } = position.coords;
        $('#getting-location').slideUp()
        $('#thanks').show()
        submitReport(latitude, longitude)
    }, function onError() {
        $('#getting-location').slideUp()
        $('#thanks').show()
        submitReport(0, 0)
    });
});

$("#upload-placeholder").click(function(){ $('#myFileInput').trigger('click'); });
$("#upload-preview-container").click(function(){ $('#myFileInput').trigger('click'); });