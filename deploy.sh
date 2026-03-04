#!/usr/bin/env bash

juju add-model kubeflow
juju model-config logging-config="<root>=WARNING;unit=DEBUG"


juju deploy ~/can/azure-auth-integrator/azure-auth-integrator_ubuntu@24.04-amd64.charm 
juju config azure-auth-integrator subscription-id=hello tenant-id=world
SECRET_ID=$(juju add-secret azure-secret client-id=foo client-secret=bar)
juju grant-secret azure-secret azure-auth-integrator
juju config azure-auth-integrator credentials=${SECRET_ID}

juju deploy ~/can/azure-auth-integrator/tests/integration/test-charm-azure-service-principal/test-charm-azure-service-principal_ubuntu@24.04-amd64.charm

juju integrate azure-auth-integrator test-charm-azure-service-principal
