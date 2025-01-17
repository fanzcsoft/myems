import uuid
import falcon
import mysql.connector
import simplejson as json
from core.useractivity import user_logger, admin_control, access_control
import config


class EnergyStorageContainerCollection:
    @staticmethod
    def __init__():
        """"Initializes Class"""
        pass

    @staticmethod
    def on_options(req, resp):
        resp.status = falcon.HTTP_200

    @staticmethod
    def on_get(req, resp):
        access_control(req)
        cnx = mysql.connector.connect(**config.myems_system_db)
        cursor = cnx.cursor()

        query = (" SELECT id, name, uuid "
                 " FROM tbl_contacts ")
        cursor.execute(query)
        rows_contacts = cursor.fetchall()

        contact_dict = dict()
        if rows_contacts is not None and len(rows_contacts) > 0:
            for row in rows_contacts:
                contact_dict[row[0]] = {"id": row[0],
                                        "name": row[1],
                                        "uuid": row[2]}

        query = (" SELECT id, name, uuid "
                 " FROM tbl_cost_centers ")
        cursor.execute(query)
        rows_cost_centers = cursor.fetchall()

        cost_center_dict = dict()
        if rows_cost_centers is not None and len(rows_cost_centers) > 0:
            for row in rows_cost_centers:
                cost_center_dict[row[0]] = {"id": row[0],
                                            "name": row[1],
                                            "uuid": row[2]}
        query = (" SELECT id, name, uuid, "
                 "        capacity, contact_id, cost_center_id, svg, description "
                 " FROM tbl_energy_storage_containers "
                 " ORDER BY id ")
        cursor.execute(query)
        rows_spaces = cursor.fetchall()

        result = list()
        if rows_spaces is not None and len(rows_spaces) > 0:
            for row in rows_spaces:
                contact = contact_dict.get(row[4], None)
                cost_center = cost_center_dict.get(row[5], None)

                meta_result = {"id": row[0],
                               "name": row[1],
                               "uuid": row[2],
                               "capacity": row[3],
                               "contact": contact,
                               "cost_center": cost_center,
                               "svg": row[6],
                               "description": row[7],
                               "qrcode": 'energystoragecontainer:' + row[2]}
                result.append(meta_result)

        cursor.close()
        cnx.close()
        resp.text = json.dumps(result)

    @staticmethod
    @user_logger
    def on_post(req, resp):
        """Handles POST requests"""
        admin_control(req)
        try:
            raw_json = req.stream.read().decode('utf-8')
        except Exception as ex:
            raise falcon.HTTPError(status=falcon.HTTP_400,
                                   title='API.BAD_REQUEST',
                                   description='API.FAILED_TO_READ_REQUEST_STREAM')

        new_values = json.loads(raw_json)

        if 'name' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['name'], str) or \
                len(str.strip(new_values['data']['name'])) == 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_ENERGY_STORAGE_CONTAINER_NAME')
        name = str.strip(new_values['data']['name'])

        if 'capacity' not in new_values['data'].keys() or \
                not (isinstance(new_values['data']['capacity'], float) or
                     isinstance(new_values['data']['capacity'], int)) or \
                new_values['data']['capacity'] <= 0.0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_CAPACITY_VALUE')
        capacity = new_values['data']['capacity']

        if 'contact_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['contact_id'], int) or \
                new_values['data']['contact_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_CONTACT_ID')
        contact_id = new_values['data']['contact_id']

        if 'cost_center_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['cost_center_id'], int) or \
                new_values['data']['cost_center_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_COST_CENTER_ID')
        cost_center_id = new_values['data']['cost_center_id']

        if 'svg' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['svg'], str) or \
                len(str.strip(new_values['data']['svg'])) == 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_SVG')
        svg = str.strip(new_values['data']['svg'])

        if 'description' in new_values['data'].keys() and \
                new_values['data']['description'] is not None and \
                len(str(new_values['data']['description'])) > 0:
            description = str.strip(new_values['data']['description'])
        else:
            description = None

        cnx = mysql.connector.connect(**config.myems_system_db)
        cursor = cnx.cursor()

        cursor.execute(" SELECT name "
                       " FROM tbl_energy_storage_containers "
                       " WHERE name = %s ", (name,))
        if cursor.fetchone() is not None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.ENERGY_STORAGE_CONTAINER_NAME_IS_ALREADY_IN_USE')

        cursor.execute(" SELECT name "
                       " FROM tbl_contacts "
                       " WHERE id = %s ",
                       (new_values['data']['contact_id'],))
        row = cursor.fetchone()
        if row is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.CONTACT_NOT_FOUND')

        cursor.execute(" SELECT name "
                       " FROM tbl_cost_centers "
                       " WHERE id = %s ",
                       (new_values['data']['cost_center_id'],))
        row = cursor.fetchone()
        if row is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.COST_CENTER_NOT_FOUND')

        add_values = (" INSERT INTO tbl_energy_storage_containers "
                      "    (name, uuid, capacity, contact_id, cost_center_id, svg, description) "
                      " VALUES (%s, %s, %s, %s, %s, %s, %s) ")
        cursor.execute(add_values, (name,
                                    str(uuid.uuid4()),
                                    capacity,
                                    contact_id,
                                    cost_center_id,
                                    svg,
                                    description))
        new_id = cursor.lastrowid
        cnx.commit()
        cursor.close()
        cnx.close()

        resp.status = falcon.HTTP_201
        resp.location = '/energystoragecontainers/' + str(new_id)


