# Azure Foundry Fabric Chatbot 🤖

A Streamlit chatbot that invokes an **Azure AI Foundry Agent** with **Microsoft Fabric Data Agent** tool using the **OpenAI Responses API** with `agent_reference`.

> The Fabric Data Agent uses identity passthrough (On-Behalf-Of), so this app authenticates users via **MSAL Device Code Flow** to pass their identity through to Fabric.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-red)
![Azure AI Foundry](https://img.shields.io/badge/Azure_AI_Foundry-Agent_Runtime-green)

## Architecture

```
User ──▶ Streamlit App ──▶ Azure AI Foundry (OpenAI Responses API)
              │                        │
         MSAL Device Code        agent_reference
         (user identity)               │
                                 Foundry Agent
                                       │
                                 Fabric Data Agent (OBO)
                                       │
                                 Microsoft Fabric
                              (Lakehouse / Warehouse / PBI)
```

## Prerequisites

1. **Azure AI Foundry** project with a deployed **Prompt Agent** that uses the Fabric Data Agent tool
2. **App Registration** in Microsoft Entra ID with:
   - Public client flows enabled (`--is-fallback-public-client true`)
   - `Azure AI User` role on the Foundry resource
3. **Fabric Data Agent** published and connected to your Foundry project
4. Users need:
   - `Azure AI User` role on the Foundry resource
   - `READ` access to the Fabric Data Agent
   - Appropriate permissions on underlying Fabric data sources

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/nikunj11itdhm/azure-foundry-fabric-chatbot.git
cd azure-foundry-fabric-chatbot
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env with your values
```

| Variable | Description |
|---|---|
| `AZURE_TENANT_ID` | Microsoft Entra tenant ID |
| `AZURE_CLIENT_ID` | App registration (client) ID |
| `PROJECT_ENDPOINT` | Foundry project endpoint URL |
| `AGENT_NAME` | Name of your Foundry agent |
| `AGENT_VERSION` | Agent version number |

### 4. Run the app

```bash
streamlit run app.py
```

## Authentication Flow

This app uses **MSAL Device Code Flow** because the Fabric Data Agent requires **user identity (OBO)**. Service Principal authentication is **not supported** for Fabric Data Agent.

1. Click **"🔐 Sign in with Microsoft"**
2. Visit the URL shown and enter the device code
3. Sign in with your Microsoft account
4. The app receives your token and enables the chat

## How It Works

- Uses `azure-ai-projects` SDK v2+ to create an `AIProjectClient`
- Calls `project_client.get_openai_client()` to get an OpenAI-compatible client
- Invokes the Foundry agent via `openai_client.responses.create()` with `agent_reference`
- Supports multi-turn conversations via `previous_response_id`

## Key Files

| File | Description |
|---|---|
| `app.py` | Streamlit chatbot application |
| `requirements.txt` | Python dependencies |
| `.env.example` | Environment variable template |

## Troubleshooting

| Issue | Solution |
|---|---|
| `tool_user_error: Create assistant failed` | Fabric Data Agent doesn't support SPN — use user identity (device code flow) |
| `Unknown parameter: 'agent'` | Upgrade to `azure-ai-projects>=2.0.0` and use `agent_reference` (not `agent`) |
| `DeploymentNotFound` | Don't pass `model` parameter — `agent_reference` handles model routing |
| Device code expired | Refresh the page and click Sign In again |

## References

- [Azure AI Foundry Agents](https://learn.microsoft.com/azure/ai-foundry/agents/)
- [Fabric Data Agent with Foundry](https://aka.ms/foundryfabrictroubleshooting)
- [Azure AI Projects SDK](https://pypi.org/project/azure-ai-projects/)

## License

MIT
