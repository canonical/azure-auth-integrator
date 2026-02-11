#!/usr/bin/env bash

juju config azure-auth-integrator subscription-id=1 tenant-id=2
SECRET_ID=$(juju add-secret azure_secret client-id=clientid client-secret=clientsecret)
juju grant-secret azure_secret azure-auth-integrator
juju config azure-auth-integrator credentials=${SECRET_ID}
