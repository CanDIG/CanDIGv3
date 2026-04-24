# CanDIG v3

- - -

## Overview

The CanDIG v3 project is a collection of heterogeneous services designed to work together to facilitate end to end
dataflow for health care data (phenotypic and genomic). The `v3 ` version of the project uses a OMOP-based back
database for structured data, allowing CanDIG to be used by a wide variety of projects sharing and analyzing 
health care data. 

## Branches

The default `develop` branch is for developers. It undergoes nightly builds and integration testing, so should generally be deployable. 

**Not Yet Implemented** The `stable` branch is the latest stable release and is the one that you should use for production deployments. 

## Installation

CanDIG uses a make-based deployment process, with services containerized in Docker. To deploy CanDIGv3, follow the installation guides on our [documentation website](https://candig.github.io/CanDIGv3/):

* [CanDIG Local Deployment Guide](https://candig.github.io/CanDIGv3/deployment/local/)
* [CanDIG Production Deployment Guide](https://candig.github.io/CanDIGv3/deployment/production/)

See [Interact using Make](https://candig.github.io/CanDIGv3/deployment/interact-with-the-stack/) for a guide to additional options or view all Makefile options with `make help`.

## Project Structure

```plaintext
CanDIGv3/
 ├── .env                          - global variables
 ├── Makefile                      - functions for repeatable testing/deployment (Docker/Kubernetes)
 ├── tox.ini                       - functions for repeatable testing/deployment (Python Venv/Screen)
 ├── bin/                          - local binaries directory
 ├── docs/                         - documentation, installation instructions
 ├── etc/                          - contains misc files/config/scripts
 │    ├── docker/                  - docker configurations
 │    ├── env/                     - sample .env file
 │    ├── ssl/                     - ssl root-ca/site configs and certs
 |    ├── tests/                   - integration and performance tests (under development)
 │    ├── venv/                    - dependency files for virtualenvs (conda, pip, etc.)
 │    └── yml/                     - various yaml based configs (toil, traefik, etc.)
 ├── lib/                          - contains modules of services/apps
 └── tmp/                          - contains temporary files used for runtime functionality
      ├── configs/                 - config files that are added to services post-deployment
      ├── data/                    - local data for running services
      ├── federation/              - federation configuration files
      ├── tyk/                     - tyk configuration files
      ├── vault/                   - vault keys
      └── secrets/                 - directory to store randomly generated secrets for service deployment
```

## List of Services and Components

The following table lists the individual repos for each service and helper library developed by the CanDIG team that contribute to the CanDIGv3 stack.

| Service/Component Name    | Source                                                                | Description                       |
|---------------------------|-----------------------------------------------------------------------|------------------------------|
| authx                     | [`candigv2-authx`](https://github.com/CanDIG/candigv2-authx)          | Library to facilitate interacting with AuthZ/AuthN services, Keycloak, Tyk, Opa, Vault & Access to minIO S3 objects |
| CanDIG Data Portal        | [`candig-data-portal`](https://github.com/CanDIG/candig-data-portal)  | Front-end User interface for CanDIG Services |
| Federation Service        | [`federation-service`](https://github.com/CanDIG/federation_service)  | Distributes requests across each federated node of the distributed infrastructure   |
| HTSGet                    | [`htsget_app`](https://github.com/CanDIG/htsget_app)                  | Implementation of GA4GH htsget API for retrieval of genomic data |
| DRS                       | [`DRS`](https://github.com/CanDIG/drs-service)                                                             | Implementation of GA4GH Data Repository Service API for storage and retrieval of files and associated metadata. |
| RNAGet                    | [`RNAGet`](https://github.com/bento-platform/takuan)                                                                  | CanDIGv3 incorporates C3G's RNAGet compliant transcriptomics data service `Takuan` |
| CanDIG API                | [`candig-api`](https://github.com/CanDIG/candig-api)                       | API access to CanDIG databases and services. Implements a GA4GH-compliant Beacon API for searching data, phenopackets for export and clinical data stored in an OMOP database.  |
| CanDIG OPA                | [`candig-opa`](https://github.com/CanDIG/candig-opa)                  | Manages role-based access policies   |

As well as in-house developed services, the CanDIG stack relies on external software which is configured to work within the stack, configurations are found in the [`/lib`](/lib) folder for each software, these include:

| Service/Component Name                  | Role                                 |
|-----------------------------------------|--------------------------------------|
| [Keycloak](https://www.keycloak.org/)   | Authentication management            |
| [minio](https://min.io/)                | Object storage for genomic files     |
| [OPA](https://www.openpolicyagent.org/) | Manages role-based access policies   |
| [Tyk](https://tyk.io/)                  | API management and redirection       |
| [Vault](https://www.vaultproject.io/)   | Secret and password management       |

## Adding a new service

New services can be added under `lib` directory.  Please refer to the
[template for new services README](./lib/templates/README.md) for more details.