class EnergyStorageContainerItem:
    @staticmethod
    def __init__():
        """"Initializes Class"""
        pass

    @staticmethod
    def on_options(req, resp, id_):
        resp.status = falcon.HTTP_200

    @staticmethod
    def on_get(req, resp, id_):
        access_control(req)
        if not id_.isdigit() or int(id_) <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_ENERGY_STORAGE_CONTAINER_ID')

        cnx = mysql.connector.connect(**config.myems_system_db)
        cursor = cnx.cursor()

        query = (" SELECT id, name, uuid "
                 " FROM tbl_contacts ")
        cursor.execute(query)
        rows_contacts = cursor.fetchall()

        contact_dict = dict()
        if rows_contacts is not None and len(rows_contacts) > 0:
            for row in rows_contacts:
                contact_dict[row[0]] = {"id": row[0],
                                        "name": row[1],
                                        "uuid": row[2]}

        query = (" SELECT id, name, uuid "
                 " FROM tbl_cost_centers ")
        cursor.execute(query)
        rows_cost_centers = cursor.fetchall()

        cost_center_dict = dict()
        if rows_cost_centers is not None and len(rows_cost_centers) > 0:
            for row in rows_cost_centers:
                cost_center_dict[row[0]] = {"id": row[0],
                                            "name": row[1],
                                            "uuid": row[2]}

        query = (" SELECT id, name, uuid, "
                 "        capacity, contact_id, cost_center_id, svg, description "
                 " FROM tbl_energy_storage_containers "
                 " WHERE id = %s ")
        cursor.execute(query, (id_,))
        row = cursor.fetchone()
        cursor.close()
        cnx.close()

        if row is None:
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.ENERGY_STORAGE_CONTAINER_NOT_FOUND')
        else:
            meta_result = {"id": row[0],
                           "name": row[1],
                           "uuid": row[2],
                           "capacity": row[3],
                           "contact": contact_dict.get(row[4], None),
                           "cost_center": cost_center_dict.get(row[5], None),
                           "svg": row[6],
                           "description": row[7],
                           "qrcode": 'energystoragecontainer:' + row[2]}

        resp.text = json.dumps(meta_result)

    @staticmethod
    @user_logger
    def on_delete(req, resp, id_):
        admin_control(req)
        if not id_.isdigit() or int(id_) <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_ENERGY_STORAGE_CONTAINER_ID')

        cnx = mysql.connector.connect(**config.myems_system_db)
        cursor = cnx.cursor()

        cursor.execute(" SELECT name "
                       " FROM tbl_energy_storage_containers "
                       " WHERE id = %s ", (id_,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.ENERGY_STORAGE_CONTAINER_NOT_FOUND')

        cursor.execute(" DELETE FROM tbl_energy_storage_containers_sensors "
                       " WHERE energy_storage_container_id = %s ", (id_, ))

        cursor.execute(" DELETE FROM tbl_energy_storage_containers_batteries "
                       " WHERE energy_storage_container_id = %s ", (id_, ))

        cursor.execute(" DELETE FROM tbl_energy_storage_containers_grids "
                       " WHERE energy_storage_container_id = %s ", (id_, ))

        cursor.execute(" DELETE FROM tbl_energy_storage_containers_loads "
                       " WHERE energy_storage_container_id = %s ", (id_, ))

        cursor.execute(" DELETE FROM tbl_energy_storage_containers_power_conversion_systems "
                       " WHERE energy_storage_container_id = %s ", (id_, ))

        cursor.execute(" DELETE FROM tbl_energy_storage_containers_users "
                       " WHERE energy_storage_container_id = %s ", (id_, ))

        cursor.execute(" DELETE FROM tbl_energy_storage_containers "
                       " WHERE id = %s ", (id_,))
        cnx.commit()

        cursor.close()
        cnx.close()

        resp.status = falcon.HTTP_204

    @staticmethod
    @user_logger
    def on_put(req, resp, id_):
        """Handles PUT requests"""
        admin_control(req)
        try:
            raw_json = req.stream.read().decode('utf-8')
        except Exception as ex:
            raise falcon.HTTPError(status=falcon.HTTP_400,
                                   title='API.BAD_REQUEST',
                                   description='API.FAILED_TO_READ_REQUEST_STREAM')

        if not id_.isdigit() or int(id_) <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_ENERGY_STORAGE_CONTAINER_ID')

        new_values = json.loads(raw_json)

        if 'name' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['name'], str) or \
                len(str.strip(new_values['data']['name'])) == 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_ENERGY_STORAGE_CONTAINER_NAME')
        name = str.strip(new_values['data']['name'])

        if 'capacity' not in new_values['data'].keys() or \
                not (isinstance(new_values['data']['capacity'], float) or
                     isinstance(new_values['data']['capacity'], int)) or \
                new_values['data']['capacity'] <= 0.0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_CAPACITY_VALUE')
        capacity = new_values['data']['capacity']

        if 'contact_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['contact_id'], int) or \
                new_values['data']['contact_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_CONTACT_ID')
        contact_id = new_values['data']['contact_id']

        if 'cost_center_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['cost_center_id'], int) or \
                new_values['data']['cost_center_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_COST_CENTER_ID')
        cost_center_id = new_values['data']['cost_center_id']

        if 'svg' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['svg'], str) or \
                len(str.strip(new_values['data']['svg'])) == 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_SVG')
        svg = str.strip(new_values['data']['svg'])

        if 'description' in new_values['data'].keys() and \
                new_values['data']['description'] is not None and \
                len(str(new_values['data']['description'])) > 0:
            description = str.strip(new_values['data']['description'])
        else:
            description = None

        cnx = mysql.connector.connect(**config.myems_system_db)
        cursor = cnx.cursor()

        cursor.execute(" SELECT name "
                       " FROM tbl_energy_storage_containers "
                       " WHERE id = %s ", (id_,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.ENERGY_STORAGE_CONTAINER_NOT_FOUND')

        cursor.execute(" SELECT name "
                       " FROM tbl_energy_storage_containers "
                       " WHERE name = %s AND id != %s ", (name, id_))
        if cursor.fetchone() is not None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.ENERGY_STORAGE_CONTAINER_NAME_IS_ALREADY_IN_USE')

        cursor.execute(" SELECT name "
                       " FROM tbl_contacts "
                       " WHERE id = %s ",
                       (new_values['data']['contact_id'],))
        row = cursor.fetchone()
        if row is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.CONTACT_NOT_FOUND')

        cursor.execute(" SELECT name "
                       " FROM tbl_cost_centers "
                       " WHERE id = %s ",
                       (new_values['data']['cost_center_id'],))
        row = cursor.fetchone()
        if row is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.COST_CENTER_NOT_FOUND')

        update_row = (" UPDATE tbl_energy_storage_containers "
                      " SET name = %s, capacity = %s, contact_id = %s, cost_center_id = %s, "
                      "     svg = %s, description = %s "
                      " WHERE id = %s ")
        cursor.execute(update_row, (name,
                                    capacity,
                                    contact_id,
                                    cost_center_id,
                                    svg,
                                    description,
                                    id_))
        cnx.commit()

        cursor.close()
        cnx.close()

        resp.status = falcon.HTTP_200


class EnergyStorageContainerSensorCollection:
    @staticmethod
    def __init__():
        """Initializes Class"""
        pass

    @staticmethod
    def on_options(req, resp, id_):
        resp.status = falcon.HTTP_200

    @staticmethod
    def on_get(req, resp, id_):
        access_control(req)
        if not id_.isdigit() or int(id_) <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_ENERGY_STORAGE_CONTAINER_ID')

        cnx = mysql.connector.connect(**config.myems_system_db)
        cursor = cnx.cursor()

        cursor.execute(" SELECT name "
                       " FROM tbl_energy_storage_containers "
                       " WHERE id = %s ", (id_,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.ENERGY_STORAGE_CONTAINER_NOT_FOUND')

        query = (" SELECT s.id, s.name, s.uuid "
                 " FROM tbl_energy_storage_containers e, "
                 "      tbl_energy_storage_containers_sensors es, tbl_sensors s "
                 " WHERE es.energy_storage_container_id = e.id AND s.id = es.sensor_id AND e.id = %s "
                 " ORDER BY s.id ")
        cursor.execute(query, (id_,))
        rows = cursor.fetchall()

        result = list()
        if rows is not None and len(rows) > 0:
            for row in rows:
                meta_result = {"id": row[0], "name": row[1], "uuid": row[2]}
                result.append(meta_result)

        resp.text = json.dumps(result)

    @staticmethod
    @user_logger
    def on_post(req, resp, id_):
        """Handles POST requests"""
        admin_control(req)
        try:
            raw_json = req.stream.read().decode('utf-8')
        except Exception as ex:
            raise falcon.HTTPError(status=falcon.HTTP_400,
                                   title='API.BAD_REQUEST',
                                   description='API.FAILED_TO_READ_REQUEST_STREAM')

        if not id_.isdigit() or int(id_) <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_ENERGY_STORAGE_CONTAINER_ID')

        new_values = json.loads(raw_json)

        if 'sensor_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['sensor_id'], int) or \
                new_values['data']['sensor_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_SENSOR_ID')
        sensor_id = new_values['data']['sensor_id']

        cnx = mysql.connector.connect(**config.myems_system_db)
        cursor = cnx.cursor()

        cursor.execute(" SELECT name "
                       " FROM tbl_energy_storage_containers "
                       " WHERE id = %s ", (id_,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.ENERGY_STORAGE_CONTAINER_NOT_FOUND')

        cursor.execute(" SELECT name "
                       " FROM tbl_sensors "
                       " WHERE id = %s ", (sensor_id,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.SENSOR_NOT_FOUND')

        query = (" SELECT id " 
                 " FROM tbl_energy_storage_containers_sensors "
                 " WHERE energy_storage_container_id = %s AND sensor_id = %s")
        cursor.execute(query, (id_, sensor_id,))
        if cursor.fetchone() is not None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.ERROR',
                                   description='API.ENERGY_STORAGE_CONTAINER_SENSOR_RELATION_EXISTS')

        add_row = (" INSERT INTO tbl_energy_storage_containers_sensors "
                   "        (energy_storage_container_id, sensor_id) "
                   " VALUES (%s, %s) ")
        cursor.execute(add_row, (id_, sensor_id,))
        cnx.commit()
        cursor.close()
        cnx.close()

        resp.status = falcon.HTTP_201
        resp.location = '/energystoragecontainers/' + str(id_) + '/sensors/' + str(sensor_id)


class EnergyStorageContainerSensorItem:
    @staticmethod
    def __init__():
        """Initializes Class"""
        pass

    @staticmethod
    def on_options(req, resp, id_, sid):
        resp.status = falcon.HTTP_200

    @staticmethod
    @user_logger
    def on_delete(req, resp, id_, sid):
        admin_control(req)
        if not id_.isdigit() or int(id_) <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_ENERGY_STORAGE_CONTAINER_ID')

        if not sid.isdigit() or int(sid) <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_SENSOR_ID')

        cnx = mysql.connector.connect(**config.myems_system_db)
        cursor = cnx.cursor()

        cursor.execute(" SELECT name "
                       " FROM tbl_energy_storage_containers "
                       " WHERE id = %s ", (id_,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.ENERGY_STORAGE_CONTAINER_NOT_FOUND')

        cursor.execute(" SELECT name "
                       " FROM tbl_sensors "
                       " WHERE id = %s ", (sid,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.SENSOR_NOT_FOUND')

        cursor.execute(" SELECT id "
                       " FROM tbl_energy_storage_containers_sensors "
                       " WHERE energy_storage_container_id = %s AND sensor_id = %s ", (id_, sid))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.ENERGY_STORAGE_CONTAINER_SENSOR_RELATION_NOT_FOUND')

        cursor.execute(" DELETE FROM tbl_energy_storage_containers_sensors "
                       " WHERE energy_storage_container_id = %s AND sensor_id = %s ", (id_, sid))
        cnx.commit()

        cursor.close()
        cnx.close()

        resp.status = falcon.HTTP_204


class EnergyStorageContainerBatteryCollection:
    @staticmethod
    def __init__():
        """Initializes Class"""
        pass

    @staticmethod
    def on_options(req, resp, id_):
        resp.status = falcon.HTTP_200

    @staticmethod
    def on_get(req, resp, id_):
        access_control(req)
        if not id_.isdigit() or int(id_) <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_ENERGY_STORAGE_CONTAINER_ID')

        cnx = mysql.connector.connect(**config.myems_system_db)
        cursor = cnx.cursor()

        cursor.execute(" SELECT name "
                       " FROM tbl_energy_storage_containers "
                       " WHERE id = %s ", (id_,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.ENERGY_STORAGE_CONTAINER_NOT_FOUND')

        # query meter dict
        query = (" SELECT id, name, uuid "
                 " FROM tbl_meters ")
        cursor.execute(query)
        rows_meters = cursor.fetchall()

        meter_dict = dict()
        if rows_meters is not None and len(rows_meters) > 0:
            for row in rows_meters:
                meter_dict[row[0]] = {"id": row[0],
                                      "name": row[1],
                                      "uuid": row[2]}
        # query point dict
        query = (" SELECT id, name "
                 " FROM tbl_points ")
        cursor.execute(query)
        rows_points = cursor.fetchall()

        point_dict = dict()
        if rows_points is not None and len(rows_points) > 0:
            for row in rows_points:
                point_dict[row[0]] = {"id": row[0],
                                      "name": row[1]}

        query = (" SELECT id, name, uuid, "
                 "        battery_state_point_id, soc_point_id, power_point_id, "
                 "        charge_meter_id, discharge_meter_id, capacity, nominal_voltage "
                 " FROM tbl_energy_storage_containers_batteries "
                 " WHERE energy_storage_container_id = %s "
                 " ORDER BY name ")
        cursor.execute(query, (id_,))
        rows = cursor.fetchall()

        result = list()
        if rows is not None and len(rows) > 0:
            for row in rows:
                battery_state_point = point_dict.get(row[3])
                soc_point = point_dict.get(row[4])
                power_point = point_dict.get(row[5])
                charge_meter = meter_dict.get(row[6])
                discharge_meter = meter_dict.get(row[7])
                meta_result = {"id": row[0],
                               "name": row[1],
                               "uuid": row[2],
                               "battery_state_point": battery_state_point,
                               "soc_point": soc_point,
                               "power_point": power_point,
                               "charge_meter": charge_meter,
                               "discharge_meter": discharge_meter,
                               "capacity": row[8],
                               "nominal_voltage": row[9]}
                result.append(meta_result)

        resp.text = json.dumps(result)

    @staticmethod
    @user_logger
    def on_post(req, resp, id_):
        """Handles POST requests"""
        admin_control(req)
        try:
            raw_json = req.stream.read().decode('utf-8')
        except Exception as ex:
            raise falcon.HTTPError(status=falcon.HTTP_400,
                                   title='API.BAD_REQUEST',
                                   description='API.FAILED_TO_READ_REQUEST_STREAM')

        if not id_.isdigit() or int(id_) <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_ENERGY_STORAGE_CONTAINER_ID')

        cnx = mysql.connector.connect(**config.myems_system_db)
        cursor = cnx.cursor()

        cursor.execute(" SELECT name "
                       " FROM tbl_energy_storage_containers "
                       " WHERE id = %s ", (id_,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.ENERGY_STORAGE_CONTAINER_NOT_FOUND')

        new_values = json.loads(raw_json)

        if 'name' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['name'], str) or \
                len(str.strip(new_values['data']['name'])) == 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_ENERGY_STORAGE_CONTAINER_BATTERY_NAME')
        name = str.strip(new_values['data']['name'])

        if 'battery_state_point_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['battery_state_point_id'], int) or \
                new_values['data']['battery_state_point_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_BATTERY_STATE_POINT_ID')
        battery_state_point_id = new_values['data']['battery_state_point_id']

        if 'soc_point_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['soc_point_id'], int) or \
                new_values['data']['soc_point_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_SOC_POINT_ID')
        soc_point_id = new_values['data']['soc_point_id']

        if 'power_point_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['power_point_id'], int) or \
                new_values['data']['power_point_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_POWER_POINT_ID')
        power_point_id = new_values['data']['power_point_id']

        if 'charge_meter_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['charge_meter_id'], int) or \
                new_values['data']['charge_meter_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_CHARGE_METER_ID')
        charge_meter_id = new_values['data']['charge_meter_id']

        if 'discharge_meter_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['discharge_meter_id'], int) or \
                new_values['data']['discharge_meter_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_DISCHARGE_METER_ID')
        discharge_meter_id = new_values['data']['discharge_meter_id']

        if 'capacity' not in new_values['data'].keys() or \
                not (isinstance(new_values['data']['capacity'], float) or
                     isinstance(new_values['data']['capacity'], int)):
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_CAPACITY')
        capacity = float(new_values['data']['capacity'])

        if 'nominal_voltage' not in new_values['data'].keys() or \
                not (isinstance(new_values['data']['nominal_voltage'], float) or
                     isinstance(new_values['data']['nominal_voltage'], int)):
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_NOMINAL_VOLTAGE')
        nominal_voltage = float(new_values['data']['nominal_voltage'])

        cnx = mysql.connector.connect(**config.myems_system_db)
        cursor = cnx.cursor()

        cursor.execute(" SELECT name "
                       " FROM tbl_energy_storage_containers_batteries "
                       " WHERE energy_storage_container_id = %s AND name = %s ",
                       (id_, name,))
        if cursor.fetchone() is not None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.ENERGY_STORAGE_CONTAINER_BATTERY_NAME_IS_ALREADY_IN_USE')

        cursor.execute(" SELECT name "
                       " FROM tbl_points "
                       " WHERE id = %s ",
                       (battery_state_point_id,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.BATTERY_STATE_POINT_NOT_FOUND')

        cursor.execute(" SELECT name "
                       " FROM tbl_points "
                       " WHERE id = %s ",
                       (soc_point_id,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.SOC_POINT_NOT_FOUND')

        cursor.execute(" SELECT name "
                       " FROM tbl_points "
                       " WHERE id = %s ",
                       (power_point_id,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.POWER_POINT_NOT_FOUND')

        cursor.execute(" SELECT name "
                       " FROM tbl_meters "
                       " WHERE id = %s ",
                       (charge_meter_id,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.CHARGE_METER_NOT_FOUND')

        cursor.execute(" SELECT name "
                       " FROM tbl_meters "
                       " WHERE id = %s ",
                       (discharge_meter_id,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.DISCHARGE_METER_NOT_FOUND')

        add_values = (" INSERT INTO tbl_energy_storage_containers_batteries "
                      "    (name, uuid, energy_storage_container_id, "
                      "     battery_state_point_id, soc_point_id, power_point_id, "
                      "     charge_meter_id, discharge_meter_id, capacity, nominal_voltage) "
                      " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ")
        cursor.execute(add_values, (name,
                                    str(uuid.uuid4()),
                                    id_,
                                    battery_state_point_id,
                                    soc_point_id,
                                    power_point_id,
                                    charge_meter_id,
                                    discharge_meter_id,
                                    capacity,
                                    nominal_voltage))
        new_id = cursor.lastrowid
        cnx.commit()
        cursor.close()
        cnx.close()

        resp.status = falcon.HTTP_201
        resp.location = '/energystoragecontainers/' + str(id_) + '/batteries/' + str(new_id)


class EnergyStorageContainerBatteryItem:
    @staticmethod
    def __init__():
        """Initializes Class"""
        pass

    @staticmethod
    def on_options(req, resp, id_, bid):
        resp.status = falcon.HTTP_200

    @staticmethod
    def on_get(req, resp, id_, bid):
        access_control(req)
        if not id_.isdigit() or int(id_) <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_ENERGY_STORAGE_CONTAINER_ID')
        if not bid.isdigit() or int(bid) <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_ENERGY_STORAGE_CONTAINER_BATTERY_ID')

        cnx = mysql.connector.connect(**config.myems_system_db)
        cursor = cnx.cursor()

        cursor.execute(" SELECT name "
                       " FROM tbl_energy_storage_containers "
                       " WHERE id = %s ", (id_,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.ENERGY_STORAGE_CONTAINER_NOT_FOUND')

        # query energy storage power station dict
        query = (" SELECT id, name, uuid "
                 " FROM tbl_energy_storage_containers ")
        cursor.execute(query)
        rows_energystoragecontainers = cursor.fetchall()

        energy_storage_container_dict = dict()
        if rows_energystoragecontainers is not None and len(rows_energystoragecontainers) > 0:
            for row in rows_energystoragecontainers:
                energy_storage_container_dict[row[0]] = {"id": row[0],
                                                         "name": row[1],
                                                         "uuid": row[2]}
        # query meter dict
        query = (" SELECT id, name, uuid "
                 " FROM tbl_meters ")
        cursor.execute(query)
        rows_meters = cursor.fetchall()

        meter_dict = dict()
        if rows_meters is not None and len(rows_meters) > 0:
            for row in rows_meters:
                meter_dict[row[0]] = {"id": row[0],
                                      "name": row[1],
                                      "uuid": row[2]}
        # query point dict
        query = (" SELECT id, name "
                 " FROM tbl_points ")
        cursor.execute(query)
        rows_points = cursor.fetchall()

        point_dict = dict()
        if rows_points is not None and len(rows_points) > 0:
            for row in rows_points:
                point_dict[row[0]] = {"id": row[0],
                                      "name": row[1]}

        query = (" SELECT id, name, uuid, energy_storage_container_id, "
                 "       battery_state_point_id, soc_point_id, power_point_id, "
                 "       charge_meter_id, discharge_meter_id, capacity, nominal_voltage "
                 " FROM tbl_energy_storage_containers_batteries "
                 " WHERE id = %s ")
        cursor.execute(query, (bid,))
        row = cursor.fetchone()
        cursor.close()
        cnx.close()

        if row is None:
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.ENERGY_STORAGE_CONTAINER_BATTERY_NOT_FOUND')
        else:
            energy_storage_container = energy_storage_container_dict.get(row[3])
            battery_state_point = point_dict.get(row[4])
            soc_point = point_dict.get(row[5])
            power_point = point_dict.get(row[6])
            charge_meter = meter_dict.get(row[7])
            discharge_meter = meter_dict.get(row[8])
            meta_result = {"id": row[0],
                           "name": row[1],
                           "uuid": row[2],
                           "energy_storage_container": energy_storage_container,
                           "battery_state_point": battery_state_point,
                           "soc_point": soc_point,
                           "power_point": power_point,
                           "charge_meter": charge_meter,
                           "discharge_meter": discharge_meter,
                           "capacity": row[9],
                           "nominal_voltage": row[10]}

        resp.text = json.dumps(meta_result)

    @staticmethod
    @user_logger
    def on_delete(req, resp, id_, bid):
        admin_control(req)
        if not id_.isdigit() or int(id_) <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_ENERGY_STORAGE_CONTAINER_ID')
        if not bid.isdigit() or int(bid) <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_ENERGY_STORAGE_CONTAINER_BATTERY_ID')

        cnx = mysql.connector.connect(**config.myems_system_db)
        cursor = cnx.cursor()

        cursor.execute(" SELECT name "
                       " FROM tbl_energy_storage_containers "
                       " WHERE id = %s ", (id_,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.ENERGY_STORAGE_CONTAINER_NOT_FOUND')

        cursor.execute(" SELECT name "
                       " FROM tbl_energy_storage_containers_batteries "
                       " WHERE id = %s ", (bid,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.ENERGY_STORAGE_CONTAINER_BATTERY_NOT_FOUND')

        cursor.execute(" DELETE FROM tbl_energy_storage_containers_batteries "
                       " WHERE id = %s ", (bid,))
        cnx.commit()

        cursor.close()
        cnx.close()

        resp.status = falcon.HTTP_204

    @staticmethod
    @user_logger
    def on_put(req, resp, id_, bid):
        """Handles PUT requests"""
        admin_control(req)
        try:
            raw_json = req.stream.read().decode('utf-8')
        except Exception as ex:
            raise falcon.HTTPError(status=falcon.HTTP_400,
                                   title='API.BAD_REQUEST',
                                   description='API.FAILED_TO_READ_REQUEST_STREAM')
        if not id_.isdigit() or int(id_) <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_ENERGY_STORAGE_CONTAINER_ID')
        if not bid.isdigit() or int(bid) <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_ENERGY_STORAGE_CONTAINER_BATTERY_ID')

        new_values = json.loads(raw_json)

        if 'name' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['name'], str) or \
                len(str.strip(new_values['data']['name'])) == 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_ENERGY_STORAGE_CONTAINER_BATTERY_NAME')
        name = str.strip(new_values['data']['name'])

        if 'battery_state_point_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['battery_state_point_id'], int) or \
                new_values['data']['battery_state_point_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_BATTERY_STATE_POINT_ID')
        battery_state_point_id = new_values['data']['battery_state_point_id']

        if 'soc_point_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['soc_point_id'], int) or \
                new_values['data']['soc_point_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_SOC_POINT_ID')
        soc_point_id = new_values['data']['soc_point_id']

        if 'power_point_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['power_point_id'], int) or \
                new_values['data']['power_point_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_POWER_POINT_ID')
        power_point_id = new_values['data']['power_point_id']

        if 'charge_meter_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['charge_meter_id'], int) or \
                new_values['data']['charge_meter_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_CHARGE_METER_ID')
        charge_meter_id = new_values['data']['charge_meter_id']

        if 'discharge_meter_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['discharge_meter_id'], int) or \
                new_values['data']['discharge_meter_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_DISCHARGE_METER_ID')
        discharge_meter_id = new_values['data']['discharge_meter_id']

        if 'capacity' not in new_values['data'].keys() or \
                not (isinstance(new_values['data']['capacity'], float) or
                     isinstance(new_values['data']['capacity'], int)):
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_CAPACITY')
        capacity = float(new_values['data']['capacity'])

        if 'nominal_voltage' not in new_values['data'].keys() or \
                not (isinstance(new_values['data']['nominal_voltage'], float) or
                     isinstance(new_values['data']['nominal_voltage'], int)):
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_NOMINAL_VOLTAGE')
        nominal_voltage = float(new_values['data']['nominal_voltage'])

        cnx = mysql.connector.connect(**config.myems_system_db)
        cursor = cnx.cursor()

        cursor.execute(" SELECT name "
                       " FROM tbl_energy_storage_containers "
                       " WHERE id = %s ",
                       (id_,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.ENERGY_STORAGE_CONTAINER_NOT_FOUND')

        cursor.execute(" SELECT name "
                       " FROM tbl_energy_storage_containers_batteries "
                       " WHERE id = %s ", (bid,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.ENERGY_STORAGE_CONTAINER_BATTERY_NOT_FOUND')

        cursor.execute(" SELECT name "
                       " FROM tbl_energy_storage_containers_batteries "
                       " WHERE energy_storage_container_id = %s AND name = %s AND id != %s ",
                       (id_, name, bid))
        if cursor.fetchone() is not None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.ENERGY_STORAGE_CONTAINER_BATTERY_NAME_IS_ALREADY_IN_USE')

        cursor.execute(" SELECT name "
                       " FROM tbl_points "
                       " WHERE id = %s ",
                       (battery_state_point_id,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.BATTERY_STATE_POINT_NOT_FOUND')

        cursor.execute(" SELECT name "
                       " FROM tbl_points "
                       " WHERE id = %s ",
                       (soc_point_id,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.SOC_POINT_NOT_FOUND')

        cursor.execute(" SELECT name "
                       " FROM tbl_points "
                       " WHERE id = %s ",
                       (power_point_id,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.POWER_POINT_NOT_FOUND')

        cursor.execute(" SELECT name "
                       " FROM tbl_meters "
                       " WHERE id = %s ",
                       (charge_meter_id,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.CHARGE_METER_NOT_FOUND')

        cursor.execute(" SELECT name "
                       " FROM tbl_meters "
                       " WHERE id = %s ",
                       (discharge_meter_id,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.DISCHARGE_METER_NOT_FOUND')

        update_row = (" UPDATE tbl_energy_storage_containers_batteries "
                      " SET name = %s, energy_storage_container_id = %s, "
                      "     battery_state_point_id = %s, soc_point_id = %s, power_point_id = %s, "
                      "     charge_meter_id = %s, discharge_meter_id = %s, capacity = %s, nominal_voltage = %s "
                      " WHERE id = %s ")
        cursor.execute(update_row, (name,
                                    id_,
                                    battery_state_point_id,
                                    soc_point_id,
                                    power_point_id,
                                    charge_meter_id,
                                    discharge_meter_id,
                                    capacity,
                                    nominal_voltage,
                                    bid))
        cnx.commit()

        cursor.close()
        cnx.close()

        resp.status = falcon.HTTP_200


class EnergyStorageContainerCommandCollection:
    @staticmethod
    def __init__():
        """Initializes Class"""
        pass

    @staticmethod
    def on_options(req, resp, id_):
        resp.status = falcon.HTTP_200

    @staticmethod
    def on_get(req, resp, id_):
        access_control(req)
        if not id_.isdigit() or int(id_) <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_ENERGY_STORAGE_CONTAINER_ID')

        cnx = mysql.connector.connect(**config.myems_system_db)
        cursor = cnx.cursor()

        cursor.execute(" SELECT name "
                       " FROM tbl_energy_storage_containers "
                       " WHERE id = %s ", (id_,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.ENERGY_STORAGE_CONTAINER_NOT_FOUND')

        query = (" SELECT c.id, c.name, c.uuid "
                 " FROM tbl_energy_storage_containers m, "
                 "      tbl_energy_storage_containers_commands mc, "
                 "      tbl_commands c "
                 " WHERE mc.energy_storage_container_id = m.id AND c.id = mc.command_id AND m.id = %s "
                 " ORDER BY c.id ")
        cursor.execute(query, (id_,))
        rows = cursor.fetchall()

        result = list()
        if rows is not None and len(rows) > 0:
            for row in rows:
                meta_result = {"id": row[0], "name": row[1], "uuid": row[2]}
                result.append(meta_result)

        resp.text = json.dumps(result)


class EnergyStorageContainerGridCollection:
    @staticmethod
    def __init__():
        """Initializes Class"""
        pass

    @staticmethod
    def on_options(req, resp, id_):
        resp.status = falcon.HTTP_200

    @staticmethod
    def on_get(req, resp, id_):
        access_control(req)
        if not id_.isdigit() or int(id_) <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_ENERGY_STORAGE_CONTAINER_ID')

        cnx = mysql.connector.connect(**config.myems_system_db)
        cursor = cnx.cursor()

        cursor.execute(" SELECT name "
                       " FROM tbl_energy_storage_containers "
                       " WHERE id = %s ", (id_,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.ENERGY_STORAGE_CONTAINER_NOT_FOUND')

        # query meter dict
        query = (" SELECT id, name, uuid "
                 " FROM tbl_meters ")
        cursor.execute(query)
        rows_meters = cursor.fetchall()

        meter_dict = dict()
        if rows_meters is not None and len(rows_meters) > 0:
            for row in rows_meters:
                meter_dict[row[0]] = {"id": row[0],
                                      "name": row[1],
                                      "uuid": row[2]}
        # query point dict
        query = (" SELECT id, name "
                 " FROM tbl_points ")
        cursor.execute(query)
        rows_points = cursor.fetchall()

        point_dict = dict()
        if rows_points is not None and len(rows_points) > 0:
            for row in rows_points:
                point_dict[row[0]] = {"id": row[0],
                                      "name": row[1]}

        query = (" SELECT id, name, uuid, "
                 "        power_point_id, buy_meter_id, sell_meter_id, capacity "
                 " FROM tbl_energy_storage_containers_grids "
                 " WHERE energy_storage_container_id = %s "
                 " ORDER BY name ")
        cursor.execute(query, (id_,))
        rows = cursor.fetchall()

        result = list()
        if rows is not None and len(rows) > 0:
            for row in rows:
                power_point = point_dict.get(row[3])
                buy_meter = meter_dict.get(row[4])
                sell_meter = meter_dict.get(row[5])
                meta_result = {"id": row[0],
                               "name": row[1],
                               "uuid": row[2],
                               "power_point": power_point,
                               "buy_meter": buy_meter,
                               "sell_meter": sell_meter,
                               "capacity": row[6]}
                result.append(meta_result)

        resp.text = json.dumps(result)

    @staticmethod
    @user_logger
    def on_post(req, resp, id_):
        """Handles POST requests"""
        admin_control(req)
        try:
            raw_json = req.stream.read().decode('utf-8')
        except Exception as ex:
            raise falcon.HTTPError(status=falcon.HTTP_400,
                                   title='API.BAD_REQUEST',
                                   description='API.FAILED_TO_READ_REQUEST_STREAM')
        if not id_.isdigit() or int(id_) <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_ENERGY_STORAGE_CONTAINER_ID')

        cnx = mysql.connector.connect(**config.myems_system_db)
        cursor = cnx.cursor()

        cursor.execute(" SELECT name "
                       " FROM tbl_energy_storage_containers "
                       " WHERE id = %s ", (id_,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.ENERGY_STORAGE_CONTAINER_NOT_FOUND')

        new_values = json.loads(raw_json)

        if 'name' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['name'], str) or \
                len(str.strip(new_values['data']['name'])) == 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_ENERGY_STORAGE_CONTAINER_GRID_NAME')
        name = str.strip(new_values['data']['name'])

        if 'power_point_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['power_point_id'], int) or \
                new_values['data']['power_point_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_POWER_POINT_ID')
        power_point_id = new_values['data']['power_point_id']

        if 'buy_meter_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['buy_meter_id'], int) or \
                new_values['data']['buy_meter_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_BUY_METER_ID')
        buy_meter_id = new_values['data']['buy_meter_id']

        if 'sell_meter_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['sell_meter_id'], int) or \
                new_values['data']['sell_meter_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_SELL_METER_ID')
        sell_meter_id = new_values['data']['sell_meter_id']

        if 'capacity' not in new_values['data'].keys() or \
                not (isinstance(new_values['data']['capacity'], float) or
                     isinstance(new_values['data']['capacity'], int)):
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_CAPACITY')
        capacity = float(new_values['data']['capacity'])

        cnx = mysql.connector.connect(**config.myems_system_db)
        cursor = cnx.cursor()

        cursor.execute(" SELECT name "
                       " FROM tbl_energy_storage_containers "
                       " WHERE id = %s ",
                       (id_,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.ENERGY_STORAGE_CONTAINER_NOT_FOUND')

        cursor.execute(" SELECT name "
                       " FROM tbl_energy_storage_containers_grids "
                       " WHERE energy_storage_container_id = %s AND name = %s ",
                       (id_, name,))
        if cursor.fetchone() is not None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.ENERGY_STORAGE_CONTAINER_GRID_NAME_IS_ALREADY_IN_USE')

        cursor.execute(" SELECT name "
                       " FROM tbl_points "
                       " WHERE id = %s ",
                       (power_point_id,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.POWER_POINT_NOT_FOUND')

        cursor.execute(" SELECT name "
                       " FROM tbl_meters "
                       " WHERE id = %s ",
                       (buy_meter_id,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.BUY_METER_NOT_FOUND')

        cursor.execute(" SELECT name "
                       " FROM tbl_meters "
                       " WHERE id = %s ",
                       (sell_meter_id,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.SELL_METER_NOT_FOUND')

        add_values = (" INSERT INTO tbl_energy_storage_containers_grids "
                      "    (name, uuid, energy_storage_container_id, power_point_id, "
                      "     buy_meter_id, sell_meter_id, capacity) "
                      " VALUES (%s, %s, %s, %s, %s, %s, %s) ")
        cursor.execute(add_values, (name,
                                    str(uuid.uuid4()),
                                    id_,
                                    power_point_id,
                                    buy_meter_id,
                                    sell_meter_id,
                                    capacity))
        new_id = cursor.lastrowid
        cnx.commit()
        cursor.close()
        cnx.close()

        resp.status = falcon.HTTP_201
        resp.location = '/energystoragecontainers/' + str(id_) + '/grids/' + str(new_id)


class EnergyStorageContainerGridItem:
    @staticmethod
    def __init__():
        """Initializes Class"""
        pass

    @staticmethod
    def on_options(req, resp, id_, gid):
        resp.status = falcon.HTTP_200

    @staticmethod
    def on_get(req, resp, id_, gid):
        access_control(req)
        if not id_.isdigit() or int(id_) <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_ENERGY_STORAGE_CONTAINER_ID')
        if not gid.isdigit() or int(gid) <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_ENERGY_STORAGE_CONTAINER_GRID_ID')

        cnx = mysql.connector.connect(**config.myems_system_db)
        cursor = cnx.cursor()

        cursor.execute(" SELECT name "
                       " FROM tbl_energy_storage_containers "
                       " WHERE id = %s ", (id_,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.ENERGY_STORAGE_CONTAINER_NOT_FOUND')

        query = (" SELECT id, name, uuid "
                 " FROM tbl_energy_storage_containers ")
        cursor.execute(query)
        rows_energystoragecontainers = cursor.fetchall()

        energy_storage_container_dict = dict()
        if rows_energystoragecontainers is not None and len(rows_energystoragecontainers) > 0:
            for row in rows_energystoragecontainers:
                energy_storage_container_dict[row[0]] = {"id": row[0],
                                                         "name": row[1],
                                                         "uuid": row[2]}
        # query meter dict
        query = (" SELECT id, name, uuid "
                 " FROM tbl_meters ")
        cursor.execute(query)
        rows_meters = cursor.fetchall()

        meter_dict = dict()
        if rows_meters is not None and len(rows_meters) > 0:
            for row in rows_meters:
                meter_dict[row[0]] = {"id": row[0],
                                      "name": row[1],
                                      "uuid": row[2]}
        # query point dict
        query = (" SELECT id, name "
                 " FROM tbl_points ")
        cursor.execute(query)
        rows_points = cursor.fetchall()

        point_dict = dict()
        if rows_points is not None and len(rows_points) > 0:
            for row in rows_points:
                point_dict[row[0]] = {"id": row[0],
                                      "name": row[1]}

        query = (" SELECT id, name, uuid, energy_storage_container_id, power_point_id, "
                 "        buy_meter_id, sell_meter_id, capacity "
                 " FROM tbl_energy_storage_containers_grids "
                 " WHERE id = %s ")
        cursor.execute(query, (gid,))
        row = cursor.fetchone()
        cursor.close()
        cnx.close()

        if row is None:
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.ENERGY_STORAGE_CONTAINER_GRID_NOT_FOUND')
        else:
            energy_storage_container = energy_storage_container_dict.get(row[3])
            power_point = point_dict.get(row[4])
            buy_meter = meter_dict.get(row[5])
            sell_meter = meter_dict.get(row[6])
            meta_result = {"id": row[0],
                           "name": row[1],
                           "uuid": row[2],
                           "energy_storage_container": energy_storage_container,
                           "power_point": power_point,
                           "buy_meter": buy_meter,
                           "sell_meter": sell_meter,
                           "capacity": row[7]}

        resp.text = json.dumps(meta_result)

    @staticmethod
    @user_logger
    def on_delete(req, resp, id_, gid):
        admin_control(req)
        if not id_.isdigit() or int(id_) <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_ENERGY_STORAGE_CONTAINER_ID')
        if not gid.isdigit() or int(gid) <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_ENERGY_STORAGE_CONTAINER_GRID_ID')

        cnx = mysql.connector.connect(**config.myems_system_db)
        cursor = cnx.cursor()

        cursor.execute(" SELECT name "
                       " FROM tbl_energy_storage_containers "
                       " WHERE id = %s ", (id_,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.ENERGY_STORAGE_CONTAINER_NOT_FOUND')

        cursor.execute(" SELECT name "
                       " FROM tbl_energy_storage_containers_grids "
                       " WHERE id = %s ", (gid,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.ENERGY_STORAGE_CONTAINER_GRID_NOT_FOUND')

        cursor.execute(" DELETE FROM tbl_energy_storage_containers_grids "
                       " WHERE id = %s ", (gid,))
        cnx.commit()

        cursor.close()
        cnx.close()

        resp.status = falcon.HTTP_204

    @staticmethod
    @user_logger
    def on_put(req, resp, id_, gid):
        """Handles PUT requests"""
        admin_control(req)
        try:
            raw_json = req.stream.read().decode('utf-8')
        except Exception as ex:
            raise falcon.HTTPError(status=falcon.HTTP_400,
                                   title='API.BAD_REQUEST',
                                   description='API.FAILED_TO_READ_REQUEST_STREAM')
        if not id_.isdigit() or int(id_) <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_ENERGY_STORAGE_CONTAINER_ID')

        if not gid.isdigit() or int(gid) <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_ENERGY_STORAGE_CONTAINER_GRID_ID')

        new_values = json.loads(raw_json)

        if 'name' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['name'], str) or \
                len(str.strip(new_values['data']['name'])) == 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_ENERGY_STORAGE_CONTAINER_GRID_NAME')
        name = str.strip(new_values['data']['name'])

        if 'power_point_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['power_point_id'], int) or \
                new_values['data']['power_point_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_POWER_POINT_ID')
        power_point_id = new_values['data']['power_point_id']

        if 'buy_meter_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['buy_meter_id'], int) or \
                new_values['data']['buy_meter_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_BUY_METER_ID')
        buy_meter_id = new_values['data']['buy_meter_id']

        if 'sell_meter_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['sell_meter_id'], int) or \
                new_values['data']['sell_meter_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_METER_ID')
        sell_meter_id = new_values['data']['sell_meter_id']

        if 'capacity' not in new_values['data'].keys() or \
                not (isinstance(new_values['data']['capacity'], float) or
                     isinstance(new_values['data']['capacity'], int)):
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_CAPACITY')
        capacity = float(new_values['data']['capacity'])

        cnx = mysql.connector.connect(**config.myems_system_db)
        cursor = cnx.cursor()

        cursor.execute(" SELECT name "
                       " FROM tbl_energy_storage_containers "
                       " WHERE id = %s ", (id_,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.ENERGY_STORAGE_CONTAINER_NOT_FOUND')

        cursor.execute(" SELECT name "
                       " FROM tbl_energy_storage_containers_grids "
                       " WHERE id = %s ", (gid,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.ENERGY_STORAGE_CONTAINER_GRID_NOT_FOUND')

        cursor.execute(" SELECT name "
                       " FROM tbl_energy_storage_containers_grids "
                       " WHERE energy_storage_container_id = %s AND name = %s AND id != %s ",
                       (id_, name, gid))
        if cursor.fetchone() is not None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.ENERGY_STORAGE_CONTAINER_GRID_NAME_IS_ALREADY_IN_USE')

        cursor.execute(" SELECT name "
                       " FROM tbl_points "
                       " WHERE id = %s ",
                       (power_point_id,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.POWER_POINT_NOT_FOUND')

        cursor.execute(" SELECT name "
                       " FROM tbl_meters "
                       " WHERE id = %s ",
                       (buy_meter_id,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.BUY_METER_NOT_FOUND')

        cursor.execute(" SELECT name "
                       " FROM tbl_meters "
                       " WHERE id = %s ",
                       (sell_meter_id,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.SELL_METER_NOT_FOUND')

        update_row = (" UPDATE tbl_energy_storage_containers_grids "
                      " SET name = %s, energy_storage_container_id = %s, "
                      "     power_point_id = %s, buy_meter_id = %s, sell_meter_id = %s, capacity = %s "
                      " WHERE id = %s ")
        cursor.execute(update_row, (name,
                                    id_,
                                    power_point_id,
                                    buy_meter_id,
                                    sell_meter_id,
                                    capacity,
                                    gid))
        cnx.commit()

        cursor.close()
        cnx.close()

        resp.status = falcon.HTTP_200


class EnergyStorageContainerLoadCollection:
    @staticmethod
    def __init__():
        """Initializes Class"""
        pass

    @staticmethod
    def on_options(req, resp, id_):
        resp.status = falcon.HTTP_200

    @staticmethod
    def on_get(req, resp, id_):
        access_control(req)
        if not id_.isdigit() or int(id_) <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_ENERGY_STORAGE_CONTAINER_ID')

        cnx = mysql.connector.connect(**config.myems_system_db)
        cursor = cnx.cursor()

        cursor.execute(" SELECT name "
                       " FROM tbl_energy_storage_containers "
                       " WHERE id = %s ", (id_,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.ENERGY_STORAGE_CONTAINER_NOT_FOUND')

        # query meter dict
        query = (" SELECT id, name, uuid "
                 " FROM tbl_meters ")
        cursor.execute(query)
        rows_meters = cursor.fetchall()

        meter_dict = dict()
        if rows_meters is not None and len(rows_meters) > 0:
            for row in rows_meters:
                meter_dict[row[0]] = {"id": row[0],
                                      "name": row[1],
                                      "uuid": row[2]}
        # query point dict
        query = (" SELECT id, name "
                 " FROM tbl_points ")
        cursor.execute(query)
        rows_points = cursor.fetchall()

        point_dict = dict()
        if rows_points is not None and len(rows_points) > 0:
            for row in rows_points:
                point_dict[row[0]] = {"id": row[0],
                                      "name": row[1]}

        query = (" SELECT id, name, uuid, "
                 "        power_point_id, meter_id, capacity "
                 " FROM tbl_energy_storage_containers_loads "
                 " WHERE energy_storage_container_id = %s "
                 " ORDER BY name ")
        cursor.execute(query, (id_,))
        rows = cursor.fetchall()

        result = list()
        if rows is not None and len(rows) > 0:
            for row in rows:
                power_point = point_dict.get(row[3])
                meter = meter_dict.get(row[4])
                meta_result = {"id": row[0],
                               "name": row[1],
                               "uuid": row[2],
                               "power_point": power_point,
                               "meter": meter,
                               "capacity": row[5]}
                result.append(meta_result)

        resp.text = json.dumps(result)

    @staticmethod
    @user_logger
    def on_post(req, resp, id_):
        """Handles POST requests"""
        admin_control(req)
        try:
            raw_json = req.stream.read().decode('utf-8')
        except Exception as ex:
            raise falcon.HTTPError(status=falcon.HTTP_400,
                                   title='API.BAD_REQUEST',
                                   description='API.FAILED_TO_READ_REQUEST_STREAM')
        if not id_.isdigit() or int(id_) <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_ENERGY_STORAGE_CONTAINER_ID')

        cnx = mysql.connector.connect(**config.myems_system_db)
        cursor = cnx.cursor()

        cursor.execute(" SELECT name "
                       " FROM tbl_energy_storage_containers "
                       " WHERE id = %s ", (id_,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.ENERGY_STORAGE_CONTAINER_NOT_FOUND')

        new_values = json.loads(raw_json)

        if 'name' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['name'], str) or \
                len(str.strip(new_values['data']['name'])) == 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_ENERGY_STORAGE_CONTAINER_LOAD_NAME')
        name = str.strip(new_values['data']['name'])

        if 'power_point_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['power_point_id'], int) or \
                new_values['data']['power_point_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_POWER_POINT_ID')
        power_point_id = new_values['data']['power_point_id']

        if 'meter_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['meter_id'], int) or \
                new_values['data']['meter_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_METER_ID')
        meter_id = new_values['data']['meter_id']

        if 'capacity' not in new_values['data'].keys() or \
                not (isinstance(new_values['data']['capacity'], float) or
                     isinstance(new_values['data']['capacity'], int)):
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_CAPACITY')
        capacity = float(new_values['data']['capacity'])

        cnx = mysql.connector.connect(**config.myems_system_db)
        cursor = cnx.cursor()

        cursor.execute(" SELECT name "
                       " FROM tbl_energy_storage_containers "
                       " WHERE id = %s ",
                       (id_,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.ENERGY_STORAGE_CONTAINER_NOT_FOUND')

        cursor.execute(" SELECT name "
                       " FROM tbl_energy_storage_containers_loads "
                       " WHERE energy_storage_container_id = %s AND name = %s ",
                       (id_, name,))
        if cursor.fetchone() is not None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.ENERGY_STORAGE_CONTAINER_LOAD_NAME_IS_ALREADY_IN_USE')

        cursor.execute(" SELECT name "
                       " FROM tbl_points "
                       " WHERE id = %s ",
                       (power_point_id,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.POWER_POINT_NOT_FOUND')

        cursor.execute(" SELECT name "
                       " FROM tbl_meters "
                       " WHERE id = %s ",
                       (meter_id,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.METER_NOT_FOUND')

        add_values = (" INSERT INTO tbl_energy_storage_containers_loads "
                      "    (name, uuid, energy_storage_container_id, power_point_id, meter_id, capacity) "
                      " VALUES (%s, %s, %s, %s, %s, %s) ")
        cursor.execute(add_values, (name,
                                    str(uuid.uuid4()),
                                    id_,
                                    power_point_id,
                                    meter_id,
                                    capacity))
        new_id = cursor.lastrowid
        cnx.commit()
        cursor.close()
        cnx.close()

        resp.status = falcon.HTTP_201
        resp.location = '/energystoragecontainers/' + str(id_) + '/loads/' + str(new_id)


class EnergyStorageContainerLoadItem:
    @staticmethod
    def __init__():
        """Initializes Class"""
        pass

    @staticmethod
    def on_options(req, resp, id_, lid):
        resp.status = falcon.HTTP_200

    @staticmethod
    def on_get(req, resp, id_, lid):
        access_control(req)
        if not id_.isdigit() or int(id_) <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_ENERGY_STORAGE_CONTAINER_ID')
        if not lid.isdigit() or int(lid) <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_ENERGY_STORAGE_CONTAINER_LOAD_ID')

        cnx = mysql.connector.connect(**config.myems_system_db)
        cursor = cnx.cursor()

        cursor.execute(" SELECT name "
                       " FROM tbl_energy_storage_containers "
                       " WHERE id = %s ", (id_,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.ENERGY_STORAGE_CONTAINER_NOT_FOUND')

        query = (" SELECT id, name, uuid "
                 " FROM tbl_energy_storage_containers ")
        cursor.execute(query)
        rows_energystoragecontainers = cursor.fetchall()

        energy_storage_container_dict = dict()
        if rows_energystoragecontainers is not None and len(rows_energystoragecontainers) > 0:
            for row in rows_energystoragecontainers:
                energy_storage_container_dict[row[0]] = {"id": row[0],
                                                         "name": row[1],
                                                         "uuid": row[2]}
        # query meter dict
        query = (" SELECT id, name, uuid "
                 " FROM tbl_meters ")
        cursor.execute(query)
        rows_meters = cursor.fetchall()

        meter_dict = dict()
        if rows_meters is not None and len(rows_meters) > 0:
            for row in rows_meters:
                meter_dict[row[0]] = {"id": row[0],
                                      "name": row[1],
                                      "uuid": row[2]}
        # query point dict
        query = (" SELECT id, name "
                 " FROM tbl_points ")
        cursor.execute(query)
        rows_points = cursor.fetchall()

        point_dict = dict()
        if rows_points is not None and len(rows_points) > 0:
            for row in rows_points:
                point_dict[row[0]] = {"id": row[0],
                                      "name": row[1]}

        query = (" SELECT id, name, uuid, energy_storage_container_id, power_point_id, meter_id, capacity "
                 " FROM tbl_energy_storage_containers_loads "
                 " WHERE id = %s ")
        cursor.execute(query, (lid,))
        row = cursor.fetchone()
        cursor.close()
        cnx.close()

        if row is None:
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.ENERGY_STORAGE_CONTAINER_LOAD_NOT_FOUND')
        else:
            energy_storage_container = energy_storage_container_dict.get(row[3])
            power_point = point_dict.get(row[4])
            meter = meter_dict.get(row[5])
            meta_result = {"id": row[0],
                           "name": row[1],
                           "uuid": row[2],
                           "energy_storage_container": energy_storage_container,
                           "power_point": power_point,
                           "meter": meter,
                           "capacity": row[6]}

        resp.text = json.dumps(meta_result)

    @staticmethod
    @user_logger
    def on_delete(req, resp, id_, lid):
        admin_control(req)
        if not id_.isdigit() or int(id_) <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_ENERGY_STORAGE_CONTAINER_ID')
        if not lid.isdigit() or int(lid) <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_ENERGY_STORAGE_CONTAINER_LOAD_ID')

        cnx = mysql.connector.connect(**config.myems_system_db)
        cursor = cnx.cursor()

        cursor.execute(" SELECT name "
                       " FROM tbl_energy_storage_containers "
                       " WHERE id = %s ", (id_,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.ENERGY_STORAGE_CONTAINER_NOT_FOUND')

        cursor.execute(" SELECT name "
                       " FROM tbl_energy_storage_containers_loads "
                       " WHERE id = %s ", (lid,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.ENERGY_STORAGE_CONTAINER_LOAD_NOT_FOUND')

        cursor.execute(" DELETE FROM tbl_energy_storage_containers_loads "
                       " WHERE id = %s ", (lid,))
        cnx.commit()

        cursor.close()
        cnx.close()

        resp.status = falcon.HTTP_204

    @staticmethod
    @user_logger
    def on_put(req, resp, id_, lid):
        """Handles PUT requests"""
        admin_control(req)
        try:
            raw_json = req.stream.read().decode('utf-8')
        except Exception as ex:
            raise falcon.HTTPError(status=falcon.HTTP_400,
                                   title='API.BAD_REQUEST',
                                   description='API.FAILED_TO_READ_REQUEST_STREAM')
        if not id_.isdigit() or int(id_) <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_ENERGY_STORAGE_CONTAINER_ID')
        if not lid.isdigit() or int(lid) <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_ENERGY_STORAGE_CONTAINER_LOAD_ID')

        new_values = json.loads(raw_json)

        if 'name' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['name'], str) or \
                len(str.strip(new_values['data']['name'])) == 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_ENERGY_STORAGE_CONTAINER_LOAD_NAME')
        name = str.strip(new_values['data']['name'])

        if 'power_point_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['power_point_id'], int) or \
                new_values['data']['power_point_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_POWER_POINT_ID')
        power_point_id = new_values['data']['power_point_id']

        if 'meter_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['meter_id'], int) or \
                new_values['data']['meter_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_METER_ID')
        meter_id = new_values['data']['meter_id']

        if 'capacity' not in new_values['data'].keys() or \
                not (isinstance(new_values['data']['capacity'], float) or
                     isinstance(new_values['data']['capacity'], int)):
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_CAPACITY')
        capacity = float(new_values['data']['capacity'])

        cnx = mysql.connector.connect(**config.myems_system_db)
        cursor = cnx.cursor()

        cursor.execute(" SELECT name "
                       " FROM tbl_energy_storage_containers "
                       " WHERE id = %s ", (id_,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.ENERGY_STORAGE_CONTAINER_NOT_FOUND')

        cursor.execute(" SELECT name "
                       " FROM tbl_energy_storage_containers_loads "
                       " WHERE id = %s ", (lid,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.ENERGY_STORAGE_CONTAINER_LOAD_NOT_FOUND')

        cursor.execute(" SELECT name "
                       " FROM tbl_energy_storage_containers_loads "
                       " WHERE energy_storage_container_id = %s AND name = %s AND id != %s ",
                       (id_, name, lid))
        if cursor.fetchone() is not None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.ENERGY_STORAGE_CONTAINER_LOAD_NAME_IS_ALREADY_IN_USE')

        cursor.execute(" SELECT name "
                       " FROM tbl_points "
                       " WHERE id = %s ",
                       (power_point_id,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.POWER_POINT_NOT_FOUND')

        cursor.execute(" SELECT name "
                       " FROM tbl_meters "
                       " WHERE id = %s ",
                       (meter_id,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.METER_NOT_FOUND')

        update_row = (" UPDATE tbl_energy_storage_containers_loads "
                      " SET name = %s, energy_storage_container_id = %s, power_point_id = %s, "
                      "     meter_id = %s, capacity = %s "
                      " WHERE id = %s ")
        cursor.execute(update_row, (name,
                                    id_,
                                    power_point_id,
                                    meter_id,
                                    capacity,
                                    lid))
        cnx.commit()

        cursor.close()
        cnx.close()

        resp.status = falcon.HTTP_200


class EnergyStorageContainerPowerconversionsystemCollection:
    @staticmethod
    def __init__():
        """Initializes Class"""
        pass

    @staticmethod
    def on_options(req, resp, id_):
        resp.status = falcon.HTTP_200

    @staticmethod
    def on_get(req, resp, id_):
        access_control(req)
        if not id_.isdigit() or int(id_) <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_ENERGY_STORAGE_CONTAINER_ID')

        cnx = mysql.connector.connect(**config.myems_system_db)
        cursor = cnx.cursor()

        cursor.execute(" SELECT name "
                       " FROM tbl_energy_storage_containers "
                       " WHERE id = %s ", (id_,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.ENERGY_STORAGE_CONTAINER_NOT_FOUND')

        # query point dict
        query = (" SELECT id, name "
                 " FROM tbl_points ")
        cursor.execute(query)
        rows_points = cursor.fetchall()

        point_dict = dict()
        if rows_points is not None and len(rows_points) > 0:
            for row in rows_points:
                point_dict[row[0]] = {"id": row[0],
                                      "name": row[1]}
        # query command dict
        query = (" SELECT id, name "
                 " FROM tbl_commands ")
        cursor.execute(query)
        rows_commands = cursor.fetchall()

        command_dict = dict()
        if rows_commands is not None and len(rows_commands) > 0:
            for row in rows_commands:
                command_dict[row[0]] = {"id": row[0],
                                        "name": row[1]}

        query = (" SELECT id, name, uuid, run_state_point_id, capacity, "
                 "        charge_start_time1_point_id, charge_end_time1_point_id, "
                 "        charge_start_time2_point_id, charge_end_time2_point_id, "
                 "        charge_start_time3_point_id, charge_end_time3_point_id, "
                 "        charge_start_time4_point_id, charge_end_time4_point_id, "
                 "        discharge_start_time1_point_id, discharge_end_time1_point_id, "
                 "        discharge_start_time2_point_id, discharge_end_time2_point_id, "
                 "        discharge_start_time3_point_id, discharge_end_time3_point_id, "
                 "        discharge_start_time4_point_id, discharge_end_time4_point_id, "
                 "        charge_start_time1_command_id, charge_end_time1_command_id, "
                 "        charge_start_time2_command_id, charge_end_time2_command_id, "
                 "        charge_start_time3_command_id, charge_end_time3_command_id, "
                 "        charge_start_time4_command_id, charge_end_time4_command_id, "
                 "        discharge_start_time1_command_id, discharge_end_time1_command_id, "
                 "        discharge_start_time2_command_id, discharge_end_time2_command_id, "
                 "        discharge_start_time3_command_id, discharge_end_time3_command_id, "
                 "        discharge_start_time4_command_id, discharge_end_time4_command_id "
                 " FROM tbl_energy_storage_containers_power_conversion_systems "
                 " WHERE energy_storage_container_id = %s "
                 " ORDER BY name ")
        cursor.execute(query, (id_,))
        rows = cursor.fetchall()

        result = list()
        if rows is not None and len(rows) > 0:
            for row in rows:
                run_state_point = point_dict.get(row[3])
                charge_start_time1_point = point_dict.get(row[5])
                charge_end_time1_point = point_dict.get(row[6])
                charge_start_time2_point = point_dict.get(row[7])
                charge_end_time2_point = point_dict.get(row[8])
                charge_start_time3_point = point_dict.get(row[9])
                charge_end_time3_point = point_dict.get(row[10])
                charge_start_time4_point = point_dict.get(row[11])
                charge_end_time4_point = point_dict.get(row[12])
                discharge_start_time1_point = point_dict.get(row[13])
                discharge_end_time1_point = point_dict.get(row[14])
                discharge_start_time2_point = point_dict.get(row[15])
                discharge_end_time2_point = point_dict.get(row[16])
                discharge_start_time3_point = point_dict.get(row[17])
                discharge_end_time3_point = point_dict.get(row[18])
                discharge_start_time4_point = point_dict.get(row[19])
                discharge_end_time4_point = point_dict.get(row[20])
                charge_start_time1_command = command_dict.get(row[21])
                charge_end_time1_command = command_dict.get(row[22])
                charge_start_time2_command = command_dict.get(row[23])
                charge_end_time2_command = command_dict.get(row[24])
                charge_start_time3_command = command_dict.get(row[25])
                charge_end_time3_command = command_dict.get(row[26])
                charge_start_time4_command = command_dict.get(row[27])
                charge_end_time4_command = command_dict.get(row[28])
                discharge_start_time1_command = command_dict.get(row[29])
                discharge_end_time1_command = command_dict.get(row[30])
                discharge_start_time2_command = command_dict.get(row[31])
                discharge_end_time2_command = command_dict.get(row[32])
                discharge_start_time3_command = command_dict.get(row[33])
                discharge_end_time3_command = command_dict.get(row[34])
                discharge_start_time4_command = command_dict.get(row[35])
                discharge_end_time4_command = command_dict.get(row[36])
                meta_result = {"id": row[0],
                               "name": row[1],
                               "uuid": row[2],
                               "run_state_point": run_state_point,
                               "capacity": row[4],
                               "charge_start_time1_point": charge_start_time1_point,
                               "charge_end_time1_point": charge_end_time1_point,
                               "charge_start_time2_point": charge_start_time2_point,
                               "charge_end_time2_point": charge_end_time2_point,
                               "charge_start_time3_point": charge_start_time3_point,
                               "charge_end_time3_point": charge_end_time3_point,
                               "charge_start_time4_point": charge_start_time4_point,
                               "charge_end_time4_point": charge_end_time4_point,
                               "discharge_start_time1_point": discharge_start_time1_point,
                               "discharge_end_time1_point": discharge_end_time1_point,
                               "discharge_start_time2_point": discharge_start_time2_point,
                               "discharge_end_time2_point": discharge_end_time2_point,
                               "discharge_start_time3_point": discharge_start_time3_point,
                               "discharge_end_time3_point": discharge_end_time3_point,
                               "discharge_start_time4_point": discharge_start_time4_point,
                               "discharge_end_time4_point": discharge_end_time4_point,
                               "charge_start_time1_command": charge_start_time1_command,
                               "charge_end_time1_command": charge_end_time1_command,
                               "charge_start_time2_command": charge_start_time2_command,
                               "charge_end_time2_command": charge_end_time2_command,
                               "charge_start_time3_command": charge_start_time3_command,
                               "charge_end_time3_command": charge_end_time3_command,
                               "charge_start_time4_command": charge_start_time4_command,
                               "charge_end_time4_command": charge_end_time4_command,
                               "discharge_start_time1_command": discharge_start_time1_command,
                               "discharge_end_time1_command": discharge_end_time1_command,
                               "discharge_start_time2_command": discharge_start_time2_command,
                               "discharge_end_time2_command": discharge_end_time2_command,
                               "discharge_start_time3_command": discharge_start_time3_command,
                               "discharge_end_time3_command": discharge_end_time3_command,
                               "discharge_start_time4_command": discharge_start_time4_command,
                               "discharge_end_time4_command": discharge_end_time4_command}
                result.append(meta_result)

        resp.text = json.dumps(result)

    @staticmethod
    @user_logger
    def on_post(req, resp, id_):
        """Handles POST requests"""
        admin_control(req)
        try:
            raw_json = req.stream.read().decode('utf-8')
        except Exception as ex:
            raise falcon.HTTPError(status=falcon.HTTP_400,
                                   title='API.BAD_REQUEST',
                                   description='API.FAILED_TO_READ_REQUEST_STREAM')
        if not id_.isdigit() or int(id_) <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_ENERGY_STORAGE_CONTAINER_ID')

        cnx = mysql.connector.connect(**config.myems_system_db)
        cursor = cnx.cursor()

        cursor.execute(" SELECT name "
                       " FROM tbl_energy_storage_containers "
                       " WHERE id = %s ", (id_,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.ENERGY_STORAGE_CONTAINER_NOT_FOUND')

        new_values = json.loads(raw_json)

        if 'name' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['name'], str) or \
                len(str.strip(new_values['data']['name'])) == 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_ENERGY_STORAGE_CONTAINER_POWER_CONVERSION_SYSTEM_NAME')
        name = str.strip(new_values['data']['name'])

        if 'run_state_point_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['run_state_point_id'], int) or \
                new_values['data']['run_state_point_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_RUN_STATE_POINT_ID')
        run_state_point_id = new_values['data']['run_state_point_id']

        if 'capacity' not in new_values['data'].keys() or \
                not (isinstance(new_values['data']['capacity'], float) or
                     isinstance(new_values['data']['capacity'], int)):
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_CAPACITY')
        capacity = float(new_values['data']['capacity'])

        if 'charge_start_time1_point_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['charge_start_time1_point_id'], int) or \
                new_values['data']['charge_start_time1_point_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_CHARGE_START_TIME1_POINT_ID')
        charge_start_time1_point_id = new_values['data']['charge_start_time1_point_id']

        if 'charge_end_time1_point_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['charge_end_time1_point_id'], int) or \
                new_values['data']['charge_end_time1_point_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_CHARGE_END_TIME1_POINT_ID')
        charge_end_time1_point_id = new_values['data']['charge_end_time1_point_id']

        if 'charge_start_time2_point_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['charge_start_time2_point_id'], int) or \
                new_values['data']['charge_start_time2_point_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_CHARGE_START_TIME2_POINT_ID')
        charge_start_time2_point_id = new_values['data']['charge_start_time2_point_id']

        if 'charge_end_time2_point_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['charge_end_time2_point_id'], int) or \
                new_values['data']['charge_end_time2_point_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_CHARGE_END_TIME2_POINT_ID')
        charge_end_time2_point_id = new_values['data']['charge_end_time2_point_id']

        if 'charge_start_time3_point_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['charge_start_time3_point_id'], int) or \
                new_values['data']['charge_start_time3_point_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_CHARGE_START_TIME3_POINT_ID')
        charge_start_time3_point_id = new_values['data']['charge_start_time3_point_id']

        if 'charge_end_time3_point_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['charge_end_time3_point_id'], int) or \
                new_values['data']['charge_end_time3_point_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_CHARGE_END_TIME3_POINT_ID')
        charge_end_time3_point_id = new_values['data']['charge_end_time3_point_id']

        if 'charge_start_time4_point_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['charge_start_time4_point_id'], int) or \
                new_values['data']['charge_start_time4_point_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_CHARGE_START_TIME4_POINT_ID')
        charge_start_time4_point_id = new_values['data']['charge_start_time4_point_id']

        if 'charge_end_time4_point_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['charge_end_time4_point_id'], int) or \
                new_values['data']['charge_end_time4_point_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_CHARGE_END_TIME4_POINT_ID')
        charge_end_time4_point_id = new_values['data']['charge_end_time4_point_id']

        if 'discharge_start_time1_point_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['discharge_start_time1_point_id'], int) or \
                new_values['data']['discharge_start_time1_point_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_DISCHARGE_START_TIME1_POINT_ID')
        discharge_start_time1_point_id = new_values['data']['discharge_start_time1_point_id']

        if 'discharge_end_time1_point_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['discharge_end_time1_point_id'], int) or \
                new_values['data']['discharge_end_time1_point_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_DISCHARGE_END_TIME1_POINT_ID')
        discharge_end_time1_point_id = new_values['data']['discharge_end_time1_point_id']

        if 'discharge_start_time2_point_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['discharge_start_time2_point_id'], int) or \
                new_values['data']['discharge_start_time2_point_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_DISCHARGE_START_TIME2_POINT_ID')
        discharge_start_time2_point_id = new_values['data']['discharge_start_time2_point_id']

        if 'discharge_end_time2_point_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['discharge_end_time2_point_id'], int) or \
                new_values['data']['discharge_end_time2_point_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_DISCHARGE_END_TIME2_POINT_ID')
        discharge_end_time2_point_id = new_values['data']['discharge_end_time2_point_id']

        if 'discharge_start_time3_point_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['discharge_start_time3_point_id'], int) or \
                new_values['data']['discharge_start_time3_point_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_DISCHARGE_START_TIME3_POINT_ID')
        discharge_start_time3_point_id = new_values['data']['discharge_start_time3_point_id']

        if 'discharge_end_time3_point_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['discharge_end_time3_point_id'], int) or \
                new_values['data']['discharge_end_time3_point_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_DISCHARGE_END_TIME3_POINT_ID')
        discharge_end_time3_point_id = new_values['data']['discharge_end_time3_point_id']

        if 'discharge_start_time4_point_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['discharge_start_time4_point_id'], int) or \
                new_values['data']['discharge_start_time4_point_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_DISCHARGE_START_TIME4_POINT_ID')
        discharge_start_time4_point_id = new_values['data']['discharge_start_time4_point_id']

        if 'discharge_end_time4_point_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['discharge_end_time4_point_id'], int) or \
                new_values['data']['discharge_end_time4_point_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_DISCHARGE_END_TIME4_POINT_ID')
        discharge_end_time4_point_id = new_values['data']['discharge_end_time4_point_id']

        if 'charge_start_time1_command_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['charge_start_time1_command_id'], int) or \
                new_values['data']['charge_start_time1_command_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_CHARGE_START_TIME1_POINT_ID')
        charge_start_time1_command_id = new_values['data']['charge_start_time1_command_id']

        if 'charge_end_time1_command_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['charge_end_time1_command_id'], int) or \
                new_values['data']['charge_end_time1_command_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_CHARGE_END_TIME1_POINT_ID')
        charge_end_time1_command_id = new_values['data']['charge_end_time1_command_id']

        if 'charge_start_time2_command_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['charge_start_time2_command_id'], int) or \
                new_values['data']['charge_start_time2_command_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_CHARGE_START_TIME2_POINT_ID')
        charge_start_time2_command_id = new_values['data']['charge_start_time2_command_id']

        if 'charge_end_time2_command_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['charge_end_time2_command_id'], int) or \
                new_values['data']['charge_end_time2_command_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_CHARGE_END_TIME2_POINT_ID')
        charge_end_time2_command_id = new_values['data']['charge_end_time2_command_id']

        if 'charge_start_time3_command_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['charge_start_time3_command_id'], int) or \
                new_values['data']['charge_start_time3_command_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_CHARGE_START_TIME3_POINT_ID')
        charge_start_time3_command_id = new_values['data']['charge_start_time3_command_id']

        if 'charge_end_time3_command_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['charge_end_time3_command_id'], int) or \
                new_values['data']['charge_end_time3_command_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_CHARGE_END_TIME3_POINT_ID')
        charge_end_time3_command_id = new_values['data']['charge_end_time3_command_id']

        if 'charge_start_time4_command_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['charge_start_time4_command_id'], int) or \
                new_values['data']['charge_start_time4_command_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_CHARGE_START_TIME4_POINT_ID')
        charge_start_time4_command_id = new_values['data']['charge_start_time4_command_id']

        if 'charge_end_time4_command_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['charge_end_time4_command_id'], int) or \
                new_values['data']['charge_end_time4_command_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_CHARGE_END_TIME4_POINT_ID')
        charge_end_time4_command_id = new_values['data']['charge_end_time4_command_id']

        if 'discharge_start_time1_command_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['discharge_start_time1_command_id'], int) or \
                new_values['data']['discharge_start_time1_command_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_DISCHARGE_START_TIME1_POINT_ID')
        discharge_start_time1_command_id = new_values['data']['discharge_start_time1_command_id']

        if 'discharge_end_time1_command_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['discharge_end_time1_command_id'], int) or \
                new_values['data']['discharge_end_time1_command_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_DISCHARGE_END_TIME1_POINT_ID')
        discharge_end_time1_command_id = new_values['data']['discharge_end_time1_command_id']

        if 'discharge_start_time2_command_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['discharge_start_time2_command_id'], int) or \
                new_values['data']['discharge_start_time2_command_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_DISCHARGE_START_TIME2_POINT_ID')
        discharge_start_time2_command_id = new_values['data']['discharge_start_time2_command_id']

        if 'discharge_end_time2_command_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['discharge_end_time2_command_id'], int) or \
                new_values['data']['discharge_end_time2_command_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_DISCHARGE_END_TIME2_POINT_ID')
        discharge_end_time2_command_id = new_values['data']['discharge_end_time2_command_id']

        if 'discharge_start_time3_command_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['discharge_start_time3_command_id'], int) or \
                new_values['data']['discharge_start_time3_command_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_DISCHARGE_START_TIME3_POINT_ID')
        discharge_start_time3_command_id = new_values['data']['discharge_start_time3_command_id']

        if 'discharge_end_time3_command_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['discharge_end_time3_command_id'], int) or \
                new_values['data']['discharge_end_time3_command_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_DISCHARGE_END_TIME3_POINT_ID')
        discharge_end_time3_command_id = new_values['data']['discharge_end_time3_command_id']

        if 'discharge_start_time4_command_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['discharge_start_time4_command_id'], int) or \
                new_values['data']['discharge_start_time4_command_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_DISCHARGE_START_TIME4_POINT_ID')
        discharge_start_time4_command_id = new_values['data']['discharge_start_time4_command_id']

        if 'discharge_end_time4_command_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['discharge_end_time4_command_id'], int) or \
                new_values['data']['discharge_end_time4_command_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_DISCHARGE_END_TIME4_POINT_ID')
        discharge_end_time4_command_id = new_values['data']['discharge_end_time4_command_id']

        cnx = mysql.connector.connect(**config.myems_system_db)
        cursor = cnx.cursor()

        cursor.execute(" SELECT name "
                       " FROM tbl_energy_storage_containers "
                       " WHERE id = %s ",
                       (id_,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.ENERGY_STORAGE_CONTAINER_NOT_FOUND')

        cursor.execute(" SELECT name "
                       " FROM tbl_energy_storage_containers_power_conversion_systems "
                       " WHERE energy_storage_container_id = %s AND name = %s ",
                       (id_, name,))
        if cursor.fetchone() is not None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.ENERGY_STORAGE_CONTAINER_PCS_NAME_IS_ALREADY_IN_USE')

        add_values = (" INSERT INTO tbl_energy_storage_containers_power_conversion_systems "
                      "     (name, uuid, energy_storage_container_id, run_state_point_id, capacity, "
                      "      charge_start_time1_point_id, charge_end_time1_point_id, "
                      "      charge_start_time2_point_id, charge_end_time2_point_id, "
                      "      charge_start_time3_point_id, charge_end_time3_point_id, "
                      "      charge_start_time4_point_id, charge_end_time4_point_id, "
                      "      discharge_start_time1_point_id, discharge_end_time1_point_id, "
                      "      discharge_start_time2_point_id, discharge_end_time2_point_id, "
                      "      discharge_start_time3_point_id, discharge_end_time3_point_id, "
                      "      discharge_start_time4_point_id, discharge_end_time4_point_id, "
                      "      charge_start_time1_command_id, charge_end_time1_command_id, "
                      "      charge_start_time2_command_id, charge_end_time2_command_id, "
                      "      charge_start_time3_command_id, charge_end_time3_command_id, "
                      "      charge_start_time4_command_id, charge_end_time4_command_id, "
                      "      discharge_start_time1_command_id, discharge_end_time1_command_id, "
                      "      discharge_start_time2_command_id, discharge_end_time2_command_id, "
                      "      discharge_start_time3_command_id, discharge_end_time3_command_id, "
                      "      discharge_start_time4_command_id, discharge_end_time4_command_id) "
                      " VALUES (%s, %s, %s, %s, %s, "
                      "         %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, "
                      "         %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ")
        cursor.execute(add_values, (name,
                                    str(uuid.uuid4()),
                                    id_,
                                    run_state_point_id,
                                    capacity,
                                    charge_start_time1_point_id,
                                    charge_end_time1_point_id,
                                    charge_start_time2_point_id,
                                    charge_end_time2_point_id,
                                    charge_start_time3_point_id,
                                    charge_end_time3_point_id,
                                    charge_start_time4_point_id,
                                    charge_end_time4_point_id,
                                    discharge_start_time1_point_id,
                                    discharge_end_time1_point_id,
                                    discharge_start_time2_point_id,
                                    discharge_end_time2_point_id,
                                    discharge_start_time3_point_id,
                                    discharge_end_time3_point_id,
                                    discharge_start_time4_point_id,
                                    discharge_end_time4_point_id,
                                    charge_start_time1_command_id,
                                    charge_end_time1_command_id,
                                    charge_start_time2_command_id,
                                    charge_end_time2_command_id,
                                    charge_start_time3_command_id,
                                    charge_end_time3_command_id,
                                    charge_start_time4_command_id,
                                    charge_end_time4_command_id,
                                    discharge_start_time1_command_id,
                                    discharge_end_time1_command_id,
                                    discharge_start_time2_command_id,
                                    discharge_end_time2_command_id,
                                    discharge_start_time3_command_id,
                                    discharge_end_time3_command_id,
                                    discharge_start_time4_command_id,
                                    discharge_end_time4_command_id
                                    ))
        new_id = cursor.lastrowid
        cnx.commit()
        cursor.close()
        cnx.close()

        resp.status = falcon.HTTP_201
        resp.location = '/energystoragecontainerpowerconversionsystems/' + str(new_id)


class EnergyStorageContainerPowerconversionsystemItem:
    @staticmethod
    def __init__():
        """Initializes Class"""
        pass

    @staticmethod
    def on_options(req, resp, id_, pid):
        resp.status = falcon.HTTP_200

    @staticmethod
    def on_get(req, resp, id_, pid):
        access_control(req)
        if not id_.isdigit() or int(id_) <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_ENERGY_STORAGE_CONTAINER_ID')
        if not pid.isdigit() or int(pid) <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_ENERGY_STORAGE_CONTAINER_POWER_CONVERSION_SYSTEM_ID')

        cnx = mysql.connector.connect(**config.myems_system_db)
        cursor = cnx.cursor()

        cursor.execute(" SELECT name "
                       " FROM tbl_energy_storage_containers "
                       " WHERE id = %s ", (id_,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.ENERGY_STORAGE_CONTAINER_NOT_FOUND')

        query = (" SELECT id, name, uuid "
                 " FROM tbl_energy_storage_containers ")
        cursor.execute(query)
        rows_energystoragecontainers = cursor.fetchall()

        energy_storage_container_dict = dict()
        if rows_energystoragecontainers is not None and len(rows_energystoragecontainers) > 0:
            for row in rows_energystoragecontainers:
                energy_storage_container_dict[row[0]] = {"id": row[0],
                                                         "name": row[1],
                                                         "uuid": row[2]}
        query = (" SELECT id, name, uuid "
                 " FROM tbl_meters ")
        cursor.execute(query)
        rows_meters = cursor.fetchall()

        meter_dict = dict()
        if rows_meters is not None and len(rows_meters) > 0:
            for row in rows_meters:
                meter_dict[row[0]] = {"id": row[0],
                                      "name": row[1],
                                      "uuid": row[2]}
        # query point dict
        query = (" SELECT id, name "
                 " FROM tbl_points ")
        cursor.execute(query)
        rows_points = cursor.fetchall()

        point_dict = dict()
        if rows_points is not None and len(rows_points) > 0:
            for row in rows_points:
                point_dict[row[0]] = {"id": row[0],
                                      "name": row[1]}

        # query command dict
        query = (" SELECT id, name "
                 " FROM tbl_commands ")
        cursor.execute(query)
        rows_commands = cursor.fetchall()

        command_dict = dict()
        if rows_commands is not None and len(rows_commands) > 0:
            for row in rows_commands:
                command_dict[row[0]] = {"id": row[0],
                                        "name": row[1]}

        query = (" SELECT id, name, uuid, energy_storage_container_id, run_state_point_id, capacity, "
                 "        charge_start_time1_point_id, charge_end_time1_point_id, "
                 "        charge_start_time2_point_id, charge_end_time2_point_id, "
                 "        charge_start_time3_point_id, charge_end_time3_point_id, "
                 "        charge_start_time4_point_id, charge_end_time4_point_id, "
                 "        discharge_start_time1_point_id, discharge_end_time1_point_id, "
                 "        discharge_start_time2_point_id, discharge_end_time2_point_id, "
                 "        discharge_start_time3_point_id, discharge_end_time3_point_id, "
                 "        discharge_start_time4_point_id, discharge_end_time4_point_id, "
                 "        charge_start_time1_command_id, charge_end_time1_command_id, "
                 "        charge_start_time2_command_id, charge_end_time2_command_id, "
                 "        charge_start_time3_command_id, charge_end_time3_command_id, "
                 "        charge_start_time4_command_id, charge_end_time4_command_id, "
                 "        discharge_start_time1_command_id, discharge_end_time1_command_id, "
                 "        discharge_start_time2_command_id, discharge_end_time2_command_id, "
                 "        discharge_start_time3_command_id, discharge_end_time3_command_id, "
                 "        discharge_start_time4_command_id, discharge_end_time4_command_id "
                 " FROM tbl_energy_storage_containers_power_conversion_systems "
                 " WHERE id = %s ")
        cursor.execute(query, (pid,))
        row = cursor.fetchone()
        cursor.close()
        cnx.close()

        if row is None:
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.ENERGY_STORAGE_CONTAINER_POWER_CONVERSION_SYSTEM_NOT_FOUND')
        else:
            energy_storage_container = energy_storage_container_dict.get(row[3])
            run_state_point = point_dict.get(row[4])
            charge_start_time1_point = point_dict.get(row[6])
            charge_end_time1_point = point_dict.get(row[7])
            charge_start_time2_point = point_dict.get(row[8])
            charge_end_time2_point = point_dict.get(row[9])
            charge_start_time3_point = point_dict.get(row[10])
            charge_end_time3_point = point_dict.get(row[11])
            charge_start_time4_point = point_dict.get(row[12])
            charge_end_time4_point = point_dict.get(row[13])
            discharge_start_time1_point = point_dict.get(row[14])
            discharge_end_time1_point = point_dict.get(row[15])
            discharge_start_time2_point = point_dict.get(row[16])
            discharge_end_time2_point = point_dict.get(row[17])
            discharge_start_time3_point = point_dict.get(row[18])
            discharge_end_time3_point = point_dict.get(row[19])
            discharge_start_time4_point = point_dict.get(row[20])
            discharge_end_time4_point = point_dict.get(row[21])
            charge_start_time1_command = command_dict.get(row[22])
            charge_end_time1_command = command_dict.get(row[23])
            charge_start_time2_command = command_dict.get(row[24])
            charge_end_time2_command = command_dict.get(row[25])
            charge_start_time3_command = command_dict.get(row[26])
            charge_end_time3_command = command_dict.get(row[27])
            charge_start_time4_command = command_dict.get(row[28])
            charge_end_time4_command = command_dict.get(row[29])
            discharge_start_time1_command = command_dict.get(row[30])
            discharge_end_time1_command = command_dict.get(row[31])
            discharge_start_time2_command = command_dict.get(row[32])
            discharge_end_time2_command = command_dict.get(row[33])
            discharge_start_time3_command = command_dict.get(row[34])
            discharge_end_time3_command = command_dict.get(row[35])
            discharge_start_time4_command = command_dict.get(row[36])
            discharge_end_time4_command = command_dict.get(row[37])
            meta_result = {"id": row[0],
                           "name": row[1],
                           "uuid": row[2],
                           "energy_storage_container": energy_storage_container,
                           "run_state_point": run_state_point,
                           "capacity": row[5],
                           "charge_start_time1_point": charge_start_time1_point,
                           "charge_end_time1_point": charge_end_time1_point,
                           "charge_start_time2_point": charge_start_time2_point,
                           "charge_end_time2_point": charge_end_time2_point,
                           "charge_start_time3_point": charge_start_time3_point,
                           "charge_end_time3_point": charge_end_time3_point,
                           "charge_start_time4_point": charge_start_time4_point,
                           "charge_end_time4_point": charge_end_time4_point,
                           "discharge_start_time1_point": discharge_start_time1_point,
                           "discharge_end_time1_point": discharge_end_time1_point,
                           "discharge_start_time2_point": discharge_start_time2_point,
                           "discharge_end_time2_point": discharge_end_time2_point,
                           "discharge_start_time3_point": discharge_start_time3_point,
                           "discharge_end_time3_point": discharge_end_time3_point,
                           "discharge_start_time4_point": discharge_start_time4_point,
                           "discharge_end_time4_point": discharge_end_time4_point,
                           "charge_start_time1_command": charge_start_time1_command,
                           "charge_end_time1_command": charge_end_time1_command,
                           "charge_start_time2_command": charge_start_time2_command,
                           "charge_end_time2_command": charge_end_time2_command,
                           "charge_start_time3_command": charge_start_time3_command,
                           "charge_end_time3_command": charge_end_time3_command,
                           "charge_start_time4_command": charge_start_time4_command,
                           "charge_end_time4_command": charge_end_time4_command,
                           "discharge_start_time1_command": discharge_start_time1_command,
                           "discharge_end_time1_command": discharge_end_time1_command,
                           "discharge_start_time2_command": discharge_start_time2_command,
                           "discharge_end_time2_command": discharge_end_time2_command,
                           "discharge_start_time3_command": discharge_start_time3_command,
                           "discharge_end_time3_command": discharge_end_time3_command,
                           "discharge_start_time4_command": discharge_start_time4_command,
                           "discharge_end_time4_command": discharge_end_time4_command}

        resp.text = json.dumps(meta_result)

    @staticmethod
    @user_logger
    def on_delete(req, resp, id_, pid):
        admin_control(req)
        if not id_.isdigit() or int(id_) <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_ENERGY_STORAGE_CONTAINER_ID')
        if not pid.isdigit() or int(pid) <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_ENERGY_STORAGE_CONTAINER_POWER_CONVERSION_SYSTEM_ID')

        cnx = mysql.connector.connect(**config.myems_system_db)
        cursor = cnx.cursor()

        cursor.execute(" SELECT name "
                       " FROM tbl_energy_storage_containers "
                       " WHERE id = %s ", (id_,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.ENERGY_STORAGE_CONTAINER_NOT_FOUND')

        cursor.execute(" SELECT name "
                       " FROM tbl_energy_storage_containers_power_conversion_systems "
                       " WHERE id = %s ", (pid,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.ENERGY_STORAGE_CONTAINER_POWER_CONVERSION_SYSTEM_NOT_FOUND')

        cursor.execute(" DELETE FROM tbl_energy_storage_containers_power_conversion_systems "
                       " WHERE id = %s ", (pid,))
        cnx.commit()

        cursor.close()
        cnx.close()

        resp.status = falcon.HTTP_204

    @staticmethod
    @user_logger
    def on_put(req, resp, id_, pid):
        """Handles PUT requests"""
        admin_control(req)
        try:
            raw_json = req.stream.read().decode('utf-8')
        except Exception as ex:
            raise falcon.HTTPError(status=falcon.HTTP_400,
                                   title='API.BAD_REQUEST',
                                   description='API.FAILED_TO_READ_REQUEST_STREAM')
        if not id_.isdigit() or int(id_) <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_ENERGY_STORAGE_CONTAINER_ID')
        if not pid.isdigit() or int(pid) <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_ENERGY_STORAGE_CONTAINER_POWER_CONVERSION_SYSTEM_ID')

        new_values = json.loads(raw_json)

        if 'name' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['name'], str) or \
                len(str.strip(new_values['data']['name'])) == 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_ENERGY_STORAGE_CONTAINER_POWER_CONVERSION_SYSTEM_NAME')
        name = str.strip(new_values['data']['name'])

        if 'run_state_point_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['run_state_point_id'], int) or \
                new_values['data']['run_state_point_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_RUN_STATE_POINT_ID')
        run_state_point_id = new_values['data']['run_state_point_id']

        if 'capacity' not in new_values['data'].keys() or \
                not (isinstance(new_values['data']['capacity'], float) or
                     isinstance(new_values['data']['capacity'], int)):
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_CAPACITY')
        capacity = float(new_values['data']['capacity'])

        if 'charge_start_time1_point_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['charge_start_time1_point_id'], int) or \
                new_values['data']['charge_start_time1_point_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_CHARGE_START_TIME1_COMMAND_ID')
        charge_start_time1_point_id = new_values['data']['charge_start_time1_point_id']

        if 'charge_end_time1_point_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['charge_end_time1_point_id'], int) or \
                new_values['data']['charge_end_time1_point_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_CHARGE_END_TIME1_COMMAND_ID')
        charge_end_time1_point_id = new_values['data']['charge_end_time1_point_id']

        if 'charge_start_time2_point_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['charge_start_time2_point_id'], int) or \
                new_values['data']['charge_start_time2_point_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_CHARGE_START_TIME2_COMMAND_ID')
        charge_start_time2_point_id = new_values['data']['charge_start_time2_point_id']

        if 'charge_end_time2_point_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['charge_end_time2_point_id'], int) or \
                new_values['data']['charge_end_time2_point_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_CHARGE_END_TIME2_COMMAND_ID')
        charge_end_time2_point_id = new_values['data']['charge_end_time2_point_id']

        if 'charge_start_time3_point_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['charge_start_time3_point_id'], int) or \
                new_values['data']['charge_start_time3_point_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_CHARGE_START_TIME3_COMMAND_ID')
        charge_start_time3_point_id = new_values['data']['charge_start_time3_point_id']

        if 'charge_end_time3_point_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['charge_end_time3_point_id'], int) or \
                new_values['data']['charge_end_time3_point_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_CHARGE_END_TIME3_COMMAND_ID')
        charge_end_time3_point_id = new_values['data']['charge_end_time3_point_id']

        if 'charge_start_time4_point_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['charge_start_time4_point_id'], int) or \
                new_values['data']['charge_start_time4_point_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_CHARGE_START_TIME4_COMMAND_ID')
        charge_start_time4_point_id = new_values['data']['charge_start_time4_point_id']

        if 'charge_end_time4_point_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['charge_end_time4_point_id'], int) or \
                new_values['data']['charge_end_time4_point_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_CHARGE_END_TIME4_COMMAND_ID')
        charge_end_time4_point_id = new_values['data']['charge_end_time4_point_id']

        if 'discharge_start_time1_point_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['discharge_start_time1_point_id'], int) or \
                new_values['data']['discharge_start_time1_point_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_DISCHARGE_START_TIME1_COMMAND_ID')
        discharge_start_time1_point_id = new_values['data']['discharge_start_time1_point_id']

        if 'discharge_end_time1_point_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['discharge_end_time1_point_id'], int) or \
                new_values['data']['discharge_end_time1_point_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_DISCHARGE_END_TIME1_COMMAND_ID')
        discharge_end_time1_point_id = new_values['data']['discharge_end_time1_point_id']

        if 'discharge_start_time2_point_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['discharge_start_time2_point_id'], int) or \
                new_values['data']['discharge_start_time2_point_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_DISCHARGE_START_TIME2_COMMAND_ID')
        discharge_start_time2_point_id = new_values['data']['discharge_start_time2_point_id']

        if 'discharge_end_time2_point_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['discharge_end_time2_point_id'], int) or \
                new_values['data']['discharge_end_time2_point_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_DISCHARGE_END_TIME2_COMMAND_ID')
        discharge_end_time2_point_id = new_values['data']['discharge_end_time2_point_id']

        if 'discharge_start_time3_point_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['discharge_start_time3_point_id'], int) or \
                new_values['data']['discharge_start_time3_point_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_DISCHARGE_START_TIME3_COMMAND_ID')
        discharge_start_time3_point_id = new_values['data']['discharge_start_time3_point_id']

        if 'discharge_end_time3_point_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['discharge_end_time3_point_id'], int) or \
                new_values['data']['discharge_end_time3_point_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_DISCHARGE_END_TIME3_COMMAND_ID')
        discharge_end_time3_point_id = new_values['data']['discharge_end_time3_point_id']

        if 'discharge_start_time4_point_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['discharge_start_time4_point_id'], int) or \
                new_values['data']['discharge_start_time4_point_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_DISCHARGE_START_TIME4_COMMAND_ID')
        discharge_start_time4_point_id = new_values['data']['discharge_start_time4_point_id']

        if 'discharge_end_time4_point_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['discharge_end_time4_point_id'], int) or \
                new_values['data']['discharge_end_time4_point_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_DISCHARGE_END_TIME4_COMMAND_ID')
        discharge_end_time4_point_id = new_values['data']['discharge_end_time4_point_id']

        if 'charge_start_time1_command_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['charge_start_time1_command_id'], int) or \
                new_values['data']['charge_start_time1_command_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_CHARGE_START_TIME1_POINT_ID')
        charge_start_time1_command_id = new_values['data']['charge_start_time1_command_id']

        if 'charge_end_time1_command_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['charge_end_time1_command_id'], int) or \
                new_values['data']['charge_end_time1_command_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_CHARGE_END_TIME1_POINT_ID')
        charge_end_time1_command_id = new_values['data']['charge_end_time1_command_id']

        if 'charge_start_time2_command_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['charge_start_time2_command_id'], int) or \
                new_values['data']['charge_start_time2_command_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_CHARGE_START_TIME2_POINT_ID')
        charge_start_time2_command_id = new_values['data']['charge_start_time2_command_id']

        if 'charge_end_time2_command_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['charge_end_time2_command_id'], int) or \
                new_values['data']['charge_end_time2_command_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_CHARGE_END_TIME2_POINT_ID')
        charge_end_time2_command_id = new_values['data']['charge_end_time2_command_id']

        if 'charge_start_time3_command_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['charge_start_time3_command_id'], int) or \
                new_values['data']['charge_start_time3_command_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_CHARGE_START_TIME3_POINT_ID')
        charge_start_time3_command_id = new_values['data']['charge_start_time3_command_id']

        if 'charge_end_time3_command_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['charge_end_time3_command_id'], int) or \
                new_values['data']['charge_end_time3_command_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_CHARGE_END_TIME3_POINT_ID')
        charge_end_time3_command_id = new_values['data']['charge_end_time3_command_id']

        if 'charge_start_time4_command_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['charge_start_time4_command_id'], int) or \
                new_values['data']['charge_start_time4_command_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_CHARGE_START_TIME4_POINT_ID')
        charge_start_time4_command_id = new_values['data']['charge_start_time4_command_id']

        if 'charge_end_time4_command_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['charge_end_time4_command_id'], int) or \
                new_values['data']['charge_end_time4_command_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_CHARGE_END_TIME4_POINT_ID')
        charge_end_time4_command_id = new_values['data']['charge_end_time4_command_id']

        if 'discharge_start_time1_command_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['discharge_start_time1_command_id'], int) or \
                new_values['data']['discharge_start_time1_command_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_DISCHARGE_START_TIME1_POINT_ID')
        discharge_start_time1_command_id = new_values['data']['discharge_start_time1_command_id']

        if 'discharge_end_time1_command_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['discharge_end_time1_command_id'], int) or \
                new_values['data']['discharge_end_time1_command_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_DISCHARGE_END_TIME1_POINT_ID')
        discharge_end_time1_command_id = new_values['data']['discharge_end_time1_command_id']

        if 'discharge_start_time2_command_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['discharge_start_time2_command_id'], int) or \
                new_values['data']['discharge_start_time2_command_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_DISCHARGE_START_TIME2_POINT_ID')
        discharge_start_time2_command_id = new_values['data']['discharge_start_time2_command_id']

        if 'discharge_end_time2_command_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['discharge_end_time2_command_id'], int) or \
                new_values['data']['discharge_end_time2_command_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_DISCHARGE_END_TIME2_POINT_ID')
        discharge_end_time2_command_id = new_values['data']['discharge_end_time2_command_id']

        if 'discharge_start_time3_command_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['discharge_start_time3_command_id'], int) or \
                new_values['data']['discharge_start_time3_command_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_DISCHARGE_START_TIME3_POINT_ID')
        discharge_start_time3_command_id = new_values['data']['discharge_start_time3_command_id']

        if 'discharge_end_time3_command_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['discharge_end_time3_command_id'], int) or \
                new_values['data']['discharge_end_time3_command_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_DISCHARGE_END_TIME3_POINT_ID')
        discharge_end_time3_command_id = new_values['data']['discharge_end_time3_command_id']

        if 'discharge_start_time4_command_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['discharge_start_time4_command_id'], int) or \
                new_values['data']['discharge_start_time4_command_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_DISCHARGE_START_TIME4_POINT_ID')
        discharge_start_time4_command_id = new_values['data']['discharge_start_time4_command_id']

        if 'discharge_end_time4_command_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['discharge_end_time4_command_id'], int) or \
                new_values['data']['discharge_end_time4_command_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_DISCHARGE_END_TIME4_POINT_ID')
        discharge_end_time4_command_id = new_values['data']['discharge_end_time4_command_id']

        cnx = mysql.connector.connect(**config.myems_system_db)
        cursor = cnx.cursor()

        cursor.execute(" SELECT name "
                       " FROM tbl_energy_storage_containers "
                       " WHERE id = %s ", (id_,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.ENERGY_STORAGE_CONTAINER_NOT_FOUND')

        cursor.execute(" SELECT name "
                       " FROM tbl_energy_storage_containers_power_conversion_systems "
                       " WHERE id = %s ", (pid,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.ENERGY_STORAGE_CONTAINER_POWER_CONVERSION_SYSTEM_NOT_FOUND')

        cursor.execute(" SELECT name "
                       " FROM tbl_energy_storage_containers_power_conversion_systems "
                       " WHERE energy_storage_container_id = %s AND name = %s AND id != %s ",
                       (id_, name, pid))
        if cursor.fetchone() is not None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.ENERGY_STORAGE_CONTAINER_PCS_NAME_IS_ALREADY_IN_USE')

        update_row = (" UPDATE tbl_energy_storage_containers_power_conversion_systems "
                      " SET name = %s, energy_storage_container_id = %s, run_state_point_id = %s, capacity = %s, "
                      "     charge_start_time1_point_id = %s, charge_end_time1_point_id = %s, "
                      "     charge_start_time2_point_id = %s, charge_end_time2_point_id = %s, "
                      "     charge_start_time3_point_id = %s, charge_end_time3_point_id = %s, "
                      "     charge_start_time4_point_id = %s, charge_end_time4_point_id = %s, "
                      "     discharge_start_time1_point_id = %s, discharge_end_time1_point_id = %s, "
                      "     discharge_start_time2_point_id = %s, discharge_end_time2_point_id = %s, "
                      "     discharge_start_time3_point_id = %s, discharge_end_time3_point_id = %s, "
                      "     discharge_start_time4_point_id = %s, discharge_end_time4_point_id = %s, "
                      "     charge_start_time1_command_id = %s, charge_end_time1_command_id = %s, "
                      "     charge_start_time2_command_id = %s, charge_end_time2_command_id = %s, "
                      "     charge_start_time3_command_id = %s, charge_end_time3_command_id = %s, "
                      "     charge_start_time4_command_id = %s, charge_end_time4_command_id = %s, "
                      "     discharge_start_time1_command_id = %s, discharge_end_time1_command_id = %s, "
                      "     discharge_start_time2_command_id = %s, discharge_end_time2_command_id = %s, "
                      "     discharge_start_time3_command_id = %s, discharge_end_time3_command_id = %s, "
                      "     discharge_start_time4_command_id = %s, discharge_end_time4_command_id = %s "
                      " WHERE id = %s ")
        cursor.execute(update_row, (name,
                                    id_,
                                    run_state_point_id,
                                    capacity,
                                    charge_start_time1_point_id,
                                    charge_end_time1_point_id,
                                    charge_start_time2_point_id,
                                    charge_end_time2_point_id,
                                    charge_start_time3_point_id,
                                    charge_end_time3_point_id,
                                    charge_start_time4_point_id,
                                    charge_end_time4_point_id,
                                    discharge_start_time1_point_id,
                                    discharge_end_time1_point_id,
                                    discharge_start_time2_point_id,
                                    discharge_end_time2_point_id,
                                    discharge_start_time3_point_id,
                                    discharge_end_time3_point_id,
                                    discharge_start_time4_point_id,
                                    discharge_end_time4_point_id,
                                    charge_start_time1_command_id,
                                    charge_end_time1_command_id,
                                    charge_start_time2_command_id,
                                    charge_end_time2_command_id,
                                    charge_start_time3_command_id,
                                    charge_end_time3_command_id,
                                    charge_start_time4_command_id,
                                    charge_end_time4_command_id,
                                    discharge_start_time1_command_id,
                                    discharge_end_time1_command_id,
                                    discharge_start_time2_command_id,
                                    discharge_end_time2_command_id,
                                    discharge_start_time3_command_id,
                                    discharge_end_time3_command_id,
                                    discharge_start_time4_command_id,
                                    discharge_end_time4_command_id,
                                    pid))
        cnx.commit()

        cursor.close()
        cnx.close()

        resp.status = falcon.HTTP_200

