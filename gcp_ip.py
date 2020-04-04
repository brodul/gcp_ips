from pprint import pprint

from googleapiclient import discovery, errors
from google.oauth2 import service_account


class GcpIPFetcher(object):
    service = None
    compute = None

    def __init__(self, service_account_filename):
        credentials = service_account.Credentials.from_service_account_file(
            filename=service_account_filename
        )

        self.service = discovery.build(
            "cloudresourcemanager", "v1", credentials=credentials
        )
        self.compute = discovery.build("compute", "v1", credentials=credentials)

    def get_projects(self):
        request = self.service.projects().list()
        while request is not None:
            response = request.execute()

            for project in response.get("projects", []):
                # pprint(project)
                if project["lifecycleState"] != "ACTIVE":
                    continue
                yield project["projectId"]

            request = self.service.projects().list_next(
                previous_request=request, previous_response=response
            )

    def get_project_addresses(self, project_id):
        request = self.compute.addresses().aggregatedList(project=project_id)
        while request is not None:
            try:
                response = request.execute()
            except errors.HttpError as e:
                # Compute API not configured for project
                if '"reason": "accessNotConfigured"' in e.args[1].decode("utf-8"):
                    break
                raise

            for name, addresses_scoped_list in response["items"].items():
                # there can be a warning with the message that there is no address in region
                if "addresses" not in addresses_scoped_list:
                    continue
                # pprint((name, addresses_scoped_list))
                for address in addresses_scoped_list["addresses"]:
                    yield (
                        address["address"],
                        address["addressType"],
                        address["status"],
                    )

            request = self.compute.addresses().aggregatedList_next(
                previous_request=request, previous_response=response
            )

    def get_addresses(self):
        for project_id in self.get_projects():
            yield self.get_project_addresses(project_id)

    def print_addresses(self):
        for project_addresses in self.get_addresses():
            for address in project_addresses:
                print(",".join(address))


if __name__ == "__main__":
    import sys
    GcpIPFetcher(sys.argv[1]).print_addresses()
