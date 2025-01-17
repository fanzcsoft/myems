import React, { Fragment } from 'react';
import BootstrapTable from 'react-bootstrap-table-next';
import FalconCardHeader from '../../common/FalconCardHeader';
import { Card, CardBody, Row, Col } from 'reactstrap';
import { withTranslation } from 'react-i18next';


const defaultSorted = [{
  dataField: 'name',
  order: 'asc'
}];

const WorkingDaysConsumptionTable = ({ data, columns, t }) => {
  return (
    <Fragment>
      <Card>
        <FalconCardHeader title={ t('Working Days') + ' & ' + t('Non Working Days')} className="bg-light" titleClass="text-lightSlateGray mb-0" />
        <CardBody>
          <Row>
            <Col>
              <BootstrapTable
                bootstrap4
                keyField="name"
                data={data}
                columns={columns}
                defaultSorted={defaultSorted}
              />
            </Col>
          </Row>
        </CardBody>
      </Card>
    </Fragment>
  );
};

export default withTranslation()(WorkingDaysConsumptionTable);
