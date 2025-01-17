'use strict';

app.controller('PhotovoltaicPowerStationController', function(
    $scope,
    $rootScope,
    $window,
    $translate,
    $uibModal,
    CostCenterService,
    ContactService,
    PhotovoltaicPowerStationService,
    toaster,
    SweetAlert) {
	$scope.cur_user = JSON.parse($window.localStorage.getItem("myems_admin_ui_current_user"));
	$scope.getAllCostCenters = function() {
		let headers = { "User-UUID": $scope.cur_user.uuid, "Token": $scope.cur_user.token };
		CostCenterService.getAllCostCenters(headers, function (response) {
			if (angular.isDefined(response.status) && response.status === 200) {
				$scope.costcenters = response.data;
			} else {
				$scope.costcenters = [];
			}
		});
	};

	$scope.getAllContacts = function() {
		let headers = { "User-UUID": $scope.cur_user.uuid, "Token": $scope.cur_user.token };
		ContactService.getAllContacts(headers, function (response) {
			if (angular.isDefined(response.status) && response.status === 200) {
				$scope.contacts = response.data;
			} else {
				$scope.contacts = [];
			}
		});
	};

	$scope.getAllPhotovoltaicPowerStations = function() {
		let headers = { "User-UUID": $scope.cur_user.uuid, "Token": $scope.cur_user.token };
		PhotovoltaicPowerStationService.getAllPhotovoltaicPowerStations(headers, function (response) {
			if (angular.isDefined(response.status) && response.status === 200) {
				$scope.photovoltaicpowerstations = response.data;
			} else {
				$scope.photovoltaicpowerstations = [];
			}
		});
	};

	$scope.addPhotovoltaicPowerStation = function() {
		var modalInstance = $uibModal.open({
			templateUrl: 'views/settings/photovoltaicpowerstation/photovoltaicpowerstation.model.html',
			controller: 'ModalAddPhotovoltaicPowerStationCtrl',
			windowClass: "animated fadeIn",
			resolve: {
				params: function() {
					return {
						costcenters: angular.copy($scope.costcenters),
						contacts: angular.copy($scope.contacts),
					};
				}
			}
		});
		modalInstance.result.then(function(photovoltaicpowerstation) {
			photovoltaicpowerstation.cost_center_id = photovoltaicpowerstation.cost_center.id;
			photovoltaicpowerstation.contact_id = photovoltaicpowerstation.contact.id;
			let headers = { "User-UUID": $scope.cur_user.uuid, "Token": $scope.cur_user.token };
			PhotovoltaicPowerStationService.addPhotovoltaicPowerStation(photovoltaicpowerstation, headers, function(response) {
				if (angular.isDefined(response.status) && response.status === 201) {
					toaster.pop({
						type: "success",
						title: $translate.instant("TOASTER.SUCCESS_TITLE"),
						body: $translate.instant("TOASTER.SUCCESS_ADD_BODY", {template: $translate.instant("COMMON.PHOTOVOLTAIC_POWER_STATION")}),
						showCloseButton: true,
					});
					$scope.$emit('handleEmitPhotovoltaicPowerStationChanged');
				} else {
					toaster.pop({
						type: "error",
						title: $translate.instant("TOASTER.ERROR_ADD_BODY", { template: $translate.instant("COMMON.PHOTOVOLTAIC_POWER_STATION") }),
						body: $translate.instant(response.data.description),
						showCloseButton: true,
					});
				}
			});
		}, function() {

		});
		$rootScope.modalInstance = modalInstance;
	};

	$scope.editPhotovoltaicPowerStation = function(photovoltaicpowerstation) {
		var modalInstance = $uibModal.open({
			windowClass: "animated fadeIn",
			templateUrl: 'views/settings/photovoltaicpowerstation/photovoltaicpowerstation.model.html',
			controller: 'ModalEditPhotovoltaicPowerStationCtrl',
			resolve: {
				params: function() {
					return {
						photovoltaicpowerstation: angular.copy(photovoltaicpowerstation),
						costcenters:angular.copy($scope.costcenters),
						contacts:angular.copy($scope.contacts)
					};
				}
			}
		});

		modalInstance.result.then(function(modifiedPhotovoltaicPowerStation) {
			modifiedPhotovoltaicPowerStation.cost_center_id=modifiedPhotovoltaicPowerStation.cost_center.id;
			modifiedPhotovoltaicPowerStation.contact_id=modifiedPhotovoltaicPowerStation.contact.id;

			let headers = { "User-UUID": $scope.cur_user.uuid, "Token": $scope.cur_user.token };
			PhotovoltaicPowerStationService.editPhotovoltaicPowerStation(modifiedPhotovoltaicPowerStation, headers, function(response) {
				if (angular.isDefined(response.status) && response.status === 200) {
					toaster.pop({
						type: "success",
						title: $translate.instant("TOASTER.SUCCESS_TITLE"),
						body: $translate.instant("TOASTER.SUCCESS_UPDATE_BODY", {template: $translate.instant("COMMON.PHOTOVOLTAIC_POWER_STATION")}),
						showCloseButton: true,
					});
					$scope.$emit('handleEmitPhotovoltaicPowerStationChanged');
				} else {
					toaster.pop({
						type: "error",
						title: $translate.instant("TOASTER.ERROR_UPDATE_BODY", {template: $translate.instant("COMMON.PHOTOVOLTAIC_POWER_STATION")}),
						body: $translate.instant(response.data.description),
						showCloseButton: true,
					});
				}
			});
		}, function() {
			//do nothing;
		});
		$rootScope.modalInstance = modalInstance;
	};

	$scope.deletePhotovoltaicPowerStation=function(photovoltaicpowerstation){
		SweetAlert.swal({
		        title: $translate.instant("SWEET.TITLE"),
		        text: $translate.instant("SWEET.TEXT"),
		        type: "warning",
		        showCancelButton: true,
		        confirmButtonColor: "#DD6B55",
		        confirmButtonText: $translate.instant("SWEET.CONFIRM_BUTTON_TEXT"),
		        cancelButtonText: $translate.instant("SWEET.CANCEL_BUTTON_TEXT"),
		        closeOnConfirm: true,
		        closeOnCancel: true },
		    function (isConfirm) {
		        if (isConfirm) {
					let headers = { "User-UUID": $scope.cur_user.uuid, "Token": $scope.cur_user.token };
		            PhotovoltaicPowerStationService.deletePhotovoltaicPowerStation(photovoltaicpowerstation, headers, function(response) {
		            	if (angular.isDefined(response.status) && response.status === 204) {
							toaster.pop({
								type: "success",
								title: $translate.instant("TOASTER.SUCCESS_TITLE"),
								body: $translate.instant("TOASTER.SUCCESS_DELETE_BODY", {template: $translate.instant("COMMON.PHOTOVOLTAIC_POWER_STATION")}),
								showCloseButton: true,
							});
							$scope.$emit('handleEmitPhotovoltaicPowerStationChanged');
						}else {
							toaster.pop({
								type: "error",
								title: $translate.instant("TOASTER.ERROR_DELETE_BODY", {template: $translate.instant("COMMON.PHOTOVOLTAIC_POWER_STATION")}),
								body: $translate.instant(response.data.description),
								showCloseButton: true,
							});
		            	}
		            });
		        }
		    });
	};
	$scope.getAllPhotovoltaicPowerStations();
	$scope.getAllCostCenters();
	$scope.getAllContacts();
	$scope.$on('handleBroadcastPhotovoltaicPowerStationChanged', function(event) {
  		$scope.getAllPhotovoltaicPowerStations();
	});
});

app.controller('ModalAddPhotovoltaicPowerStationCtrl', function($scope, $uibModalInstance,params) {

	$scope.operation = "SETTING.ADD_PHOTOVOLTAIC_POWER_STATION";
	$scope.costcenters=params.costcenters;
	$scope.contacts=params.contacts;
	$scope.ok = function() {
		$uibModalInstance.close($scope.photovoltaicpowerstation);
	};

    $scope.cancel = function() {
		$uibModalInstance.dismiss('cancel');
	};
});

app.controller('ModalEditPhotovoltaicPowerStationCtrl', function($scope, $uibModalInstance, params) {
	$scope.operation = "SETTING.EDIT_PHOTOVOLTAIC_POWER_STATION";
	$scope.photovoltaicpowerstation = params.photovoltaicpowerstation;
	$scope.costcenters=params.costcenters;
	$scope.contacts=params.contacts;
	$scope.ok = function() {
		$uibModalInstance.close($scope.photovoltaicpowerstation);
	};

	$scope.cancel = function() {
		$uibModalInstance.dismiss('cancel');
	};
});
