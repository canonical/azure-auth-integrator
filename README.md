# Azure auth integrator
[![Charmhub](https://charmhub.io/azure-auth-integrator/badge.svg)](https://charmhub.io/azure-auth-integrator)
[![Release](https://github.com/canonical/azure-auth-integrator/actions/workflows/release.yaml/badge.svg)](https://github.com/canonical/azure-auth-integrator/actions/workflows/release.yaml)
[![Tests](https://github.com/canonical/azure-auth-integrator/actions/workflows/ci.yaml/badge.svg)](https://github.com/canonical/azure-auth-integrator/actions/workflows/ci.yaml)

## Description

`azure-auth-integrator` is an integrator charm responsible for relaying the credentials required to interact with Microsoft [Entra ID](https://learn.microsoft.com/en-us/entra/fundamentals/what-is-entra) using [Service principals](https://learn.microsoft.com/en-us/entra/identity-platform/app-objects-and-service-principals?tabs=browser).

## Basic usage

First, deploy `azure-auth-integrator` by running:
```shell
juju deploy azure-auth-integrator --channel 1/edge
```

Then, configure the charm with your Azure credentials:
```shell
juju config azure-auth-integrator subscription-id=<your-subscription-id> tenant-id=<your-tenant-id>
```

Requirer charms also need the `client-id` and `client-secret` which uniquely identify your app. To pass this sensitive information to the charm, add a Juju secret with these values, and grant access to `azure-auth-integrator`:
```shell
juju add-secret my-secret client-id=<your-client-id> client-secret=<your-client-password>
juju grant-secret my-secret azure-auth-integrator
```

Use the URI of the added secret in the previous step as the value for the `credentials` configuration option:
```
juju config azure-auth-integrator credentials=<secret-uri>
```

After deploying the requirer charm, integrate it with `azure-auth-integrator` by running:
```shell
juju integrate azure-auth-integrator <requirer-charm>
```

The requirer charm should have access to all credentials needed to access your Azure resources.

## Community and support

`azure-auth-integrator` is an open-source project that welcomes community contributions, suggestions,
fixes and constructive feedback.

- Report [issues](https://github.com/canonical/azure-auth-integrator/issues).
- [Contact us on Matrix](https://matrix.to/#/#charmhub-data-platform:ubuntu.com).
- Explore [Canonical Data & AI solutions](https://canonical.com/data).

## License and copyright

`azure-auth-integrator` is free software, distributed under the Apache Software License, version 2.0. See [LICENSE](https://www.apache.org/licenses/LICENSE-2.0) for more information.
