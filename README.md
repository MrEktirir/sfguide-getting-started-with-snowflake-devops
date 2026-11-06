# Snowflake DevOps | Automated Data Pipeline CI/CD

An end-to-end Snowflake DevOps implementation demonstrating automated data pipeline deployments, Git-based version control, environment isolation, and CI/CD orchestration using GitHub Actions and Snowflake CLI.

## Project Overview

This project implements a Git-integrated data pipeline with separate development and production environments.

The pipeline processes aviation and weather-related data to generate analytical insights about flight punctuality, carbon emissions, temperature, and precipitation across selected destinations.

The implementation is based on the [Getting Started with Snowflake DevOps](https://quickstarts.snowflake.com/guide/getting_started_with_snowflake_devops/index.html) quickstart, extended with practical CI/CD troubleshooting and secure GitHub Actions configuration.

## Technology Stack

- **Data Platform:** Snowflake
- **Version Control:** Git and GitHub
- **CI/CD:** GitHub Actions
- **Command-Line Tools:** Snowflake CLI
- **Programming Languages:** SQL and Python
- **Data Processing:** Snowpark Python
- **Authentication:** JWT / RSA Key-Pair Authentication
- **Development Environment:** GitHub Codespaces

## Architecture

```text
GitHub Repository
       |
       +-- dev branch
       |      |
       |      v
       |   GitHub Actions
       |      |
       |      v
       |   QUICKSTART_DEV
       |      |
       |      +-- BRONZE
       |      +-- SILVER
       |      +-- GOLD
       |
       +-- main branch
              |
              v
           GitHub Actions
              |
              v
           QUICKSTART_PROD
              |
              +-- BRONZE
              +-- SILVER
              +-- GOLD
```

Snowflake Git integration retrieves the repository changes, while GitHub Actions executes the environment-specific deployment scripts.

## CI/CD Workflow

The automated deployment process performs the following operations:

1. Detects changes pushed to the `dev` or `main` branch.
2. Checks out the repository using GitHub Actions.
3. Configures RSA private-key authentication using GitHub Secrets.
4. Installs Snowflake CLI.
5. Creates the Snowflake CLI connection configuration at runtime.
6. Validates the Snowflake connection.
7. Fetches the latest changes through Snowflake Git integration.
8. Executes SQL and Snowpark Python deployment scripts.
9. Deploys the pipeline to the corresponding Snowflake environment.

### Branch-to-Environment Mapping

| Git Branch | Snowflake Database | Retention Time |
|---|---|---|
| `dev` | `QUICKSTART_DEV` | 0 days |
| `main` | `QUICKSTART_PROD` | 1 day |

## Pipeline Components

| Script | Responsibility |
|---|---|
| `01_deploy_environment.sql` | Environment and database object deployment |
| `03_harmonize_data.py` | Data harmonization using Snowpark Python |
| `04_orchestrate_jobs.sql` | Pipeline orchestration and scheduling |

## Analytical Output

The pipeline produces a destination-level analytical dataset in:

`QUICKSTART_PROD.GOLD.VACATION_SPOTS`

The dataset includes:

- City and airport identifiers
- CO₂ emissions per passenger
- Flight punctuality percentage
- Average air temperature
- Total precipitation

The production query was validated successfully with three destinations: New York (JFK), Los Angeles (LAX), and Houston (IAH).

## Security

The CI/CD workflow uses Snowflake JWT authentication with an RSA private key.

Sensitive credentials are supplied through GitHub Actions Secrets. The local Snowflake CLI configuration file is excluded from version control, and the CI/CD connection configuration is created dynamically during workflow execution.

## Implementation Challenges

During development, several integration issues were identified and resolved:

- Corrected environment variable naming for Snowpark Python execution.
- Implemented explicit Git branch-to-Snowflake environment mapping.
- Replaced repository-tracked CLI configuration with runtime configuration.
- Resolved Snowflake CLI default connection initialization.
- Configured the default database and schema for Git-based script execution.

## Validation

The following milestones were completed:

- Successful DEV deployment through GitHub Actions
- Successful PROD deployment through GitHub Actions
- Successful JWT authentication and Snowflake CLI connection
- Successful production data query
- Clean Git working tree after configuration changes

## Reference

[Snowflake Quickstart — Getting Started with Snowflake DevOps](https://quickstarts.snowflake.com/guide/getting_started_with_snowflake_devops/index.html)

## Author

[MrEktirir](https://github.com/MrEktirir)