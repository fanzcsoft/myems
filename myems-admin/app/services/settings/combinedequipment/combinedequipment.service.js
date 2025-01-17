'use strict';
app.factory('CombinedEquipmentService', function($http) {
    return {
        getAllCombinedEquipments:function(headers, callback){
            $http.get(getAPI()+'combinedequipments', {headers})
            .then(function (response) {
                callback(response);
            }, function (response) {
                callback(response);
            });
        },
        searchCombinedEquipments: function(query, headers, callback) {
            $http.get(getAPI()+'combinedequipments', { params: { q: query } }, {headers})
            .then(function (response) {
                callback(response);
            }, function (response) {
                callback(response);
            });
        },
        addCombinedEquipment: function(combinedequipment, headers, callback) {
            $http.post(getAPI()+'combinedequipments',{data:combinedequipment}, {headers})
            .then(function (response) {
                callback(response);
            }, function (response) {
                callback(response);
            });
        },
        editCombinedEquipment: function(combinedequipment, headers, callback) {
            $http.put(getAPI()+'combinedequipments/'+combinedequipment.id,{data:combinedequipment}, {headers})
            .then(function (response) {
                callback(response);
            }, function (response) {
                callback(response);
            });
        },
        deleteCombinedEquipment: function(combinedequipment, headers, callback) {
            $http.delete(getAPI()+'combinedequipments/'+combinedequipment.id, {headers})
            .then(function (response) {
                callback(response);
            }, function (response) {
                callback(response);
            });
        }
    };
});
