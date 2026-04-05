# Azure Foundry Fabric Chatbot 🤖

A production-ready **Streamlit chatbot** that invokes an **Azure AI Foundry Agent** with **Microsoft Fabric Data Agent** tool, enabling natural language queries over enterprise data in **Microsoft Fabric** (Lakehouses, Warehouses, Power BI Semantic Models, and KQL Databases).

> **Why Device Code Flow?** The Fabric Data Agent uses **identity passthrough (On-Behalf-Of)** authorization. This means the agent runs queries using the signed-in user's identity — Service Principal authentication is **not supported** by the Fabric Data Agent tool. This app uses MSAL Device Code Flow to acquire a user token that carries the necessary identity for OBO.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-red)
![Azure AI Foundry](https://img.shields.io/badge/Azure_AI_Foundry-Agent_Runtime-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## Architecture

```
┌──────────────┐     MSAL Device Code      ┌────────────────────────┐
│              │  ◄──────────────────────►  │  Microsoft Entra ID    │
│   End User   │     (user identity)        │  (Authentication)      │
│              │                            └────────────────────────┘
└──────┬───────┘
       │ Chat messages
       ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Streamlit App (app.py)                                              │
│  ┌────────────────┐  ┌──────────────────┐  ┌──────────────────────┐ │
│  │ MSAL Auth       │  │ Chat UI          │  │ Session Management   │ │
│  │ (Device Code)   │  │ (Multi-turn)     │  │ (Sign-in/out)        │ │
│  └────────┬───────┘  └────────┬─────────┘  └──────────────────────┘ │
└───────────┼───────────────────┼──────────────────────────────────────┘
            │ User token        │ agent_reference
            ▼                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Azure AI Foundry Project                                            │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  AIProjectClient  ──►  OpenAI Responses API                   │  │
│  │                        (responses.create with agent_reference) │  │
│  └────────────────────────────────┬───────────────────────────────┘  │
│                                   │                                  │
│  ┌────────────────────────────────▼───────────────────────────────┐  │
│  │  Foundry Prompt Agent (e.g., Fabric-Executive-Agent)          │  │
│  │  ├── Model: gpt-4.1 (orchestration + response generation)    │  │
│  │  └── Tool: fabric_dataagent_preview (OBO identity passthrough)│  │
│  └────────────────────────────────┬───────────────────────────────┘  │
└───────────────────────────────────┼──────────────────────────────────┘
                                    │ On-Behalf-Of (user identity)
                                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Microsoft Fabric                                                    │
│  ┌──────────────┐ ┌──────────────┐ ┌────────┐ ┌──────────────────┐  │
│  │  Lakehouse   │ │  Warehouse   │ │  KQL   │ │ Power BI Semantic│  │
│  │  (Delta/SQL) │ │  (T-SQL)     │ │  DB    │ │ Model (DAX)      │  │
│  └──────────────┘ └──────────────┘ └────────┘ └──────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Features

- 🔐 **Secure User Authentication** — MSAL Device Code Flow with Microsoft Entra ID
- 🤖 **Foundry Agent Invocation** — Uses OpenAI Responses API with `agent_reference`
- 💬 **Multi-turn Conversations** — Maintains context via `previous_response_id`
- 📊 **Enterprise Data Access** — Queries Fabric Lakehouses, Warehouses, PBI Models, and KQL DBs
- 🔄 **Session Management** — New conversation, sign-out, and user identity display
- 🛡️ **Identity Passthrough (OBO)** — Fabric queries run under the signed-in user's permissions

---

## Prerequisites

### Azure Resources

| Resource | Requirement |
|---|---|
| **Azure AI Foundry Project** | A project with a deployed Prompt Agent using the Fabric Data Agent tool |
| **Azure AI Services Resource** | The underlying Cognitive Services account hosting the Foundry project |
| **Microsoft Fabric** | A published Fabric Data Agent connected to your data sources |
| **App Registration** | An Entra ID app with public client flows enabled |

### Fabric Data Agent Setup

1. **Create and publish** a [Fabric Data Agent](https://go.microsoft.com/fwlink/?linkid=2312910) in Microsoft Fabric
2. From the Fabric Data Agent URL, copy the `workspace_id` and `artifact_id`:
   ```
   .../groups/<workspace_id>/aiskills/<artifact_id>...
   ```
3. In the **Foundry Portal** → your project → **Management Center** → **Connected Resources**:
   - Create a connection of type **Microsoft Fabric**
   - Enter the `workspace_id` and `artifact_id`
   - Save and copy the connection **ID**

### User Permissions

| Scope | Required Role / Permission |
|---|---|
| Azure AI Foundry resource | `Azure AI User` (RBAC) |
| Fabric Data Agent | At least `READ` access |
| Power BI Semantic Model | `Build` permission (Read alone is not sufficient) |
| Lakehouse | Read on the lakehouse item |
| Warehouse | `SELECT` on relevant tables |
| KQL Database | Reader role |

> ⚠️ **Important:** The Fabric Data Agent and Foundry project must be in the **same tenant**.

---

## Step-by-Step Setup

### Step 1: Create App Registration

```bash
# Create a new app registration (or use an existing one)
az ad app create --display-name "azure-foundry-fabric-chatbot"

# Note the appId from the output, then enable public client flows
az ad app update --id <app-id> --is-fallback-public-client true
```

### Step 2: Assign RBAC Roles

```bash
# Assign Azure AI User role to the app on your Foundry resource
az role assignment create \
  --role "Azure AI User" \
  --assignee "<app-id>" \
  --scope "/subscriptions/<sub-id>/resourceGroups/<rg>/providers/Microsoft.CognitiveServices/accounts/<foundry-resource>"

# Also assign the role to each user who will use the chatbot
az role assignment create \
  --role "Azure AI User" \
  --assignee "<user-email>" \
  --scope "/subscriptions/<sub-id>/resourceGroups/<rg>/providers/Microsoft.CognitiveServices/accounts/<foundry-resource>"
```

### Step 3: Create and Configure the Foundry Agent

1. Open your **Azure AI Foundry** project in the portal
2. Create a new **Prompt Agent** with:
   - **Model:** `gpt-4.1` (or your preferred model — used for orchestration only)
   - **Instructions:** Include guidance like *"Use the Fabric tool for data queries"*
   - **Tools:** Add the **Microsoft Fabric** tool with your Fabric connection
3. **Test** the agent in the Foundry playground to verify it works
4. Note down the **Agent Name** and **Version** from the agent details

### Step 4: Clone and Configure the App

```bash
git clone https://github.com/nikunj11itdhm/azure-foundry-fabric-chatbot.git
cd azure-foundry-fabric-chatbot
pip install -r requirements.txt
```

Create your `.env` file:

```bash
cp .env.example .env
```

Edit `.env` with your values:

```env
AZURE_TENANT_ID=<your-entra-tenant-id>
AZURE_CLIENT_ID=<your-app-registration-client-id>
PROJECT_ENDPOINT=https://<resource>.services.ai.azure.com/api/projects/<project>
AGENT_NAME=<your-foundry-agent-name>
AGENT_VERSION=<agent-version-number>
```

### Step 5: Find Your Configuration Values

| Value | Where to Find It |
|---|---|
| `AZURE_TENANT_ID` | Azure Portal → Microsoft Entra ID → Overview → Tenant ID |
| `AZURE_CLIENT_ID` | Azure Portal → App Registrations → Your app → Application (client) ID |
| `PROJECT_ENDPOINT` | Foundry Portal → Project → Overview → Project endpoint |
| `AGENT_NAME` | Foundry Portal → Agents → Your agent → Name |
| `AGENT_VERSION` | Foundry Portal → Agents → Your agent → Version number |

### Step 6: Run the App

```bash
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

---

## Authentication Flow (Detailed)

```
┌─────────┐          ┌────────────┐          ┌──────────────┐
│  User   │          │ Streamlit  │          │  Entra ID    │
│ Browser │          │   App      │          │  (Microsoft) │
└────┬────┘          └─────┬──────┘          └──────┬───────┘
     │  Click Sign In      │                        │
     │────────────────────►│                        │
     │                     │  Initiate Device Flow  │
     │                     │───────────────────────►│
     │                     │  {user_code, url}      │
     │                     │◄───────────────────────│
     │  Show code + URL    │                        │
     │◄───────────────────│                        │
     │                     │                        │
     │  User visits URL    │                        │
     │  & enters code      │                        │
     │─────────────────────────────────────────────►│
     │                     │                        │
     │                     │  Poll for token        │
     │                     │───────────────────────►│
     │                     │  {access_token}        │
     │                     │◄───────────────────────│
     │                     │                        │
     │  Chat UI enabled    │                        │
     │◄───────────────────│                        │
     │                     │                        │
     │  Send message       │                        │
     │────────────────────►│                        │
     │                     │  responses.create()    │
     │                     │  (user token + agent_  │
     │                     │   reference)           │
     │                     │───────────────────────►│ Foundry
     │                     │  Agent response        │
     │                     │◄───────────────────────│
     │  Display response   │                        │
     │◄───────────────────│                        │
```

### Why Not Service Principal?

The Fabric Data Agent uses **On-Behalf-Of (OBO)** authorization:
- The agent generates NL2SQL queries and runs them against Fabric data sources
- These queries execute under the **signed-in user's identity**
- This ensures row-level security (RLS), object-level security, and workspace permissions are enforced
- A Service Principal has no user context to pass through, so the OBO flow fails

### Why Not OAuth2 Authorization Code Flow?

Streamlit's architecture makes browser-redirect OAuth flows unreliable:
- The OAuth redirect creates a **new Streamlit session** (new WebSocket connection)
- Tokens stored in `st.session_state` are lost when the URL changes
- Device Code Flow avoids this entirely — no redirects, the token is acquired within the same session

---

## How It Works (Technical Details)

### Agent Invocation

The app uses the **Azure AI Projects SDK v2+** with the OpenAI Responses API:

```python
from azure.ai.projects import AIProjectClient

project_client = AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=credential)
openai_client = project_client.get_openai_client()

response = openai_client.responses.create(
    input=[{"role": "user", "content": "Show me sales data"}],
    extra_body={
        "agent_reference": {
            "name": "Fabric-Executive-Agent",
            "version": "2",
            "type": "agent_reference",
        }
    },
)
print(response.output_text)
```

### Key SDK Patterns

| Pattern | Implementation |
|---|---|
| **Authentication** | MSAL `PublicClientApplication` with Device Code Flow |
| **Client creation** | `AIProjectClient` → `get_openai_client()` |
| **Agent invocation** | `responses.create()` with `agent_reference` in `extra_body` |
| **Multi-turn** | Pass `previous_response_id` from prior response |
| **Token wrapping** | Custom `TokenCredential` class wrapping MSAL access token |

### API Details

| Property | Value |
|---|---|
| SDK | `azure-ai-projects >= 2.0.0` |
| API endpoint | `{project_endpoint}/openai/responses` |
| API version | Managed by SDK (v2+ required) |
| Auth scope | `https://ai.azure.com/user_impersonation` |
| Agent routing | `agent_reference` in `extra_body` (not `model` parameter) |

---

## Project Structure

```
azure-foundry-fabric-chatbot/
├── app.py               # Streamlit chatbot application
│                        #   - MSAL Device Code authentication
│                        #   - Foundry agent invocation via OpenAI Responses API
│                        #   - Multi-turn chat with session management
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variable template
├── .gitignore           # Excludes .env, __pycache__, .venv
├── LICENSE              # MIT License
└── README.md            # This file
```

---

## Troubleshooting

### Common Errors

| Error | Cause | Solution |
|---|---|---|
| `tool_user_error: Create assistant failed` | SPN authentication used with Fabric Data Agent | Switch to user identity auth (Device Code Flow). Fabric Data Agent requires OBO. |
| `Unknown parameter: 'agent'` | Using old SDK (`azure-ai-projects < 2.0`) | Upgrade: `pip install azure-ai-projects>=2.0.0`. Use `agent_reference` not `agent`. |
| `DeploymentNotFound` | Passing `model` parameter in `responses.create()` | Remove the `model` parameter. `agent_reference` handles model routing internally. |
| `Unauthorized (401)` | Wrong token audience | Use scope `https://ai.azure.com/user_impersonation` for device code flow. |
| `API version not supported` | Using wrong API version | Ensure `azure-ai-projects >= 2.0.0` — the SDK manages the correct API version. |
| Device code expired | User didn't complete sign-in within the timeout | Refresh the page and click "Sign in with Microsoft" again. |
| `AADSTS700016: Application not found` | Wrong `AZURE_CLIENT_ID` | Verify the Client ID in Azure Portal → App Registrations. |
| `AADSTS7000218: request body must contain client_assertion` | Public client flows not enabled | Run: `az ad app update --id <app-id> --is-fallback-public-client true` |

### Verifying Your Setup

```bash
# 1. Check RBAC assignments on Foundry resource
az role assignment list \
  --scope "/subscriptions/<sub-id>/resourceGroups/<rg>/providers/Microsoft.CognitiveServices/accounts/<resource>" \
  --query "[?contains(roleDefinitionName, 'Azure AI')].{Principal:principalName, Role:roleDefinitionName}" \
  --output table

# 2. Verify app registration settings
az ad app show --id <app-id> --query "{AppId:appId, PublicClient:isFallbackPublicClient}" --output table

# 3. Test token acquisition
az account get-access-token --scope https://ai.azure.com/.default --query "{token:accessToken}" --output table

# 4. Verify agent exists (requires a valid token)
curl -s -H "Authorization: Bearer <token>" \
  "https://<resource>.services.ai.azure.com/api/projects/<project>/agents/<agent-name>?api-version=2025-05-15-preview" | python -m json.tool
```

---

## Security Considerations

- 🔒 **Never commit `.env`** — it's excluded via `.gitignore`
- 🔒 **Token lifetime** — Device code tokens expire (typically 1 hour). Users must re-authenticate after expiry.
- 🔒 **Least privilege** — Assign only `Azure AI User` role, not Owner or Contributor
- 🔒 **Data access** — Fabric queries run under the user's identity, enforcing existing RLS/OLS policies
- 🔒 **No secrets stored** — Device Code Flow uses a public client (no client secret required)

---

## References

- [Azure AI Foundry Agents Documentation](https://learn.microsoft.com/azure/ai-foundry/agents/)
- [Fabric Data Agent with Foundry — Setup & Troubleshooting](https://aka.ms/foundryfabrictroubleshooting)
- [Azure AI Projects Python SDK (v2+)](https://pypi.org/project/azure-ai-projects/)
- [MSAL Python — Device Code Flow](https://learn.microsoft.com/entra/msal/python/)
- [Fabric Data Agent Permissions](https://learn.microsoft.com/fabric/data-science/data-agent-sharing)
- [Azure RBAC for AI Foundry](https://learn.microsoft.com/azure/ai-foundry/concepts/rbac-ai-foundry)
- [Foundry Agent Samples (GitHub)](https://github.com/azure-ai-foundry/foundry-samples)

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes (`git commit -m 'Add my feature'`)
4. Push to the branch (`git push origin feature/my-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
