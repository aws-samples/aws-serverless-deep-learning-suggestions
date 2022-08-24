/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: MIT-0
 */
let map;
let submissionId;

function generateReportMarkerDescription(submission) {
    let description = "<span style='font-weight:bold'>"
    description += generateMarkerTitle(submission)
    description += "</span><br />"
    description += `<img src='/maint-img/${submissionId}' style="max-height:100px; width:auto;" alt="Picture of Damage" />`
    description += `<br />Report ${submissionId}`
    return description
}

function generateMarkerTitle(submission) {
    let description = ''
    submission['selected_reports'].forEach(function (report) {
        description += reportData[report]['name'] + ' / '
    });
    return description.substring(0, description.length - 3)
}

function generateRelevantReports(submission) {
    let description = ''
    let sortedArray = Object.keys(submission['relevant_reports']).map(function(key) {
        return [key, submission['relevant_reports'][key]];
    });
    sortedArray.sort(function(first, second) { return second[1] - first[1]; });
    for (let i = 0; i < sortedArray.length; i++) {
        description += `${reportData[sortedArray[i][0]]['name']} (${Math.round(sortedArray[i][1] * 10) / 10})<br />`
        if (i >= 5) { break }
    }
    return description.substring(0, description.length - 6)
}

function generateIdentifiedLabels(submission) {
    let description = ''
    let sortedArray = Object.keys(submission['ml_labels']).map(function(key) {
        return [key, submission['ml_labels'][key]];
    });
    sortedArray.sort(function(first, second) { return second[1] - first[1]; });
    for (let i = 0; i < sortedArray.length; i++) {
        description += `${sortedArray[i][0]} (${Math.round(sortedArray[i][1] * 10) / 10})<br />`
        if (i >= 5) { break }
    }
    return description.substring(0, description.length - 6)
}

function generateCoords(coords) {
    return `${coords['latitude']}<br />${coords['longitude']}`
}


