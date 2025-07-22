"""Azure service principal manager."""

from utils.logging import WithLogging

class AzureServicePrincipalManager(WithLogging):
    """Azure service principal manager class."""
    
    def __init__(self, relation_data):
        self.relation_data = relation_data

    def update(self, azure_service_principal_info):
        """Update the contents of the relation data bag."""
        if len(self.relation_data.relations) > 0 and azure_service_principal_info:
            for relation in self.relation_data.relations:
                self.relation_data.update_relation_data(
                    relation.id, azure_service_principal_info.to_dict()
                )
