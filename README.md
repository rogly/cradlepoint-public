# cradlepoint-public
This repository contains all of the relevant source files, and packages for quick, automated deployment of *Cradlepoint Automation*. The application makes use of a simple web front end hosted in Amazon S3, API Gateway, and several lambda functions to trigger updates to Cradlepoint (configuration), LogicMonitor (monitoring), and Smartsheet (asset tracking).

## Repository Structure
| Folder   | Description                                                                              |
|:--------:|------------------------------------------------------------------------------------------|
| source   | source files for making edits to package builds                                          |
| v1.0     | packaged files for upload to deployment repository                                       |
| build.py | python script to package deployments, passed a single value "VERSION" as system argument |

## Deployment Instructions
1. Upload contents of desired version (ex. v1.0) to a S3 repository
2. Create a new CloudFormation Stack
3. Paste the URL for {version}/cloudformation/template.yml from your S3 repository
4. Fill in the required CloudFormation Parameters
5. Deploy Stack