async function initializeMap() {
    map = await AmazonLocation.createMap(
        { identityPoolId: awsConfigOptions.identity_pool_id },
        {
            container: "map",
            center: [-98.46, 37.52], // Geographic Center of US
            zoom: 3.67,
            bearing: 0,
            pitch: 60,
            style: 'DL-Suggest-Blog-Map-' + awsConfigOptions.unique_suffix,
            hash: true,
        }
    );
    map.addControl(new maplibregl.NavigationControl(), "top-left");

    map.on('load', function () {
        map.resize();
        map.loadImage(
            'https://maplibre.org/maplibre-gl-js-docs/assets/custom_marker.png',
            // Add an image to use as a custom marker
            function (error, image) {
                if (error) throw error;
                let submissionResponse = $.ajax({
                    type: "GET",
                    url: `${awsConfigOptions.api_base_url}/submissions?status=submitted`,
                    headers: {
                        'X-API-Key': awsConfigOptions.api_key
                    },
                    async: false
                });
                let reportResponse = $.ajax({
                    type: "GET",
                    url: `${awsConfigOptions.api_base_url}/reports`,
                    headers: {
                        'X-API-Key': awsConfigOptions.api_key
                    },
                    async: false
                });
                window.reportData = reportResponse.responseJSON
                window.submissionData = submissionResponse.responseJSON
                window.placesData = []
                window.submissionData.forEach(function (submission) {
                    submissionId = submission['pk'].replace('submission_', '')
                    // Prefer Image Coordinates
                    let coord_long = (submission['coords_image']['longitude'] != 0) ? submission['coords_image']['longitude'] : submission['coords_browser']['longitude']
                    let coord_lat = (submission['coords_image']['latitude'] != 0) ? submission['coords_image']['latitude'] : submission['coords_browser']['latitude']
                    let newPlace = {
                        'type': 'Feature',
                        'properties': {
                            'description': generateReportMarkerDescription(submission),
                            'submission_id': submissionId
                        },
                        'geometry': {
                            'type': 'Point',
                            'coordinates': [coord_long, coord_lat]
                        }
                    }
                    window.placesData.push(newPlace)
                });
                map.addImage('custom-marker', image);

                map.addSource('places', {
                    'type': 'geojson',
                    'data': {
                        'type': 'FeatureCollection',
                        'features': window.placesData
                    }
                });

                // Add a layer showing the places.
                map.addLayer({
                    'id': 'places',
                    'type': 'symbol',
                    'source': 'places',
                    'layout': {
                        'icon-image': 'custom-marker',
                        'icon-overlap': 'always'
                    }
                });
            }
        );

        // Create a popup, but don't add it to the map yet.
        let popup = new maplibregl.Popup({
            closeButton: false,
            closeOnClick: false
        });

        map.on('click', 'places', function (e) {
            submissionId = e.features[0].properties.submission_id;
            let submission = {}
            window.submissionData.forEach(function (thisSubmission) {
                let loopSubId = thisSubmission['pk'].replace('submission_', '')
                if (submissionId == loopSubId) {
                    submission = thisSubmission
                }
            });
            $('#details-title').text(generateMarkerTitle(submission))
            $('#details-card-relevant-reports').html(generateRelevantReports(submission))
            $('#details-card-identified-labels').html(generateIdentifiedLabels(submission))
            $('#details-card-location-image').html(generateCoords(submission['coords_image']))
            $('#details-card-location-mobile').html(generateCoords(submission['coords_browser']))
            $('#details-card-last-status').text(moment(new Date(submission['timestamp_submitted'])).fromNow())
            $('#details-card-submission-id').text(submission['pk'].replace('submission_', ''))
            $('#instruction-card').css('display','none');
            $('#details-card').css('display','block');
            $('#details-img-container').css('display', 'block');
            $('#details-img').attr('src', `/maint-img/${submissionId}`)
            $('#details-img-link').attr('href', `/maint-img/${submissionId}`)
            console.log(e.features)
        });


        map.on('mouseenter', 'places', function (e) {
            // Change the cursor style as a UI indicator.
            map.getCanvas().style.cursor = 'pointer';

            let coordinates = e.features[0].geometry.coordinates.slice();
            let description = e.features[0].properties.description;

            // Ensure that if the map is zoomed out such that multiple
            // copies of the feature are visible, the popup appears
            // over the copy being pointed to.
            while (Math.abs(e.lngLat.lng - coordinates[0]) > 180) {
                coordinates[0] += e.lngLat.lng > coordinates[0] ? 360 : -360;
            }

            // Populate the popup and set its coordinates
            // based on the feature found.
            popup.setLngLat(coordinates).setHTML(description).addTo(map);
        });

        map.on('mouseleave', 'places', function () {
            map.getCanvas().style.cursor = '';
            popup.remove();
        });
    });

}
initializeMap();

$("#details-card-resolve-button").click(function(e) {
    e.preventDefault();
    $('#details-card-resolve-button').prop("disabled", true);
    $('#details-card-resolve-button').html('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Resolving...')
    let submissionUUID = $('#details-card-submission-id').text()
    let payload = { 'action': 'resolve' }
    $.ajax({
        type: 'PATCH',
        url: `${awsConfigOptions.api_base_url}/submission/${submissionUUID}`,
        headers: {
            "X-API-Key": awsConfigOptions.api_key
        },
        data: JSON.stringify(payload),
        success: function(result) {
            console.log('Success:')
            console.log(result)
            console.log(window.placesData)
            for (let i = 0; i < window.placesData.length; i++) {
                if (window.placesData[i].properties.submission_id == submissionUUID) {
                    window.placesData.splice(i, 1);
                }
            }
            console.log(window.placesData)
            map.getSource('places').setData({
                'type': 'FeatureCollection',
                'features': window.placesData
            });
            $('#details-card').css('display','none');
            $('#details-img-container').css('display', 'none');
            $('#instruction-card').css('display','block');
            $('#details-card-resolve-button').prop("disabled", false);
            $('#details-card-resolve-button').html('Resolve');
        },
        error: function(result) {
            console.log('Error:')
            console.log(result)
        }
    });

});
