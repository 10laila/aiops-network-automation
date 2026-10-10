# AIOps Network Automation

### Intelligent Network Configuration Automation using Temporal, Gemini, RAG and Ansible

An AIOps-based network automation project developed during an engineering internship at **Intelcia**.

The solution transforms network requests written in natural language into Ansible playbooks, using AI-assisted analysis, internal knowledge retrieval, human approval, automated execution and network configuration verification.

The objective is to improve the reliability, consistency and traceability of network configuration operations.

## Project Overview

Traditional network configuration processes often involve manually interpreting requests, consulting technical documentation, writing configuration commands and applying changes to network devices.

This project explores an intelligent automation approach that combines:

- **Natural Language Processing:** Interpret network requests written in everyday language.
- **Retrieval-Augmented Generation (RAG):** Consult network policies and technical documentation before generating configurations.
- **AI-Assisted Automation:** Analyze requests and generate structured Ansible playbooks.
- **Human-in-the-Loop Validation:** Require approval before executing changes.
- **Automated Network Verification:** Check the resulting configuration after execution.
- **Version Control:** Store successfully tested playbooks in Git.

## System Architecture

The solution follows a distributed architecture, with its main services deployed across separate virtual machines.

```text
                  Network Engineer
                         |
                         v
                    FastAPI API
                         |
                         v
                 Temporal Workflow
                         |
                         v
                AnythingLLM (RAG)
                         |
                         v
                    Gemini AI
                         |
                         v
               AI Response Validation
                         |
                         v
               Ansible Playbook Generation
                         |
                         v
                Playbook YAML Validation
                         |
                         v
                   Human Approval
                         |
                    Approved?
                     /      \
                   No        Yes
                   |          |
                  Stop        v
                       Ansible Execution
                              |
                              v
                       PNETLab Network
                              |
                              v
                    Configuration Verification
                              |
                        Verified?
                         /     \
                       No       Yes
                       |         |
                      Stop       v
                          Result Processing
                                |
                                v
                         Git / Gitea
```

**Note:** The intended integration with the existing TechTrack platform is part of the project's future scope. The current implementation uses FastAPI to submit requests and handle workflow interactions.

## Technology Stack

| Technology | Role |
|---|---|
| Python | Core implementation language |
| FastAPI | REST API for workflow requests and approval |
| Temporal | Durable workflow orchestration |
| AnythingLLM | RAG and technical knowledge retrieval |
| Gemini | AI-based request analysis and playbook generation |
| Ansible | Network configuration automation |
| Cisco IOS | Target network operating system |
| PNETLab | Virtual network testing environment |
| Git / Gitea | Version control for validated playbooks |
| SSH | Remote communication and device access |
| Ubuntu Server | Service hosting environment |
| VMware Workstation | Virtual machine infrastructure |

## How It Works

**1. Network request submission**

A network engineer submits a natural-language request through the FastAPI endpoint.

Example:

```text
Create VLAN 100 named RH on switch sw1.
```

**2. Knowledge retrieval**

AnythingLLM retrieves relevant technical information from the project's knowledge base, including network configuration rules and VLAN policies.

**3. AI analysis**

Gemini analyzes the request using the retrieved context and produces a structured response containing the proposed configuration, potential risks and validation requirements.

**4. Playbook generation**

The system generates an Ansible YAML playbook using the appropriate Cisco IOS modules.

**5. Technical and human validation**

The playbook undergoes YAML validation and requires explicit human approval before execution.

**6. Network execution**

Ansible executes the approved playbook against Cisco network devices in the PNETLab test environment.

**7. Automated verification**

The workflow executes a verification command, such as:

```bash
show vlan brief
```

It compares the observed network state with the expected configuration.

**8. Version control**

If execution and verification succeed, the generated playbook is committed to the Gitea repository.

## Project Structure

```text
aiops-network-automation/
├── activities/             # Supporting workflow activities
├── api/                    # FastAPI application
│   └── main.py
├── config/                 # Application configuration
├── playbooks/              # Generated Ansible playbooks
├── services/               # Integrations with external services
│   ├── ansible_service.py
│   ├── anythingllm_client.py
│   ├── gemini_client.py
│   └── git_service1.py
├── workflows/              # Temporal orchestration
│   ├── activities.py
│   ├── aiops_workflow.py
│   ├── client.py
│   └── worker.py
├── approve.py              # Approval utility
├── requirements.txt        # Python dependencies
└── README.md
```

The repository contains the Python application, workflow implementation, integration services and example playbooks. External platforms such as Temporal, AnythingLLM, PNETLab and Gitea require their own deployment and configuration.

## Example Use Case: VLAN Creation

**Input request**

```text
Create VLAN 100 named RH on sw1.
```

**Expected result**

```text
Device: sw1
VLAN ID: 100
VLAN Name: RH
Status: active
```

**Network verification**

```text
VLAN Name                             Status
---- -------------------------------- --------
1    default                          active
100  RH                               active
```

The workflow verifies that VLAN 100 is present with the expected name and active status before proceeding to version control.

## Running the Project

The application was developed and tested in a distributed virtualized environment.

### Prerequisites

- Python and the dependencies listed in `requirements.txt`
- Temporal Server
- An accessible AnythingLLM workspace
- Gemini API access
- Ansible with the required Cisco collections
- A reachable Cisco-compatible test environment
- Git and a configured Gitea repository
- SSH connectivity between the relevant services

### Install Python Dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Configure Services

Configure the service endpoints, API credentials, SSH access and Ansible inventory according to your deployment environment.

Keep credentials in environment variables or an appropriate secrets manager. Never commit API keys, passwords or private SSH keys.

### Start the Temporal Worker

With Temporal and the required services running:

```bash
python -m workflows.worker
```

### Start the API

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

The API can then be used to submit network requests and interact with the workflow, subject to the application's configured endpoints.

## Validation and Results

The project was tested using virtual Cisco network devices in PNETLab.

The implemented workflow demonstrates:

- Processing network requests expressed in natural language.
- Retrieving relevant network documentation through RAG.
- Generating Ansible playbooks using Gemini.
- Enforcing human approval before execution.
- Applying configurations to a virtual network environment.
- Verifying VLAN configurations using Cisco CLI commands.
- Versioning successfully verified playbooks in Gitea.

The solution is an experimental prototype intended for controlled network automation workflows, rather than a production-ready autonomous deployment platform.

## Future Improvements

- Integrate the workflow into the existing **TechTrack** platform.
- Extend automatic verification beyond VLAN operations.
- Improve error handling and recovery mechanisms.
- Add more network configuration scenarios and supported devices.
- Strengthen authentication, authorization and audit logging.
- Integrate with enterprise ticketing and change-management systems.

## Author

**Laila AIT ALI**

Engineering Student — Information and Communication Systems Engineering (ISIC)

ENSA El Jadida, Morocco

Developed during an engineering internship at **Intelcia**.

## Disclaimer

This repository is intended for educational and demonstration purposes. Network configuration changes should only be executed in authorized environments and reviewed before deployment to production infrastructure.
