#!/usr/bin/env bash

juju add-model kubeflow
juju deploy ./azure-auth-integrator_ubuntu@24.04-amd64.charm 

juju config azure-auth-integrator subscription-id=1 tenant-id=2
SECRET_ID=$(juju add-secret azure_secret client-id=clientid client-secret=clientsecret)
juju grant-secret azure_secret azure-auth-integrator
juju config azure-auth-integrator credentials=${SECRET_ID}

juju deploy ${HOME}/azure-auth-integrator/tests/integration/test-charm-azure-service-principal/test-charm-azure-service-principal_ubuntu@24.04-amd64.charm 
