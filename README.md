# Azure auth integrator
[![Charmhub](https://charmhub.io/azure-auth-integrator/badge.svg)](https://charmhub.io/azure-auth-integrator)
[![Release](https://github.com/canonical/azure-auth-integrator/actions/workflows/release.yaml/badge.svg)](https://github.com/canonical/azure-auth-integrator/actions/workflows/release.yaml)
[![Tests](https://github.com/canonical/azure-auth-integrator/actions/workflows/ci.yaml/badge.svg)](https://github.com/canonical/azure-auth-integrator/actions/workflows/ci.yaml)

## Description

`azure-auth-integrator` is an integrator charm responsible for relaying the credentials required to interact with Microsoft [Entra ID](https://learn.microsoft.com/en-us/entra/fundamentals/what-is-entra) using [Service principals](https://learn.microsoft.com/en-us/entra/identity-platform/app-objects-and-service-principals?tabs=browser).

## Get started

Deploy `azure-auth-integrator` by running:
```shell
juju deploy azure-auth-integrator --channel 1/edge
```

Now configure it with your Azure credentials:
```shell
juju config azure-auth-integrator subscription-id=<your-subscription-id> tenant-id=<your-tenant-id>
```

Requirer charms also need the `client-id` and `client-secret` keys which uniquely identify your app. To pass this sensitive information to the charm, add a Juju secret with these values, and grant access to `azure-auth-integrator` as follows:
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

The requirer charm should now have access to all credentials needed to access your Azure resources.


## Integrating your charm with `azure-auth-integrator`

Charmed applications can enable the integration with `azure-auth-integrator` over the `azure_service_principal` relation interface, allowing them to consume Azure Service Principal connection information over the Juju relation.

First, add a relation endpoint to the `requires` section of your charm's metadata:

```yaml
# metadata.yaml

requires:
  azure-service-principal-credentials:
    interface: azure_service_principal
```

`azure_service_principal` has a library released on Charmhub that can be pulled by updating the `charm-libs` section in `charmcraft.yaml`. Since `azure_services_principal` depends on version `v1` of the [data_interfaces](https://github.com/canonical/data-platform-libs/blob/ba0faad1bf8d52409aff80f96b4163935264bd40/lib/charms/data_platform_libs/v1/data_interfaces.py) charm lib, it also should be specified as a dependency:

```yaml
# charmcraft.yaml

charm-libs:
  - lib: azure_auth_integrator.azure_service_principal
    version: "0"
  - lib: data_platform_libs.data_interfaces
    version: "1"
```

And then run `charmcraft fetch-libs` to pull the library from Charmhub.

On the requirer side of the charm, instantiate an `AzureServicePrincipalRequirer` object:

```python
# charm.py

from charms.azure_auth_integrator.v0.azure_service_principal import (
    AzureServicePrincipalRequirer,
)

class RequirerCharm(CharmBase):
    """Requirer charm that relates to Azure auth integrator."""

    def __init__(self, *args):
        super().__init__(*args)

	    ...

        self.azure_service_principal_client = AzureServicePrincipalRequirer(self, relation_name="azure-service-prinicpal-credentials")
```


Using this instance of class `AzureServicePrincipalRequirer`, the requirer charm then needs to listen to custom events `service_principal_connection_info_changed` and `service_principal_info_gone` and handle them appropriately in the charm code.

- The event `service_principal_info_changed` is fired whenever `azure-auth-integrator` has written new data to the relation databag, which needs to be handled by the requirer charm by updating its state with the new Azure Service Principal connection information.
- The event `service_principal_info_gone` is fired when the relation with `azure-auth-integrator` is broken, which needs to be handled by the requirer charm by updating its state to not use the Azure Service principal connection information anymore.

```python
# charm.py

from charms.azure_auth_integrator.v0.azure_service_principal import (
    AzureServicePrincipalRequirer,
    ServicePrincipalInfoChangedEvent,
    ServicePrincipalInfoGoneEvent,
)

class RequirerCharm(CharmBase):
    def __init__(self, *args):
        super().__init__(*args)

	    self.azure_service_principal_client = AzureServicePrincipalRequirer(self, relation_name="azure-service-prinicpal-credentials")

        # Observe custom events
        self.framework.observe(
            self.azure_service_principal_client.on.service_principal_info_changed,
            self._on_service_principal_info_changed,
        )
        self.framework.observe(
            self.azure_service_principal_client.on.service_principal_info_gone,
            self._on_service_principal_info_gone,
        )


    def _on_service_principal_info_changed(self, event: ServicePrincipalInfoChangedEvent):
        # access and consume data from the provider
        connection_info = self.azure_service_principal_client.get_azure_service_principal_info()
        process_connection_info(connection_info)

    def _on_service_principal_info_gone(self, event: ServicePrincipalInfoGoneEvent):
        # notify charm code that credentials are removed
        process_connection_info(None)

```

The latest Azure Service Principal connection information shared by the `azure-auth-integrator` over the relation can be fetched using the utility method `get_azure_service_principal_info()` available in the `AzureServicePrincipalRequirer` instance, which returns a dictionary:

```python
	AzureServicePrincipalInfo = {
	    "subscription-id": str,
		"tenant-id": str,
		"client-id": str,
		"client-secret": str,
	}
```

Once the requirer charm is built and deployed, it can integrated with `azure-auth-integrator` by executing:

```shell
juju integrate azure-auth-integrator requirer-charm
```

## Security
Security issues in the `azure-auth-integrator` operator can be reported through [LaunchPad](https://wiki.ubuntu.com/DebuggingSecurity#How%20to%20File). Please do not file GitHub issues about security issues.


## Community and support

`azure-auth-integrator` is an open-source project that welcomes community contributions, suggestions,
fixes and constructive feedback.

- Report [issues](https://github.com/canonical/azure-auth-integrator/issues).
- [Contact us on Matrix](https://matrix.to/#/#charmhub-data-platform:ubuntu.com).
- Explore [Canonical Data & AI solutions](https://canonical.com/data).

## License and copyright

`azure-auth-integrator` is free software, distributed under the Apache Software License, version 2.0. See [LICENSE](https://www.apache.org/licenses/LICENSE-2.0) for more information.
