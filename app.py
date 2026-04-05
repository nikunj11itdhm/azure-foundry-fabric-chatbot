"""
Streamlit Chatbot — Azure AI Foundry Agent (Fabric-Executive-Agent)
Uses MSAL Device Code flow for user identity (required by Fabric Data Agent OBO).
"""

import os
import time
import threading
import streamlit as st
import msal
from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.core.credentials import AccessToken, TokenCredential

load_dotenv()

# ── Configuration ───────────────────────────────────────────────────────────
TENANT_ID = os.getenv("AZURE_TENANT_ID")
CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
PROJECT_ENDPOINT = os.getenv("PROJECT_ENDPOINT")
AGENT_NAME = os.getenv("AGENT_NAME", "Fabric-Executive-Agent")
AGENT_VERSION = os.getenv("AGENT_VERSION", "2")
SCOPES = ["https://ai.azure.com/user_impersonation"]


# ── Custom credential wrapping MSAL token ──────────────────────────────────
class MsalTokenCredential(TokenCredential):
    """Wraps an MSAL access token for use with Azure SDK clients."""

    def __init__(self, access_token: str, expires_on: int):
        self._token = AccessToken(access_token, expires_on)

    def get_token(self, *scopes, **kwargs):
        return self._token


# ── MSAL Device Code Flow ──────────────────────────────────────────────────
def get_msal_app() -> msal.PublicClientApplication:
    authority = f"https://login.microsoftonline.com/{TENANT_ID}"
    return msal.PublicClientApplication(
        client_id=CLIENT_ID,
        authority=authority,
    )


def device_code_login():
    """Run device code flow: user visits URL, enters code, app gets token."""
    app = get_msal_app()
    flow = app.initiate_device_flow(scopes=SCOPES)
    if "user_code" not in flow:
        st.error(f"Failed to initiate device flow: {flow.get('error_description', 'Unknown error')}")
        return None

    # Show instructions to user
    st.info(f"👉 Go to **{flow['verification_uri']}** and enter code: **{flow['user_code']}**")
    st.caption("Waiting for you to complete sign-in...")

    progress = st.progress(0)
    timeout = flow.get("expires_in", 600)
    interval = flow.get("interval", 5)
    elapsed = 0

    # Poll for token
    while elapsed < timeout:
        result = app.acquire_token_by_device_flow(flow, exit_condition=lambda flow: True)
        if "access_token" in result:
            progress.progress(100)
            return result
        time.sleep(interval)
        elapsed += interval
        progress.progress(min(int(elapsed / timeout * 100), 99))

    st.error("Sign-in timed out. Please refresh and try again.")
    return None


# ── Agent invocation ───────────────────────────────────────────────────────
def invoke_foundry_agent(user_message: str) -> str:
    """Invoke the Foundry agent using the signed-in user's token."""
    token_data = st.session_state["token_data"]
    credential = MsalTokenCredential(
        access_token=token_data["access_token"],
        expires_on=int(time.time()) + token_data.get("expires_in", 3600),
    )

    project_client = AIProjectClient(
        endpoint=PROJECT_ENDPOINT,
        credential=credential,
    )
    openai_client = project_client.get_openai_client()

    kwargs = {
        "input": [{"role": "user", "content": user_message}],
        "extra_body": {
            "agent_reference": {
                "name": AGENT_NAME,
                "version": AGENT_VERSION,
                "type": "agent_reference",
            }
        },
    }

    if "last_response_id" in st.session_state:
        kwargs["previous_response_id"] = st.session_state.last_response_id

    try:
        response = openai_client.responses.create(**kwargs)
    except Exception as e:
        return f"⚠️ Agent invocation failed: {e}"

    st.session_state.last_response_id = response.id
    return response.output_text


# ── Streamlit UI ────────────────────────────────────────────────────────────
def main():
    st.set_page_config(
        page_title="Fabric Executive Agent",
        page_icon="🤖",
        layout="centered",
    )

    st.title("🤖 Fabric Executive Agent")
    st.caption("Powered by Azure AI Foundry  •  User Sign-In (Device Code)")

    # Validate env vars
    missing = [v for v in ("AZURE_TENANT_ID", "AZURE_CLIENT_ID", "PROJECT_ENDPOINT")
               if not os.getenv(v)]
    if missing:
        st.error(f"Missing environment variables: {', '.join(missing)}")
        st.stop()

    # ── Auth flow ──
    if "token_data" not in st.session_state:
        st.warning("You need to sign in to use the Fabric Executive Agent.")
        if st.button("🔐 Sign in with Microsoft"):
            result = device_code_login()
            if result and "access_token" in result:
                st.session_state["token_data"] = result
                st.session_state["user_name"] = result.get("id_token_claims", {}).get("name", "User")
                st.rerun()
        st.stop()

    # ── Signed in → show chat ──
    user_name = st.session_state.get("user_name", "User")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ask the Fabric Executive Agent..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = invoke_foundry_agent(prompt)
            st.markdown(response)

        st.session_state.messages.append({"role": "assistant", "content": response})

    # Sidebar
    with st.sidebar:
        st.header("Session")
        st.success(f"✅ Signed in as: {user_name}")
        st.text(f"Agent: {AGENT_NAME}")
        st.text(f"Version: {AGENT_VERSION}")
        if st.button("🔄 New Conversation"):
            for key in ("messages", "last_response_id"):
                st.session_state.pop(key, None)
            st.rerun()
        if st.button("🚪 Sign Out"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()


if __name__ == "__main__":
    main()
